'''Parse JVM class file, according JAVA SE 8 spec
'''
import os
import logging
from lib import read_bytes
from lib import constant_pool
from lib import attributes
from lib import run_time_data

classpath = './'
java_home = ''
java_library_path = ''


class ClassStruct(object):
    '''Store compiled class structures such as the run-time
    constant pool, field and method data, and the code for
    methods and constructors, including the special methods
    used in class and instance initialization and interface
    initialization.
    '''
    def __init__(self):
        self.magic = 0
        self.minor_version = 0
        self.major_version = 0
        self.constant_pool = None
        self.access_flags = 0
        self.this_class = 0
        self.super_class = 0
        self.interfaces_count = 0
        self.interfaces = []
        self.fields_count = 0
        self.fields = []
        self.methods_count = 0
        self.methods = []
        self.attributes_count = 0
        self.attributes = []

    def name(self):
        this_class = self.constant(self.this_class)
        assert type(this_class) is constant_pool.ConstantClass, 'this_class index in constant_pool is not CONSTANT_Class_info'
        name_str = self.constant(this_class.name_index)
        assert type(name_str) is constant_pool.ConstantUtf8, 'name_index in constant_pool is not CONSTANT_Utf8_info'
        return name_str.value()

    def find_method(self, method_name):
        for method in self.methods:
            name_const = self.constant_pool[method.name_index]
            assert type(name_const) is constant_pool.ConstantUtf8, 'Method {0} name_index in constant_pool is not CONSTANT_Utf8_info'.format(method_name)
            if name_const.value() == method_name:
                return method
        return None

    def validate(self):
        '''Valid if class struct according to spec
        Raise ValueError if any fail validation
        '''
        # Well, trust it now.
        pass

    def debug_info(self):
        logging.debug('Class file info')
        logging.debug('Magic number: 0x{:X}'.format(self.magic))
        logging.debug('Major version:' + str(self.major_version))
        logging.debug('Minor version:' + str(self.minor_version))
        logging.debug('Constant count:' + str(self.constant_pool.count))
        for index in range(1, self.constant_pool.count):
            self.constant_pool[index].debug_info('\tCONSTANT_POOL[{0}] ->'.format(index))
        self.access_flags.debug_info()
        logging.debug('This class index:' + str(self.this_class))
        logging.debug('Super class index:' + str(self.super_class))
        logging.debug('Interface count:' + str(self.interfaces_count))
        for interface in self.interfaces:
            logging.debug('\tinterface index in constant_pool:' + str(interface))
        logging.debug('Fields count:' + str(self.fields_count))
        logging.debug('Methods count:' + str(self.methods_count))
        for method in self.methods:
            method.debug_info()
        logging.debug('Attributes count:' + str(self.attributes_count))
        for attr in self.attributes:
            attr.debug_info()


class BootstrapClassLoader(object):
    '''Class for parse and store a JAVA class file
    '''
    def __init__(self):
        pass

    def parse(self, fd) -> ClassStruct:
        class_struct = ClassStruct()
        class_struct.magic = read_bytes.read_u4_int(fd)
        assert class_struct.magic == 0xCAFEBABE, 'Magic number ({0}) in class file is wrong'.format(class_struct.magic)
        class_struct.minor_version = read_bytes.read_u2_int(fd)
        class_struct.major_version = read_bytes.read_u2_int(fd)
        class_struct.constant_pool = constant_pool.parse(fd)
        class_struct.access_flags = AccessFlags()
        class_struct.access_flags.parse(fd)
        class_struct.this_class = read_bytes.read_u2_int(fd)
        class_struct.super_class = read_bytes.read_u2_int(fd)
        class_struct.interfaces_count = read_bytes.read_u2_int(fd)
        for _ in range(class_struct.interfaces_count):
            class_struct.interfaces.append(read_bytes.read_u2_int(fd))
        class_struct.fields_count = read_bytes.read_u2_int(fd)
        for _ in range(class_struct.fields_count):
            field = Field()
            field.parse(fd, class_struct)
            class_struct.fields.append(field)
        class_struct.methods_count = read_bytes.read_u2_int(fd)
        for _ in range(class_struct.methods_count):
            method = Method()
            method.parse(fd, class_struct)
            class_struct.methods.append(method)
        (class_struct.attributes_count, class_struct.attributes) = attributes.parse(fd, class_struct)
        assert len(fd.read(1)) == 0, 'Class file is finish parsed, but still data left in tail.'
        class_struct.validate()
        return class_struct


