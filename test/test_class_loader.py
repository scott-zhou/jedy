import os
from unittest import TestCase
from lib.class_loader import BootstrapClassLoader
from lib import constant_pool
import logging


class TestBootstrapClassLoader(TestCase):
    def setUp(self):
        class_loader = BootstrapClassLoader()
        filename = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'local_static_func/',
            'LocalStaticFunc.class'
        )
        logging.debug(f'Loading file {filename}')
        with open(filename, 'rb') as java_class_file:
            self.class_struct = class_loader.parse(java_class_file)

    def tearDown(self):
        self.class_struct = None

    def test_magic_number_in_classfile_must_be_correct(self):
        self.assertIsNotNone(self.class_struct, 'Load class fail')
        self.assertEqual(
            self.class_struct.magic, 0xCAFEBABE, 'Magic number wrong')

    def test_version_in_classfile_must_be_correct(self):
        self.assertIsNotNone(self.class_struct, 'Load class fail')
        self.assertEqual(
            self.class_struct.major_version, 52, 'Major version wrong')
        self.assertEqual(
            self.class_struct.minor_version, 0, 'Minor version wrong')

    def test_load_constant_pool(self):
        self.assertIsNotNone(self.class_struct, 'Load class fail')
        self.assertIsNotNone(
            self.class_struct.constant_pool, 'Constant pool is none.')
        self.assertEqual(self.class_struct.constant_pool.count, 20)
        expected_class = [
            None,
            constant_pool.CONSTANT_Methodref,
            constant_pool.CONSTANT_Methodref,
            constant_pool.CONSTANT_Class,
            constant_pool.CONSTANT_Class,
            constant_pool.CONSTANT_Utf8,
            constant_pool.CONSTANT_Utf8,
            constant_pool.CONSTANT_Utf8,
            constant_pool.CONSTANT_Utf8,
            constant_pool.CONSTANT_Utf8,
            constant_pool.CONSTANT_Utf8,
            constant_pool.CONSTANT_Utf8,
            constant_pool.CONSTANT_Utf8,
            constant_pool.CONSTANT_Utf8,
            constant_pool.CONSTANT_Utf8,
            constant_pool.CONSTANT_Utf8,
            constant_pool.CONSTANT_NameAndType,
            constant_pool.CONSTANT_NameAndType,
            constant_pool.CONSTANT_Utf8,
            constant_pool.CONSTANT_Utf8,
        ]
        for index in range(1, self.class_struct.constant_pool.count):
            self.assertIs(
                expected_class[index],
                self.class_struct.constant_pool[index].tag)
            constant_type = constant_pool.constant_type_tag_to_class.get(
                expected_class[index], None)
            self.assertIs(
                constant_type, type(self.class_struct.constant_pool[index]))
