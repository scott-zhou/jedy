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

    def test_class_access_flags(self):
        self.assertIsNotNone(self.class_struct, 'Load class fail')
        self.assertTrue(self.class_struct.access_flags.public())
        self.assertFalse(self.class_struct.access_flags.final())
        self.assertTrue(self.class_struct.access_flags.super())
        self.assertFalse(self.class_struct.access_flags.interface())
        self.assertFalse(self.class_struct.access_flags.abstract())
        self.assertFalse(self.class_struct.access_flags.synthetic())
        self.assertFalse(self.class_struct.access_flags.annotation())
        self.assertFalse(self.class_struct.access_flags.enum())

    def test_this_class_name(self):
        self.assertEqual(
            self.class_struct.constant_pool.get_constant_class_name(
                self.class_struct.this_class),
            'LocalStaticFunc'
        )

    def test_super_class_name(self):
        self.assertEqual(
            self.class_struct.constant_pool.get_constant_class_name(
                self.class_struct.super_class),
            'java/lang/Object'
        )

    def test_interface_counter(self):
        self.assertEqual(self.class_struct.interfaces_count, 0)

    def test_field_counter(self):
        self.assertEqual(self.class_struct.fields_count, 0)

    def test_method_counter(self):
        self.assertEqual(self.class_struct.methods_count, 3)