class _GenericAccessFlags(object):
    '''Generic part for access_flags item for class, interface, field and method
    '''
    def __init__(self):
        self._flags = 0

    def parse(self, fd):
        self._flags = read_bytes.read_u2_int(fd)

    def public(self):
        return (self._flags & 0x0001 > 0)

    def private(self):
        return (self._flags & 0x0002 > 0)

    def protected(self):
        return (self._flags & 0x0004 > 0)

    def static(self):
        return (self._flags & 0x0008 > 0)

    def final(self):
        return (self._flags & 0x0010 > 0)

    def abstract(self):
        return (self._flags & 0x0400 > 0)

    def synthetic(self):
        return (self._flags & 0x1000 > 0)

    def enum(self):
        return (self._flags & 0x4000 > 0)


class AccessFlags(_GenericAccessFlags):
    '''access_flags item is a mask of flags used to denote access
    permissions to and properties of this class or interface
    '''
    def __init__(self):
        super(AccessFlags, self).__init__()

    def super(self):
        return (self._flags & 0x0020 > 0)

    def interface(self):
        return (self._flags & 0x0200 > 0)

    def annotation(self):
        return (self._flags & 0x2000 > 0)

    def debug_info(self):
        logging.debug('access_flags - ACC_PUBLIC:' + str(self.public()))
        logging.debug('access_flags - ACC_FINAL:' + str(self.final()))
        logging.debug('access_flags - ACC_SUPER:' + str(self.super()))
        logging.debug('access_flags - ACC_INTERFACE:' + str(self.interface()))
        logging.debug('access_flags - ACC_ABSTRACT:' + str(self.abstract()))
        logging.debug('access_flags - ACC_SYNTHETIC:' + str(self.synthetic()))
        logging.debug('access_flags - ACC_ANNOTATION:' + str(self.annotation()))
        logging.debug('access_flags - ACC_ENUM:' + str(self.enum()))


class Field(object):
    def __init__(self):
        pass

    class AccessFlags(_GenericAccessFlags):
        '''access_flags item is a mask of flags used to denote access
        permission to and properties of this field.
        '''
        def __init__(self):
            super(Field.AccessFlags, self).__init__()

        def volatile(self):
            return (self._flags & 0x0040 > 0)

        def transient(self):
            return (self._flags & 0x0080 > 0)

        def debug_info(self, prefix):
            logging.debug(prefix + 'access_flags - ACC_PUBLIC:' + str(self.public()))
            logging.debug(prefix + 'access_flags - ACC_PRIVATE:' + str(self.public()))
            logging.debug(prefix + 'access_flags - ACC_PROTECTED:' + str(self.public()))
            logging.debug(prefix + 'access_flags - ACC_STATIC:' + str(self.public()))
            logging.debug(prefix + 'access_flags - ACC_FINAL:' + str(self.final()))
            logging.debug(prefix + 'access_flags - ACC_VOLATILE:' + str(self.volatile()))
            logging.debug(prefix + 'access_flags - ACC_TRANSIENT:' + str(self.transient()))
            logging.debug(prefix + 'access_flags - ACC_SYNTHETIC:' + str(self.synthetic()))
            logging.debug(prefix + 'access_flags - ACC_ENUM:' + str(self.enum()))

    def parse(self, fd, class_file):
        self.access_flags = Field.AccessFlags()
        self.access_flags.parse(fd)
        self.name_index = read_bytes.read_u2_int(fd)
        self.descriptor_index = read_bytes.read_u2_int(fd)
        (self.attributes_count, self.attributes) = attributes.parse(fd, class_file)

    def debug_info(self):
        logging.debug('Field  - name index:' + str(self.name_index))
        logging.debug('       - descriptor index:' + str(self.descriptor_index))
        self.access_flags.debug_info('       - ')
        logging.debug('       - attributes count:' + str(self.attributes_count))
        for attr in self.attributes:
            attr.debug_info('       - ')


