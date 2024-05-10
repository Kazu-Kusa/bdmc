import pathlib
import time
import unittest

from viztracer import VizTracer

from bdmc import set_log_level
from bdmc.modules.controller import MotorInfo, CloseLoopController
from bdmc.modules.debug import motor_speed_test

VIZ_OUTPUT_DIR = pathlib.Path(__file__).parent / "viz_output"
VIZ_OUTPUT_DIR.mkdir(exist_ok=True)


class TestControllerSend(unittest.TestCase):
    def setUp(self):
        self.test_port = None
        self.tracer = VizTracer()

    def test_send(self):
        set_log_level(10)
        m = [MotorInfo(code_sign=1, direction=-1), MotorInfo(code_sign=2, direction=-1)]
        self.tracer.start()
        motor_speed_test(port=self.test_port, motor_infos=m, interval=0.01)
        self.tracer.stop()
        self.tracer.save(output_file=(VIZ_OUTPUT_DIR / "test_send.json").as_posix())

    def test_unique_motor_check(self):
        m = [MotorInfo(code_sign=1, direction=-1), MotorInfo(code_sign=1, direction=-1)]

        with self.assertRaises(ValueError):
            CloseLoopController(port=self.test_port, motor_infos=m)

    def test_cmds_align(self):
        m = [MotorInfo(code_sign=1, direction=-1), MotorInfo(code_sign=2, direction=-1)]
        con = CloseLoopController(port=self.test_port, motor_infos=m)
        con.set_motors_speed([1000, 2000])
        with self.assertRaises(ValueError):
            con.set_motors_speed([100] * 3)

    def test_delays(self):
        m = [MotorInfo(code_sign=1, direction=-1), MotorInfo(code_sign=2, direction=-1)]
        con = CloseLoopController(port=self.test_port, motor_infos=m)
        start = time.time()
        con.delay(1)
        self.assertAlmostEqual(start + 1, time.time(), delta=0.02)
        start = time.time()
        con.delay_b(1, lambda: False)
        self.assertAlmostEqual(start + 1, time.time(), delta=0.02)
        start = time.time()
        print(con.delay_b(1, lambda: False))
        self.assertAlmostEqual(start + 1, time.time(), delta=0.02)


if __name__ == "__main__":
    pass
