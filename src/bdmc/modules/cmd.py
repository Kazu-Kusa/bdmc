from enum import Enum


class CMD(Enum):
    """
    CMDs that is a constant
    """

    RESET = b"RESET\r"  # 重新启动
    FULL_STOP = b"v0\r"  # 停止电机

    ADL = b"ADL\r"  # 定义逆时针方向为正
    ADR = b"ADR\r"  # 定义顺时针方向为正

    NPOFF = b"NPOFF\r"  # 关闭位置应答
    NVOFF = b"NVOFF\r"  # 关闭速度应答
    EEPSAVE = b"EEPSAVE\r"  # 将参数写入驱动器EERPROM
