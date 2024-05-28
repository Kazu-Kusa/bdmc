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
        updater = self.con.register_context_executor(func, ["output"], [])
        updater()
        func.assert_called_once()
        print(self.con.context)
        self.assertEqual(self.con.context["output"], "output_value")

    def test_case_2_no_inputs_and_multiple_outputs(self):
        # 函数无输入，多个输出
        func = MagicMock(return_value=["out1", "out2"])
        updater = self.con.register_context_executor(func, ["out1", "out2"], [])
        updater()
        func.assert_called_once()
        self.assertEqual(self.con.context["out1"], "out1")
        self.assertEqual(self.con.context["out2"], "out2")

    def test_case_3_unfrozen_single_input_no_outputs(self):
        # 未冻结的单个输入，无输出
        func = MagicMock()
        updater = self.con.register_context_executor(func, [], ["key1"])
        updater()
        func.assert_called_once_with("value1")

    def test_case_4_frozen_single_input_no_outputs(self):
        # 冻结的单个输入，无输出
        func = MagicMock()
        self.con.register_context_executor(func, [], ["key1"], freeze_inputs=True)
        # 不检查函数调用，因为在这种情况下函数不会在上下文更新时被调用

    def test_case_5_unfrozen_multiple_inputs_no_outputs(self):
        # 未冻结的多个输入，无输出
        func = MagicMock()
        updater = self.con.register_context_executor(func, [], ["key1", "key2"])
        updater()
        func.assert_called_once_with("value1", "value2")

    def test_case_6_frozen_multiple_inputs_no_outputs(self):
        # 冻结的多个输入，无输出
        func = MagicMock()
        frozen_data = ("value1", "value2")
        updater = self.con.register_context_executor(func, [], ["key1", "key2"], freeze_inputs=True)
        updater()
        func.assert_called_once_with(*frozen_data)

    def test_case_7_unfrozen_single_input_single_output(self):
        # 未冻结的单个输入，单个输出
        func = MagicMock(return_value="output_value")
        updater = self.con.register_context_executor(func, ["output"], ["key1"])
        updater()
        func.assert_called_once_with("value1")
        self.assertEqual(self.con.context["output"], "output_value")

    def test_case_8_frozen_single_input_single_output(self):
        # 冻结的单个输入，单个输出
        func = MagicMock(return_value="output_value")
        updater = self.con.register_context_executor(func, ["output"], ["key1"], freeze_inputs=True)
        updater()
        func.assert_called_once_with("value1")
        self.assertEqual(self.con.context["output"], "output_value")

    def test_case_9_unfrozen_multiple_inputs_multiple_outputs(self):
        # 未冻结的多个输入，多个输出
        func = MagicMock(return_value=["out1", "out2"])
        updater = self.con.register_context_executor(func, ["out1", "out2"], ["key1", "key2"])
        updater()
        func.assert_called_once_with("value1", "value2")
        self.assertEqual(self.con.context["out1"], "out1")
        self.assertEqual(self.con.context["out2"], "out2")

    def test_case_10_frozen_multiple_inputs_multiple_outputs(self):
        # 冻结的多个输入，多个输出
        func = MagicMock(side_effect=[("out1", "out2")])
        updater = self.con.register_context_executor(func, ["out1", "out2"], ["key1", "key2"], freeze_inputs=True)
        updater()
        func.assert_called_once_with("value1", "value2")
        self.assertEqual(self.con.context["out1"], "out1")
        self.assertEqual(self.con.context["out2"], "out2")

    def test_invalid_arguments_exception(self):
        with self.assertRaises(ValueError):
            # 测试无效参数引发的异常
            self.con.register_context_executor(lambda: None, [], [])


