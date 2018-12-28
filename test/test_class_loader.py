import os
import nose
from lib.class_loader import BootstrapClassLoader
import logging


class TestBootstrapClassLoader:
    def setup(self):
        class_loader = BootstrapClassLoader()
        filename = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'local_static_func/',
            'LocalStaticFunc.class'
        )
        logging.debug(f'Loading file {filename}')
        with open(filename, 'rb') as java_class_file:
            self.class_struct = class_loader.parse(java_class_file)

    def teardown(self):
        self.class_struct = None

    def test_magic_number_in_classfile_must_be_correct(self):
        nose.tools.ok_(self.class_struct, 'Load class fail')
        nose.tools.eq_(
            self.class_struct.magic, 0xCAFEBABE, 'Magic number wrong')

    def test_version_in_classfile_must_be_correct(self):
        nose.tools.ok_(self.class_struct, 'Load class fail')
        nose.tools.eq_(
            self.class_struct.major_version, 52, 'Major version wrong')
        nose.tools.eq_(
            self.class_struct.minor_version, 0, 'Minor version wrong')
