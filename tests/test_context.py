import unittest
from unittest.mock import MagicMock

from bdmc import CloseLoopController, MotorInfo


class TestContextUpdaterRegistration(unittest.TestCase):

    def setUp(self):
        self.con = CloseLoopController(
            motor_infos=[MotorInfo(code_sign=1, direction=-1), MotorInfo(code_sign=2, direction=-1)],
            context={"key1": "value1", "key2": "value2"},
        )
        # 假设有一个简单的上下文字典

    def test_case_1_no_inputs_and_single_output(self):
        # 函数无输入，单个输出
        func = MagicMock(return_value="output_value")
        updater = self.con.register_context_updater(func, [], ["output"])
        updater()
        func.assert_called_once()
        print(self.con.context)
        self.assertEqual(self.con.context["output"], "output_value")

    def test_case_2_no_inputs_and_multiple_outputs(self):
        # 函数无输入，多个输出
        func = MagicMock(return_value=["out1", "out2"])
        updater = self.con.register_context_updater(func, [], ["out1", "out2"])
        updater()
        func.assert_called_once()
        self.assertEqual(self.con.context["out1"], "out1")
        self.assertEqual(self.con.context["out2"], "out2")

    def test_case_3_unfrozen_single_input_no_outputs(self):
        # 未冻结的单个输入，无输出
        func = MagicMock()
        updater = self.con.register_context_updater(func, ["key1"], [])
        updater()
        func.assert_called_once_with("value1")

    def test_case_4_frozen_single_input_no_outputs(self):
        # 冻结的单个输入，无输出
        func = MagicMock()
        self.con.register_context_updater(func, ["key1"], [], freeze_inputs=True)
        # 不检查函数调用，因为在这种情况下函数不会在上下文更新时被调用

    def test_case_5_unfrozen_multiple_inputs_no_outputs(self):
        # 未冻结的多个输入，无输出
        func = MagicMock()
        updater = self.con.register_context_updater(func, ["key1", "key2"], [])
        updater()
        func.assert_called_once_with("value1", "value2")

    def test_case_6_frozen_multiple_inputs_no_outputs(self):
        # 冻结的多个输入，无输出
        func = MagicMock()
        frozen_data = ("value1", "value2")
        updater = self.con.register_context_updater(func, ["key1", "key2"], [], freeze_inputs=True)
        updater()
        func.assert_called_once_with(*frozen_data)

    def test_case_7_unfrozen_single_input_single_output(self):
        # 未冻结的单个输入，单个输出
        func = MagicMock(return_value="output_value")
        updater = self.con.register_context_updater(func, ["key1"], ["output"])
        updater()
        func.assert_called_once_with("value1")
        self.assertEqual(self.con.context["output"], "output_value")

    def test_case_8_frozen_single_input_single_output(self):
        # 冻结的单个输入，单个输出
        func = MagicMock(return_value="output_value")
        updater = self.con.register_context_updater(func, ["key1"], ["output"], freeze_inputs=True)
        updater()
        func.assert_called_once_with("value1")
        self.assertEqual(self.con.context["output"], "output_value")

    def test_case_9_unfrozen_multiple_inputs_multiple_outputs(self):
        # 未冻结的多个输入，多个输出
        func = MagicMock(return_value=["out1", "out2"])
        updater = self.con.register_context_updater(func, ["key1", "key2"], ["out1", "out2"])
        updater()
        func.assert_called_once_with("value1", "value2")
        self.assertEqual(self.con.context["out1"], "out1")
        self.assertEqual(self.con.context["out2"], "out2")

    def test_case_10_frozen_multiple_inputs_multiple_outputs(self):
        # 冻结的多个输入，多个输出
        func = MagicMock(side_effect=[("out1", "out2")])
        updater = self.con.register_context_updater(func, ["key1", "key2"], ["out1", "out2"], freeze_inputs=True)
        updater()
        func.assert_called_once_with("value1", "value2")
        self.assertEqual(self.con.context["out1"], "out1")
        self.assertEqual(self.con.context["out2"], "out2")

    def test_invalid_arguments_exception(self):
        with self.assertRaises(ValueError):
            # 测试无效参数引发的异常
            self.con.register_context_updater(lambda: None, [], [])
