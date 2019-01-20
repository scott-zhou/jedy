import os
from unittest import TestCase
from lib import (
    class_loader,
    thread,
    run_time_data
)


class TestBootstrapClassLoader(TestCase):
    def setUp(self):
        class_loader.classpath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'local_static_func'
        )
        class_loader.jrelibpath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '..'
        )
        self.class_struct = class_loader.load_class('LocalStaticFunc')
        self.main_thread = thread.Thread(
            'LocalStaticFunc', 'main', '([Ljava/lang/String;)V', [''])
        run_time_data.thread_pool.append(self.main_thread)

    def tearDown(self):
        self.class_struct = None

    def test_local_static_func_return_6(self):
        final_index_1_value = None

        def func(idx, value):
            print(f'ID: {idx}, value: {value}')
            nonlocal final_index_1_value
            if idx == 1:
                final_index_1_value = value
        class_loader.local_variable_callbacks['LocalStaticFunc.main'] = func
        self.main_thread.run()
        self.assertEqual(
            final_index_1_value, 6, 'Local static func return value wrong.')
