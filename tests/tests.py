import unittest

from bdmc.modules.controller import MotorInfo, CloseLoopController
from bdmc.modules.debug import handle_user_input, motor_speed_test
from bdmc.modules.seriald import SerialClient


class MyTestCase(unittest.TestCase):

    def test_send(self):
        m = [MotorInfo(code_sign=1, direction=-1)]
        motor_speed_test(port="COM3", motor_infos=m)

    def test_unique_motor_check(self):
        m = [MotorInfo(code_sign=1, direction=-1), MotorInfo(code_sign=1, direction=-1)]

        with self.assertRaises(ValueError):
            CloseLoopController(port="COM3", motor_infos=m)

    def test_cmds_align(self):
        m = [MotorInfo(code_sign=1, direction=-1), MotorInfo(code_sign=2, direction=-1)]
        con = CloseLoopController(port="COM3", motor_infos=m)
        con.set_motors_speed([1000, 2000])
        with self.assertRaises(ValueError):
            con.set_motors_speed([100] * 3)

    def test_user_input(self):

        con = SerialClient(port="COM3")
        handle_user_input(con)


if __name__ == "__main__":
    pass