class TestCloseLoopController(unittest.TestCase):

    def setUp(self):
        self.controller = CloseLoopController()
        # 假设的上下文字典
        self.controller._context = {"var1": 1, "var2": 2, "var3": 3}

    def test_register_context_getter_with_single_key(self):
        # 测试单个键值
        getter = self.controller.register_context_getter("var1")
        self.assertEqual(getter(), 1)

    def test_register_context_getter_with_single_key_in_sequence(self):
        # 测试包含单个键的序列
        getter = self.controller.register_context_getter(["var2"])
        self.assertEqual(getter(), 2)

    def test_register_context_getter_with_multiple_keys(self):
        # 测试包含多个键的序列
        getter = self.controller.register_context_getter(["var2", "var3"])
        self.assertEqual(getter(), (2, 3))

    def test_register_context_getter_with_invalid_key_type(self):
        # 测试无效的键类型
        with self.assertRaises(ValueError):
            self.controller.register_context_getter(123)

    def test_register_context_getter_with_empty_sequence(self):
        # 测试空序列作为键
        with self.assertRaises(ValueError):
            self.controller.register_context_getter([])

    def test_register_context_getter_with_none_key(self):
        # 测试 None 作为键
        with self.assertRaises(ValueError):
            self.controller.register_context_getter(None)


class MockFunction:
    def __call__(self, *args, **kwargs):
        return args, kwargs


class TestCloseLoopControllerRegisterContextExecutor(unittest.TestCase):

    def setUp(self):
        self.controller = CloseLoopController()
        self.controller._context = {"a": 1, "b": 2, "c": 3, "d": 4}  # 假设的上下文

    def test_register_context_executor_with_empty_keys(self):
        with self.assertRaises(ValueError):
            self.controller.register_context_executor(MockFunction(), [], [])

    def test_register_context_executor_with_missing_input_key(self):
        with self.assertRaises(ValueError):
            self.controller.register_context_executor(MockFunction(), ["f"], ["e"])

    def test_register_context_executor_with_single_input_single_output(self):
        func = MockFunction()
        input_key = "a"
        output_key = "result"
        updater = self.controller.register_context_executor(func, [output_key], [input_key])
        updater()
        print(self.controller.context)
        self.assertIn(output_key, self.controller._context)
        self.assertEqual(self.controller._context[output_key], ((self.controller.context.get(input_key),), {}))

    def test_register_context_executor_with_multiple_inputs_single_output(self):
        func = MockFunction()
        input_keys = ["a", "b"]
        output_key = "result"
        updater = self.controller.register_context_executor(func, [output_key], input_keys)
        updater()
        print(self.controller.context)
        self.assertIn(output_key, self.controller._context)
        self.assertEqual(
            self.controller._context[output_key],
            (tuple(self.controller.context.get(input_key) for input_key in input_keys), {}),
        )

    def test_register_context_executor_with_freeze_inputs_single_input(self):
        func = MockFunction()
        input_key = "a"
        output_key = "result"
        updater = self.controller.register_context_executor(func, [output_key], [input_key], freeze_inputs=True)
        updater()
        self.assertIn(output_key, self.controller._context)
        self.assertEqual(self.controller._context[output_key], ((1,), {}))

    def test_register_context_executor_with_single_input_multiple_outputs(self):
        func = MockFunction()
        input_key = "a"
        output_keys = ["result1", "result2"]
        updater = self.controller.register_context_executor(func, output_keys, [input_key])
        updater()
        for key in output_keys:
            self.assertIn(key, self.controller._context)
        self.assertEqual(self.controller._context[output_keys[0]], (1,))
        self.assertEqual(self.controller._context[output_keys[1]], {})

    def test_register_context_executor_with_multiple_inputs_no_output(self):
        func = MockFunction()
        input_keys = ["a", "b"]
        updater = self.controller.register_context_executor(func, [], input_keys)
        updater()
        self.assertEqual(len(self.controller._context), 4)  # 检查上下文未增加新键

    def test_register_context_executor_with_freeze_inputs_multiple_inputs_no_output(self):
        func = MockFunction()
        input_keys = ["a", "b"]
        updater = self.controller.register_context_executor(func, [], input_keys, freeze_inputs=True)
        updater()
        self.assertEqual(len(self.controller._context), 4)  # 检查上下文未增加新键

    def test_register_context_executor_with_freeze_inputs_multiple_inputs_multiple_outputs(self):
        func = MockFunction()
        input_keys = ["a", "b"]
        output_keys = ["result1", "result2"]
        updater = self.controller.register_context_executor(func, output_keys, input_keys, freeze_inputs=True)
        updater()
        print(self.controller._context)
        for key in output_keys:
            self.assertIn(key, self.controller._context)
        self.assertEqual(self.controller._context[output_keys[0]], (1, 2))
        self.assertEqual(self.controller._context[output_keys[1]], {})


# 运行测试
if __name__ == "__main__":
    unittest.main()
