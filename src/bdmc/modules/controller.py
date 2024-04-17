from itertools import zip_longest
from queue import Queue
from threading import Thread
from typing import List, Optional, ByteString, Literal, TypeAlias, Sequence, Self

from .cmd import CMD
from .logger import _logger
from .seriald import SerialClient

DIRECTION: TypeAlias = Literal[1, -1]


class MotorInfo:
    def __init__(self, code_sign: int, direction: DIRECTION = 1):
        self.code_sign = code_sign
        self.direction = direction

    def __eq__(self, other) -> bool:
        return self.code_sign == other.code_sign

    def __hash__(self) -> int:
        return hash(self.code_sign)


class CloseLoopController:
    def __init__(self, motor_infos: Sequence[MotorInfo], port: Optional[str] = None):
        """
        :param motor_infos: A list of MotorInfo objects containing motor ID and direction.
        """
        if len(motor_infos) != len(set(motor_infos)):
            raise ValueError("Motor infos must be unique.")

        self._serial: SerialClient = SerialClient(port=port)
        self._motor_infos: Sequence[MotorInfo] = motor_infos
        self._cmd_queue: Queue[ByteString] = Queue()
        self._msg_send_thread: Optional[Thread] = None
        self._msg_send_thread_should_run: bool = True

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
        return self._serial

    def stop_msg_sending(self) -> Self:
        """
        Stop the message sending by setting the _msg_send_thread_should_run flag to False and joining the message send thread.
        """
        self._msg_send_thread_should_run = False
        self._msg_send_thread.join()
        self._msg_send_thread = None
        return self

    def start_msg_sending(self) -> Self:
        """
        A description of the entire function, its parameters, and its return types.
        """

        _logger.info("MSG sending thread starting")
        self._msg_send_thread_should_run = True
        self._msg_send_thread = Thread(name="msg_send_thread", target=self._msg_sending_loop)
        self._msg_send_thread.daemon = True
        self._msg_send_thread.start()

        return self

    def _msg_sending_loop(self) -> None:
        """
        A function that handles the sending of messages in a loop.
        It continuously retrieves messages from a queue and writes them to a channel until the thread should stop running.
        Returns None.
        """
        _logger.info(f"MSG sending thread started")
        while self._msg_send_thread_should_run:
            temp = self._cmd_queue.get()
            _logger.debug(f"Writing {temp} to channel,remaining {self._cmd_queue.qsize()}")
            self._serial.write(temp)
        _logger.info("MSG sending thread stopped")

    def set_motors_speed(self, speeds: Sequence[int]) -> Self:
        """
        Set the speed for each motor based on the provided speed_list.

        Parameters:
            speeds (Sequence[int]): A list of speeds for each motor.

        Returns:
            None
        """
        if any(speeds):
            if len(speeds) != len(self._motor_infos):
                raise ValueError("Length of speed_list must be equal to the number of motors")
            cmd_list = [
                f"{motor_info.code_sign}v{speed * motor_info.direction}"
                for motor_info, speed in zip_longest(self._motor_infos, speeds)
            ]
            self._cmd_queue.put(b"".join((cmd + "\r").encode("ascii") for cmd in cmd_list))
        else:
            self._cmd_queue.put(CMD.FULL_STOP.value)

        return self

    def send_cmd(self, cmd: CMD) -> Self:

        self._cmd_queue.put(cmd.value)
        return self
