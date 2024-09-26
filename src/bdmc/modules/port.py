from typing import List

from serial.tools.list_ports import comports


def find_usb_tty(id_product: int = 0, id_vendor: int = 0) -> List[str]:
    """
    Finds and returns a list of USB TTY devices with the specified ID product and ID vendor.
    :param id_product: the product ID
    :param id_vendor: the vendor ID
    :return: a list of USB TTY devices that match the specified criteria
    """


    return list(map(lambda x: x.device,filter(lambda x: x.vid == id_vendor and x.pid == id_product,comports())))


def find_serial_ports() -> List[str]:
    """
    Finds and returns a list of serial ports.
    :return: a list of serial ports
    """
    return [port.device for port in comports()]
