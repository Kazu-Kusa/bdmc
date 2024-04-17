from typing import List

from serial.tools.list_ports import comports


def find_usb_tty(id_product: int = 0, id_vendor: int = 0) -> List[str]:
    """
    该函数实现在 Linux 系统下查找指定厂商和产品 ID 的 USB 串口设备，并返回设备名列表。
    """
    import re

    tty_list = []

    # 预编译正则表达式以提高性能
    pattern = re.compile(r"idVendor=(\d{4})\s+idProduct=(\d{4})")

    for i in comports():
        # 判断串口文件名是否包含有 "USB" 或 "ACM"
        if "USB" in i.device or "ACM" in i.device:
            # 使用正则表达式提取 idVendor 和 idProduct
            match = pattern.search(i.description)
            if match:
                try:
                    vendor_id = int(match.group(1), 16)
                    product_id = int(match.group(2), 16)
                except ValueError:
                    # 如果转换失败，跳过这个设备
                    continue
                if vendor_id == id_vendor and product_id == id_product:
                    tty_list.append(i.device)

    return tty_list


def find_serial_ports() -> List[str]:
    """
    A function that finds and returns a list of serial ports.

    Returns:
        List[str]: A list of strings representing the serial ports found.
    """
    return [port.device for port in comports()]