class Method(object):
    def __init__(self):
        pass

    class AccessFlags(_GenericAccessFlags):
        '''access_flags item is a mask of flags used to denote access
        permission to and properties of this method.
        '''
        def __init__(self):
            super(Method.AccessFlags, self).__init__()

        def synchronized(self):
            return (self._flags & 0x0020 > 0)

        def bridge(self):
            return (self._flags & 0x0040 > 0)

        def varargs(self):
            return (self._flags & 0x0080 > 0)

        def native(self):
            return (self._flags & 0x0100 > 0)

        def strict(self):
            return (self._flags & 0x0800 > 0)

        def debug_info(self, prefix):
            logging.debug(prefix + 'access_flags - ACC_PUBLIC:' + str(self.public()))
            logging.debug(prefix + 'access_flags - ACC_PRIVATE:' + str(self.public()))
            logging.debug(prefix + 'access_flags - ACC_PROTECTED:' + str(self.public()))
            logging.debug(prefix + 'access_flags - ACC_STATIC:' + str(self.public()))
            logging.debug(prefix + 'access_flags - ACC_FINAL:' + str(self.final()))
            logging.debug(prefix + 'access_flags - ACC_SYNCHRONIZED:' + str(self.synchronized()))
            logging.debug(prefix + 'access_flags - ACC_BRIDGE:' + str(self.bridge()))
            logging.debug(prefix + 'access_flags - ACC_VARARGS:' + str(self.varargs()))
            logging.debug(prefix + 'access_flags - ACC_NATIVE:' + str(self.native()))
            logging.debug(prefix + 'access_flags - ACC_ABSTRACT:' + str(self.abstract()))
            logging.debug(prefix + 'access_flags - ACC_STRICT:' + str(self.strict()))
            logging.debug(prefix + 'access_flags - ACC_SYNTHETIC:' + str(self.synthetic()))

    def parse(self, fd, class_file):
        self.access_flags = Method.AccessFlags()
        self.access_flags.parse(fd)
        self.name_index = read_bytes.read_u2_int(fd)
        self.descriptor_index = read_bytes.read_u2_int(fd)
        self.attributes_count, self.attributes = attributes.parse(fd, class_file)

    def code(self):
        for attr in self.attributes:
            if type(attr) is attributes.CodeAttribute:
                # Only one code attribute in Method
                return attr
        return None

    def debug_info(self):
        logging.debug('Method - name index:' + str(self.name_index))
        logging.debug('       - descriptor index:' + str(self.descriptor_index))
        self.access_flags.debug_info('       - ')
        logging.debug('       - attributes count:' + str(self.attributes_count))
        for attr in self.attributes:
            attr.debug_info('       -       - ')


def parse(file_name: str, loader=BootstrapClassLoader):
    class_loader = loader()
    with open(file_name, 'rb') as java_class_file:
        class_struct = class_loader.parse(java_class_file)
    return class_struct


def load_class(classname: str) -> ClassStruct:
    """
    :param classname: str, represent the name of class
    :return: ClassStruct object if the class is success loaded, otherwise None
    """
    filename = classname + '.class'
    possible_path = os.path.join(classpath, filename)
    if os.path.isfile(possible_path):
        class_struct = parse(possible_path)
        run_time_data.method_area[classname] = class_struct
        return class_struct
    return None