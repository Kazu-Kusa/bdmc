from types import MappingProxyType
from typing import Callable, Any, Optional, ByteString, Dict

from serial import Serial, EIGHTBITS, PARITY_NONE, STOPBITS_ONE
from serial.serialutil import SerialException
from serial.threaded import ReaderThread, Protocol

from bdmc.modules.logger import _logger
from bdmc.modules.port import find_serial_ports

ReadHandler = Callable[[bytes | bytearray], Optional[Any]]
DEFAULT_SERIAL_KWARGS = MappingProxyType(
    {"baudrate": 115200, "bytesize": EIGHTBITS, "parity": PARITY_NONE, "stopbits": STOPBITS_ONE, "timeout": 2}
)


def serial_kwargs_factory(
    baudrate: int = 115200,
    bytesize: int = EIGHTBITS,
    parity: str = PARITY_NONE,
    stopbits: int = STOPBITS_ONE,
    timeout: float = 2,
) -> MappingProxyType:
    """
    A function that generates a dictionary of serial port settings with default values.

    Parameters:
        baudrate (int): The baud rate for the serial port. Default is 115200.
        bytesize (int): The number of data bits. Default is EIGHTBITS.
        parity (str): The parity checking scheme. Default is PARITY_NONE.
        stopbits (int): The number of stop bits. Default is STOPBITS_ONE.
        timeout (float): The timeout value for the serial port. Default is 2.

    Returns:
        MappingProxyType: A read-only mapping of the serial port settings.
    """
    return MappingProxyType(
        {"baudrate": baudrate, "bytesize": bytesize, "parity": parity, "stopbits": stopbits, "timeout": timeout}
    )


CODING_METHOD = "ascii"


def default_read_handler(data: bytes | bytearray) -> None:
    print(f"\n##Received:{data.decode(CODING_METHOD)}")


class ReadProtocol(Protocol):

    def __init__(self, read_handler: Optional[ReadHandler] = None):
        self._read_handler: ReadHandler = read_handler if read_handler else lambda data: None

    def connection_made(self, transport):
        """Called when reader thread is started"""
        _logger.info("ReadProtocol has been Set")

    def data_received(self, data):
        """Called with snippets received from the serial port"""
        self._read_handler(data)


def new_ReadProtocol_factory(read_handler: Optional[ReadHandler] = None) -> Callable[[], ReadProtocol]:
    def factory():
        return ReadProtocol(read_handler)

    return factory


class SerialClient:
    """
    create Serial Client
    """

    def __init__(
        self,
        port: Optional[str] = None,
        serial_config: Optional[Dict] = DEFAULT_SERIAL_KWARGS,
        search_available_port: bool = False,
    ):
        """
        :param serial_config: a dict that contains the critical transport parameters
        :param port: the serial port to use
        """
        self._serial: Serial = Serial(**serial_config)

        if port is not None:
            # 尝试使用用户提供的端口
            self._serial.port = port
            if not self.open():
                raise ValueError(f"The specified port '{port}' is not available or cannot be opened.")

        elif search_available_port:
            # 没有提供端口，尝试自动查找并打开可用端口
            _logger.info("Searching available Ports")
            available_serial_ports = find_serial_ports()
            if not available_serial_ports:
                raise ValueError("No serial ports FOUND!")

            _logger.info(f"Available ports: {available_serial_ports}")

            for ava_port in available_serial_ports:
                self._serial.port = ava_port
                if self.open():
                    break
            else:
                raise ValueError("No available serial ports could be opened.")
        else:
            pass
        self._read_thread: Optional[ReaderThread] = None

    @property
    def is_connected(self) -> bool:

        return self._serial.is_open

    @property
    def port(self) -> str:
        return self._serial.port

    @port.setter
    def port(self, value: str):
        """
        pyserial will reopen the serial port on the serial port change
        :param value:
        :return:
        """
        self._serial.port = value

    def open(self) -> bool:
        """
        Connect to the serial port with the settings specified in the instance attributes using a thread-safe mechanism.
        Return True if the connection is successful, else False.
        """
        # 如果当前尚未连接
        try:
            _logger.info(f"Trying to open {self._serial.port}")

            # 创建一个 `Serial` 实例连接到对应的串口，并根据实例属性设置相关参数
            self._serial.open() if not self._serial.is_open else None
            _logger.info(f"Successfully open [{self._serial.port}]")
            # 如果已经连接，直接返回 True 表示已连接
            return True
        except SerialException:
            _logger.critical(f"Failed to open [{self._serial.port}]")
            return False

    def close(self):
        """
        disconnects the connection
        :return:
        """
        self._serial.close()

    def write(self, data: ByteString) -> bool:
        """
        向串口设备中写入二进制数据。

        Args:
            data: 要写入的二进制数据

        Returns:
            如果写入成功则返回 True，否则返回 False。

        Raises:
            无异常抛出。

        Examples:
            serial = SerialHelper()
            if serial.write(b'hello world'):
                print('Data was successfully written to serial port.')
            else:
                print('Failed to write data to serial port.')

        Note:
            1. 此方法需要确保串口设备已经连接并打开，并且调用此方法前应该先检查设备的状态是否正常。
            2. 在多线程或多进程环境下使用此方法时，需要确保对串口上下文对象（即 SerialPort 类的实例）进行正确的锁定保护，以避免多个线程或进程同时访问串口设备造成不可预期的错误。
        """
        try:
            self._serial.write(data)
            return True
        except SerialException:
            _logger.critical("Serial write error")
            return False

    def read(self, length: int) -> bytes | bytearray:
        """
        从串口设备中读取指定长度的字节数据。

        Args:
            length: 整数类型，要读取的字节长度。

        Returns:
            字节串类型，表示所读取的字节数据。如果读取失败，则返回一个空字节串（b''）。

        Raises:
            无异常抛出。

        Example:
            data = serial.read(length=10)
            print(data)

        Note:
            如果连接断开或者读取过程中发生异常，会在控制台打印错误信息并返回一个空字节串（b''）。
        """
        try:
            return self._serial.read(length)
        except SerialException:
            _logger.critical("Serial read error")
        return b""

    def start_read_thread(self, read_handler: [ReadHandler]) -> None:
        """
        Start the thread reading loop.
        :return:
        """
        _logger.info("Start Read Thread")
        self._read_thread = ReaderThread(
            serial_instance=self._serial, protocol_factory=new_ReadProtocol_factory(read_handler)
        )
        self._read_thread.daemon = True
        self._read_thread.start()

    def stop_read_thread(self) -> None:
        self._read_thread.stop()
