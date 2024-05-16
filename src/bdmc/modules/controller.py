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

    def register_context_updater(
        self, function: Callable[..., Any], input_keys: List[str], output_keys: List[str], freeze_inputs: bool = False
    ) -> Callable[[], None]:
        """
        Registers a context updater function that updates the context with the specified input and output keys.

        Args:
            function (Callable[..., Any]): The function to register as a context updater.
            input_keys (List[str]): The list of input keys to use for the context updater.
            output_keys (List[str]): The list of output keys to update in the context.
            freeze_inputs (bool, optional): Whether to freeze the input data. Defaults to False.

        Returns:
            Callable[[], None]: The registered context updater function.

        Raises:
            ValueError: If either input_keys or output_keys is empty.
            ValueError: If any input variable is not found in the context.
            ValueError: If invalid arguments are provided.
        """
        if input_keys == [] and output_keys == []:
            raise ValueError("Either input_keys or output_keys must be non-empty.")
        # 确保输入和输出变量存在于上下文中
        if not_included := [var for var in input_keys if var not in self._context]:
            raise ValueError(f"Input variables {not_included} not found in context.")

        context = self._context
        input_keys = tuple(input_keys)
        output_keys = tuple(output_keys)
        frozen_input_data = tuple(context.get(key) for key in input_keys)

        match freeze_inputs, input_keys, output_keys:
            case _, (), (output_key,):

                def _updater() -> None:
                    context[output_key] = function()

            case _, (), all_output_keys:

                def _updater() -> None:
                    for key, val in zip(all_output_keys, function()):
                        context[key] = val

            case False, (input_key,), ():

                def _updater() -> None:
                    function(context.get(input_key))

            case True, (input_key,), ():
                input_data = context.get(input_key)

                def _updater() -> None:
                    function(input_data)

            case False, all_input_keys, ():

                def _updater() -> None:
                    function(*(tuple(context.get(key) for key in all_input_keys)))

            case True, all_input_keys, ():

                def _updater() -> None:
                    function(*frozen_input_data)

            case False, (input_key,), (output_key,):

                def _updater() -> None:
                    context[output_key] = function(context.get(input_key))

            case True, (input_key,), (output_key,):
                input_data = context.get(input_key)

                def _updater() -> None:
                    context[output_key] = function(input_data)

            case False, all_input_keys, all_output_keys:

                def _updater() -> None:
                    frozen_input_data = tuple(context.get(key) for key in all_input_keys)
                    for key, output_data in zip(all_output_keys, function(*frozen_input_data)):
                        context[key] = output_data

            case True, all_input_keys, all_output_keys:

                def _updater() -> None:
                    for key, output_data in zip(all_output_keys, function(*frozen_input_data)):
                        context[key] = output_data

            case _:
                raise ValueError(
                    f"Invalid arguments for register_context_updater function. got {input_keys} and {output_keys} and {freeze_inputs}"
                )
        return _updater

    def register_context_getter(self, var_key: str) -> Callable[[], Any]:
        """
        Register a context getter function for a given variable key.

        Args:
            var_key (str): The key of the variable.

        Returns:
            Callable[[], Any]: A function that returns the value of the variable.
        """
        context = self._context
        return lambda: context.get(var_key)

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
        breaker: Callable[[], Any],
        check_interval: float = 0.01,
    ) -> Self:
        """
        Delays the execution of the function by a specified amount of time, while checking a breaker function periodically.

        Parameters:
            delay_sec (float): The amount of time to delay the execution in seconds.
            breaker (Callable[[], Any]): A function that returns a boolean value indicating whether the delay should be aborted.
            check_interval (float, optional): The interval in seconds between each check of the breaker function. Defaults to 0.01.

        Returns:
            Self: The instance of the class itself.

        Raises:
            ValueError: If the check_interval is not at least twice as large as the delay_sec.

        Notes:
            - The delay_sec parameter specifies the total amount of time to delay the execution,
             including the initial delay and the time spent checking the breaker function.
            - The check_interval parameter specifies the interval in seconds between each check of the breaker function.
             It should be at least twice as large as the delay_sec parameter to ensure accurate timing.
            - The breaker function is called periodically to check if the delay should be aborted.
            If the breaker function returns True, the delay is aborted and the function returns immediately.
            - If the breaker function returns False, the function continues to check the breaker function until either
            the delay is completed or the breaker function returns True.
            - If the delay is completed before the breaker function returns True, the function returns immediately.
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
        breaker: Callable[[], GT],
        check_interval: float = 0.01,
    ) -> GT:
        """
        Delays the execution of a function until a condition is met.

        Args:
            delay_sec (float): The number of seconds to delay the execution.
            breaker (Callable[[], GT]): The function to be executed after the delay.
            check_interval (float, optional): The interval between each check. Defaults to 0.01.

        Returns:
            GT: The result of the `breaker` function after the delay.

        Raises:
            ValueError: If `check_interval` is not 2 times greater than `delay_sec`.

        Note:
            - The `delay_sec` parameter specifies the total amount of time to delay the execution,
            including the initial delay and the time spent checking the `breaker` function.
            - The `check_interval` parameter specifies the interval in seconds between each check.
            It should be at least twice as large as the `delay_sec` parameter to ensure accurate timing.
            - The `breaker` function is called periodically to check if the delay should be aborted.
            If the `breaker` function returns True, the delay is aborted and the function returns immediately.
            - If the `breaker` function returns False, the function continues to check the `breaker` function until
            either the delay is completed or the `breaker` function returns True.
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
