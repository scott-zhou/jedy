import os
from unittest import TestCase
from lib import (
    class_loader,
    thread,
    run_time_data
)


class TestAsAWholeProgramm(TestCase):
    def setUp(self):
        class_loader.jrelibpath = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '..',
            'jre',
            'lib'
        )

    def tearDown(self):
        self.class_struct = None

    def load_main(self, klass_path, klass_name):
        class_loader.classpath = klass_path
        self.class_struct = class_loader.load_class(klass_name)
        self.main_thread = thread.Thread(
            klass_name, 'main', '([Ljava/lang/String;)V', [''])
        run_time_data.thread_pool.append(self.main_thread)

    def test_local_static_func_return_6(self):
        self.load_main(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'local_static_func'
            ),
            'LocalStaticFunc'
        )

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

    def test_simple_loop(self):
        self.load_main(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'simple_loop'
            ),
            'SimpleLoop'
        )

        final_index_1_value = None

        def func(idx, value):
            print(f'ID: {idx}, value: {value}')
            nonlocal final_index_1_value
            if idx == 1:
                final_index_1_value = value

        class_loader.local_variable_callbacks['SimpleLoop.main'] = func
        self.main_thread.run()
        self.assertEqual(
            final_index_1_value, 30, 'Simple loop calculate get wrong result.')

    def test_load_another_class(self):
        self.load_main(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'load_another_class'
            ),
            'Main'
        )

        final_index_1_value = None

        def func(idx, value):
            print(f'ID: {idx}, value: {value}')
            nonlocal final_index_1_value
            if idx == 1:
                final_index_1_value = value

        class_loader.local_variable_callbacks['Main.main'] = func
        self.main_thread.run()
        self.assertEqual(
            final_index_1_value,
            6,
            'Load another class call cal func return wrong result.'
        )

    def test_virtual_function(self):
        self.load_main(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'call_virtual_function'
            ),
            'Main'
        )

        local_variable_index_2_values = []

        def func(idx, value):
            print(f'ID: {idx}, value: {value}')
            nonlocal local_variable_index_2_values
            if idx == 2:
                local_variable_index_2_values.append(value)

        class_loader.local_variable_callbacks['Main.main'] = func
        self.main_thread.run()
        self.assertEqual(
            local_variable_index_2_values,
            [20, 1],
            'Virtual function wrong result.'
        )

    def test_get_set_field(self):
        self.load_main(
            os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'get_set_field'
            ),
            'Main'
        )
        local_variable_index_2_values = []
        local_variable_index_3_values = []

        def func(idx, value):
            print(f'ID: {idx}, value: {value}')
            nonlocal local_variable_index_2_values
            nonlocal local_variable_index_3_values
            if idx == 2:
                local_variable_index_2_values.append(value)
            elif idx == 3:
                local_variable_index_3_values.append(value)
        class_loader.local_variable_callbacks['Main.main'] = func
        self.main_thread.run()
        self.assertEqual(
            local_variable_index_2_values,
            [99, 199],
            'Virtual function wrong result.'
        )
        self.assertEqual(
            local_variable_index_3_values,
            [199, 99],
            'Virtual function wrong result.'
        )
