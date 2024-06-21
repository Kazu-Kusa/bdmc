from queue import Queue
from threading import Thread
from time import sleep, time
from typing import (
    List,
    Optional,
    ByteString,
    Literal,
    TypeAlias,
    Sequence,
    Self,
    Callable,
    Any,
    TypeVar,
    Hashable,
    Dict,
    Tuple,
)

from bdmc.modules.cmd import CMD
from bdmc.modules.logger import _logger
from bdmc.modules.seriald import SerialClient

DIRECTION: TypeAlias = Literal[1, -1]
GT = TypeVar("GT", bound=Hashable)


class MotorInfo:
    """
    A class representing a motor's ID and direction.
    """

    def __init__(self, code_sign: int, direction: DIRECTION = 1):
        self.code_sign = code_sign
        self.direction = direction

    def __eq__(self, other) -> bool:
        return self.code_sign == other.code_sign

    def __hash__(self) -> int:
        return hash(self.code_sign)


ClassicMIs: Tuple[MotorInfo, MotorInfo, MotorInfo, MotorInfo] = (MotorInfo(1), MotorInfo(2), MotorInfo(3), MotorInfo(4))


class CloseLoopController:
    """
    CloseLoopController is a class designed to manage and control a system involving multiple motors with closed-loop feedback.
    It provides methods for setting motor speeds, sending commands, introducing delays with breakers, and updating a shared context.
    The controller maintains a connection to a serial client for communication with the hardware, manages a command queue,
    and runs a dedicated thread for message sending. It also allows registering context updaters and getters to facilitate data flow within the application.

    Key features and functionality include:

    1. **Initialization**:
       - Accepts a list of `MotorInfo` objects, specifying motor IDs and directions, and an optional serial port for communication.
       - Initializes a `SerialClient` for interfacing with the hardware, a command queue, and a flag for controlling the message sending thread.

    2. **Context Management**:
       - Maintains a dictionary (`_context`) to store shared data across the application.
       - Provides methods `register_context_updater` and `register_context_getter` to register functions that update or retrieve specific context variables.

    3. **Motor Control**:
       - `set_motors_speed`: Sets the speed of each motor based on a provided list of speeds, ensuring consistency with the provided `MotorInfo`.
       - `send_cmd`: Adds a command to the command queue for transmission to the hardware.

    4. **Message Sending**:
       - Manages a background thread (`_msg_send_thread`) responsible for continuously retrieving messages from the command queue and writing them to the serial channel.
       - Offers `start_msg_sending` and `stop_msg_sending` methods to control the message sending thread's lifecycle.

    5. **Delay Functions**:
       - `delay`: Introduces a simple delay for a specified duration in seconds.
       - `delay_b`: Delays execution for a given time, periodically checking a breaker function that can abort the delay if it returns True.
       - `delay_b_match`: Similar to `delay_b`, but returns the result of the breaker function once the delay has completed or the breaker condition is met.

    6. **Utility Methods**:
       - `wait_exec`: Executes a given function and returns the instance of the class itself.
       - Properties `context`, `motor_ids`, `motor_dirs`, `cmd_queue`, and `serial_client` provide convenient access to internal attributes.

    Overall, the CloseLoopController serves as a central hub for coordinating motor operations, handling communication with the hardware, managing shared data, and introducing controlled delays with breakers in a closed-loop motor control system.
    """

    def __init__(
        self,
        motor_infos: Sequence[MotorInfo] = ClassicMIs,
        port: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        search_available_port: bool = False,
    ) -> None:

        if len(motor_infos) != len(set(motor_infos)):
            raise ValueError("Motor infos must be unique.")

        self._serial: SerialClient = SerialClient(port=port, search_available_port=search_available_port)
        self._motor_infos: Sequence[MotorInfo] = motor_infos
        self._cmd_queue: Queue[ByteString] = Queue()
        self._msg_send_thread: Optional[Thread] = None
        self._msg_send_thread_should_run: bool = True
        self._context: Dict[str, Any] = context or {}

    def register_context_executor(
        self,
        function: Callable[..., Any],
        output_keys: Sequence[str] | str = (),
        input_keys: Sequence[str] | str = (),
        freeze_inputs: bool = False,
        function_name: Optional[str] = "_executor",
    ) -> Callable[[], None]:
        """
        Registers a function to be executed in the context of the class.

        Args:
            function (Callable[..., Any]): The function to be executed.
            output_keys (Sequence[str] | str, optional): The keys in the context where the function's output will be stored. Defaults to ().
            input_keys (Sequence[str] | str, optional): The keys in the context that the function will use as input. Defaults to ().
            freeze_inputs (bool, optional): Whether to freeze the input values so that they are not modified during execution. Defaults to False.
            function_name (Optional[str], optional): The name of the function. Defaults to "_executor".

        Returns:
            Callable[[], None]: The registered function.

        Raises:
            ValueError: If neither input_keys nor output_keys are provided, or if the function_name contains spaces.
            ValueError: If any input_keys are not found in the context.
            ValueError: If freeze_inputs is True and input_keys is empty.
            ValueError: If any keys in input_keys or output_keys collide with context keys.

        """
        if not (input_keys or output_keys):
            raise ValueError(
                f"Either input_keys or output_keys must be non-empty. "
                f"You should not register executor as you function needs/dumps not data in/to the context."
            )
        if " " in function_name:
            raise ValueError(f"function_name cannot contain spaces. <{function_name}> is invalid.")
        # 确保输入存在于上下文中
        if not_included := [var for var in input_keys if var not in self._context]:
            raise ValueError(f"Input variables {not_included} not found in context.")

        input_keys: Tuple[str] = tuple(input_keys) if isinstance(input_keys, Sequence) else (input_keys,)
        output_keys: Tuple[str] = tuple(output_keys) if isinstance(output_keys, Sequence) else (output_keys,)
        if freeze_inputs and not input_keys:
            raise ValueError("If freeze_inputs is True, input_keys must be non-empty.")
        function_context: Dict[str, Any] = {
            "__func": function,
            "__input_keys": input_keys,
            "__output_keys": output_keys,
            "__context": self._context,
        }

        func_header = f"def {function_name}()->None:\n"

        if len(output_keys) > 1:
            output_unpack_string = (",".join(f"__context['{k}']" for k in output_keys) + "=") if output_keys else ""
        else:
            output_unpack_string = f'__context["{output_keys[0]}"]='

        if freeze_inputs:
            if collied_keys := [k for k in function_context if k in self._context]:
                raise ValueError(
                    f"{collied_keys} collides with context keys, please use different keys in input_keys and output_keys"
                )
            function_context.update(self._context)
            input_unpack_string = ", ".join(input_keys)

        else:
            input_unpack_string = ",".join(f"__context['{k}']" for k in input_keys)

        func_body = f" {output_unpack_string}__func({input_unpack_string})"
        func = func_header + func_body

        self._context.update({key: None for key in output_keys if key not in self._context})
        exec(func, function_context)
        return function_context.get(function_name)

    def register_context_getter(self, var_key: str | Sequence[str]) -> Callable[[], Any]:
        """
        Registers a context getter function that retrieves values from the internal context dictionary.

        Args:
            var_key (str | Sequence[str]): The key or keys to retrieve from the context dictionary.

        Returns:
            Callable[[], Any]: A function that, when called, retrieves the value(s) associated with the provided key(s) from the context dictionary.

        Raises:
            ValueError: If the var_key parameter is not a string or a sequence of strings with length greater than 1.

        Example:
            >>> controller = CloseLoopController()
            >>> controller.register_context_getter("var1")()
            1
            >>> controller.register_context_getter(["var2", "var3"])()
            (2, 3)
        """
        context = self._context
        if isinstance(var_key, str):
            return lambda: context.get(var_key)
        elif isinstance(var_key, Sequence) and len(var_key) == 1:
            var_key = var_key[0]
            return lambda: context.get(var_key)
        elif isinstance(var_key, Sequence) and len(var_key) > 1:
            return lambda: tuple(context.get(key) for key in var_key)
        else:
            raise ValueError(f"Invalid variable key type: {type(var_key)} | {var_key}")

    def wait_exec(self, function: Callable[[], None]) -> Self:
        """
        Executes the given function and returns the instance of the class itself.

        Parameters:
            function (Callable[[], None]): The function to be executed.

        Returns:
            Self: The instance of the class itself.
        """
        function()
        return self

    @property
    def context(self) -> Dict[str, Any]:
        """
        Returns the context dictionary of the object.

        :return: A dictionary containing the context of the object.
        :rtype: Dict[str, Any]
        """
        return self._context

    @property
    def motor_ids(self) -> List[int]:
        """
        A property that returns a list of motor ids from the motor infos.
        """
        return [motor_info.code_sign for motor_info in self._motor_infos]

    @property
    def motor_dirs(self) -> List[DIRECTION]:
        """
        Return the list of directions for each motor in the motor_infos.
        """
        return [motor_info.direction for motor_info in self._motor_infos]

    @property
    def motor_infos(self) -> Sequence[MotorInfo]:
        """
        Return the list of motor infos.
        """
        return self._motor_infos

    @motor_infos.setter
    def motor_infos(self, value: Sequence[MotorInfo]) -> None:
        """
        Set the list of motor infos.
        """
        self._motor_infos = value

    @property
    def cmd_queue(self) -> Queue[ByteString]:
        """
        Return the message queue.
        """
        return self._cmd_queue

    @property
    def serial_client(self) -> SerialClient:
        """
        A property that returns the serial client.
        """
        return self._serial

    def stop_msg_sending(self) -> Self:
        """
        Stop the message sending by setting the _msg_send_thread_should_run flag to False and joining the message send thread.
        """
        if self._msg_send_thread is None:
            _logger.error("Message sending thread is not running.")
            return self
        _logger.info("Try to stop message sending thread.")
        while not self._cmd_queue.empty():
            sleep(0.1)

        self._msg_send_thread_should_run = False
        self._cmd_queue.put(b"\r")
        self._msg_send_thread.join()
        self._msg_send_thread = None
        return self

    def start_msg_sending(self) -> Self:
        """
        A description of the entire function, its parameters, and its return types.
        """

        if not self._serial.is_connected:
            _logger.error("Serial port is not connected")
            if not self._serial.open():
                _logger.error(f"Failed to open serial port {self._serial.port}")
                return self

        _logger.info("MSG sending thread starting")
        self._msg_send_thread_should_run = True

        cmd_queue_get = self._cmd_queue.get
        serial_write = self._serial.write

        def _msg_sending_loop() -> None:
            """
            A function that handles the sending of messages in a loop.
            It continuously retrieves messages from a queue and writes them to a channel until the thread should stop running.
            Returns None.
            """

            while self._msg_send_thread_should_run:
                temp = cmd_queue_get()
                _logger.debug(f"Writing {temp} to channel.")
                serial_write(temp)
            _logger.info("MSG sending thread sopped")

        self._msg_send_thread = Thread(name="msg_send_thread", target=_msg_sending_loop, daemon=True)
        self._msg_send_thread.start()
        _logger.info("MSG sending thread started")
        return self

    def set_motors_speed(self, speeds: Sequence[int | float]) -> Self:
        """
        Set the speed for each motor based on the provided speed_list.

        Parameters:
            speeds (Sequence[int|float]): A list of speeds for each motor.

        Returns:
            None
        """

        if len(speeds) != len(self._motor_infos):
            raise ValueError("Length of speed_list must be equal to the number of motors")
        self._cmd_queue.put(
            (
                "".join(
                    f"{motor_info.code_sign}v{int(speed * motor_info.direction)}\r"
                    for motor_info, speed in zip(self._motor_infos, speeds)
                )
            ).encode("ascii")
        )
        return self

    def send_cmd(self, cmd: CMD) -> Self:
        """
        Add a command to the command queue.

        Args:
            cmd (CMD): The command to be added to the queue.

        Returns:
            Self: Returns the instance of the class.
        """
        self._cmd_queue.put(cmd.value)
        return self

    def delay_b(
        self,
        delay_sec: float,
        breaker: Callable[[], bool] | Callable[[], int] | Callable[[], float] | Callable[[], Any],
        check_interval: float = 0.01,
    ) -> Self:
        """
        A function to introduce a delay of a specified time with a breaker function.

        Parameters:
            delay_sec (float): The time in seconds to delay.
            breaker (Callable[[], Any]): The breaker function that can abort the delay.
            check_interval (float): The interval to check the breaker function.

        Returns:
            Self: Returns the instance of the class.
        """

        ed_time = time() + delay_sec - check_interval
        # this is to add the first time check, since the timer waits before the check
        if alarm := breaker():
            return self
        while not alarm and time() < ed_time:
            alarm = breaker()
            sleep(check_interval)
        return self

    @staticmethod
    def delay_b_match(
        delay_sec: float,
        breaker: Callable[[], bool] | Callable[[], int] | Callable[[], float] | Callable[[], GT],
        check_interval: float = 0.01,
    ) -> GT:
        """
        Delays the execution based on the specified delay time and checks a breaker function periodically.

        Parameters:
            delay_sec (float): The amount of time to delay the execution in seconds.
            breaker (Callable[[], GT]): A function that returns the status of the delay.
            check_interval (float): The interval between each check of the breaker function.

        Returns:
            GT: The result of the breaker function.

        Notes:
            - The function delays the execution by the specified time and checks the breaker function periodically.
        """

        ed_time = time() + delay_sec - check_interval
        # this is to add the first time check, since the timer waits before the check
        if alarm := breaker():
            return alarm
        while not alarm and time() < ed_time:
            alarm = breaker()
            sleep(check_interval)
        return alarm

    def delay(self, delay_sec: float) -> Self:
        """
        A function to introduce a delay of a specified time.

        Parameters:
            delay_sec (float): The time in seconds to delay.

        Returns:
            Self
        """
        sleep(delay_sec)
        return self
