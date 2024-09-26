from enum import Enum

class CMD(Enum):
    """
    Constants for various commands used to control a device.
    """

    RESET = b"RESET\r"  # Restart the device
    FULL_STOP = b"v0\r"  # Stop the motor

    ADL = b"ADL\r"  # Define counterclockwise direction as positive
    ADR = b"ADR\r"  # Define clockwise direction as positive

    NPOFF = b"NPOFF\r"  # Disable position response
    NVOFF = b"NVOFF\r"  # Disable velocity response
    EEPSAVE = b"EEPSAVE\r"  # Write parameters to the driver's EEPROM
