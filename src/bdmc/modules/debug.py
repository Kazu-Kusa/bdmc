import time
from typing import Sequence

from bdmc.modules.controller import MotorInfo, CloseLoopController


def motor_speed_test(
    port: str,
    motor_infos: Sequence[MotorInfo],
    speed_level: int = 11,
    interval: float = 1,
    laps: int = 1,
) -> None:
    """
    A function to test the speed of motors connected to a specified port.

    Parameters:
        port (str): The port where the motors are connected.
        motor_infos (Sequence[MotorInfo]): Information about the motors being tested.
        speed_level (int): The level of speed to test, default is 11.
        interval (float): The time interval between speed level changes, default is 1.
        laps (int): The number of laps to run the speed test, default is 3.

    Returns:
        None
    """
    motors = len(motor_infos)
    con = CloseLoopController(motor_infos=motor_infos, port=port)

    for _ in range(laps):

        for i in range(speed_level):
            speed = i * 1000
            print(f"doing {speed}")
            con.set_motors_speed([speed] * motors)
            time.sleep(interval)

    con.set_motors_speed([0] * motors)
    print("over")
