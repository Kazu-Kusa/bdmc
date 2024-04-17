from enum import Enum


class CMD(Enum):
    """
    CMDs that is a constant
    """

    RESET = b"RESET\n"
    FULL_STOP = b"v0\n"
