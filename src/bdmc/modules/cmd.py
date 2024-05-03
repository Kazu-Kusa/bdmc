from enum import Enum


class CMD(Enum):
    """
    CMDs that is a constant
    """

    RESET = b"RESET\n"  # 重新启动
    FULL_STOP = b"v0\n"  # 停止电机

    ADL = b"ADL\n"  # 定义逆时针方向为正
    ADR = b"ADR\n"  # 定义顺时针方向为正

    NPOFF = b"NPOFF\n"  # 关闭位置应答
    NVOFF = b"NVOFF\n"  # 关闭速度应答
    EEPSAVE = b"EEPSAVE\n"  # 将参数写入驱动器EERPROM
