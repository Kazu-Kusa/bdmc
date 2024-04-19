import time
from typing import Sequence

from bdmc.modules.controller import MotorInfo, CloseLoopController
from bdmc.modules.seriald import SerialClient


def handle_user_input(serial_client: SerialClient) -> None:
    """
    A function that handles user input by starting a read thread, processing the input, and putting it into a command queue.

    Parameters:
    - serial_client (SerialClient): The client for serial communication.
    - cmd_queue (Queue[ByteString]): The queue to store processed commands.

    Returns:
    - None
    """
    ct = 0
    print("\n\nuser input channel opened\n" "please enter cmd below, enter [exit] to end the channel")

    serial_client.start_read_thread(lambda s: print(f"\n\rout[{ct}]: {s}"))
    try:

        while True:
            user_input = input(f"\n\rin[{ct}]: ")
            ct += 1
            # 对输入的内容进行处理
            compiled_cmd = (user_input + "\r").encode("ascii")
            serial_client.write(compiled_cmd)

            if user_input.lower() == "exit":
                break
    except KeyboardInterrupt:
        pass
    finally:
        serial_client.stop_read_thread()
        print("\n\ruser input channel closed")


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
    con = CloseLoopController(motor_infos=motor_infos, port=port).start_msg_sending()

    for _ in range(laps):

        for i in range(speed_level):
            speed = i * 1000
            print(f"doing {speed}")
            con.set_motors_speed([speed] * motors)
            time.sleep(interval)

    con.set_motors_speed([0] * motors)
    print("over")
