'''Parse JVM class file, according JAVA SE 8 spec
'''
import logging
import read_bytes
import constant_pool
import attributes


def parse(file_name):
    class_file = ClassFile()
    with open(file_name, 'rb') as java_class_file:
        class_file.parse(java_class_file)
    return class_file


class ClassFile(object):
    '''Class for parse and store a JAVA class file
    '''
    def __init__(self):
        self.__magic = 0
        self.__minor_version = 0
        self.__major_version = 0
        self.__constant_pool_count = 0
        self.__constant_pool = []
        self.__access_flags = 0
        self.__this_class = 0
        self.__super_class = 0
        self.__interfaces_count = 0
        self.__interfaces = []
        self.__fields_count = 0
        self.__fields = []
        self.__methods_count = 0
        self.__methods = []
        self.__attributes_count = 0
        self.__attributes = []

    def parse(self, fd):
        self.__magic = read_bytes.read_u4_int(fd)
        assert self.__magic == 0xCAFEBABE, 'Magic number ({0}) in class file is wrong'.format(self.__magic)
        self.__minor_version = read_bytes.read_u2_int(fd)
        self.__major_version = read_bytes.read_u2_int(fd)
        (self.__constant_pool_count, self.__constant_pool) = constant_pool.parse(fd)
        self.__validate_constant_pool()
        self.__access_flags = AccessFlags()
        self.__access_flags.parse(fd)
        self.__this_class = read_bytes.read_u2_int(fd)
        self.__super_class = read_bytes.read_u2_int(fd)
        self.__interfaces_count = read_bytes.read_u2_int(fd)
        for _ in range(self.__interfaces_count):
            self.__interfaces.append(read_bytes.read_u2_int(fd))
        self.__fields_count = read_bytes.read_u2_int(fd)
        for _ in range(self.__fields_count):
            field = Field()
            field.parse(fd, self)
            self.__fields.append(field)
        self.__methods_count = read_bytes.read_u2_int(fd)
        for _ in range(self.__methods_count):
            method = Method()
            method.parse(fd, self)
            self.__methods.append(method)
        (self.__attributes_count, self.__attributes) = attributes.parse(fd, self)
        assert len(fd.read(1)) == 0, 'Class file is finish parsed, but still data left in tail.'

    def __validate_constant_pool(self):
        '''Valid if constant_pool according to spec
        Raise ValueError if any fail validation
        '''
        # Well, trust it now.
        pass

    def constant(self, index):
        '''Return constant in constant_pool on given index
        index valid from 1 to constant_pool_count - 1
        '''
        assert index >= 1 and index < self.__constant_pool_count, 'Invalid constant index {0}'.format(index)
        return self.__constant_pool[index - 1]

    def name(self):
        this_class = self.constant(self.__this_class)
        assert type(this_class) is constant_pool.ConstantClass, 'this_class index in constant_pool is not CONSTANT_Class_info'
        name_str = self.constant(this_class.name_index())
        assert type(name_str) is constant_pool.ConstantUtf8, 'name_index in constant_pool is not CONSTANT_Utf8_info'
        return name_str.value()

    def debug_info(self):
        logging.debug('Class file info')
        logging.debug('Magic number: 0x{:X}'.format(self.__magic))
        logging.debug('Major version:' + str(self.__major_version))
        logging.debug('Minor version:' + str(self.__minor_version))
        logging.debug('Constant count:' + str(self.__constant_pool_count))
        for index in range(self.__constant_pool_count - 1):
            self.__constant_pool[index].debug_info('\tCONSTANT_POOL[{0}] ->'.format(index + 1))
        self.__access_flags.debug_info()
        logging.debug('This class index:' + str(self.__this_class))
        logging.debug('Super class index:' + str(self.__super_class))
        logging.debug('Interface count:' + str(self.__interfaces_count))
        for interface in self.__interfaces:
            logging.debug('\tinterface index in constant_pool:' + str(interface))
        logging.debug('Fields count:' + str(self.__fields_count))
        logging.debug('Methods count:' + str(self.__methods_count))
        for method in self.__methods:
            method.debug_info()
        logging.debug('Attributes count:' + str(self.__attributes_count))
        for attr in self.__attributes:
            attr.debug_info()


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
        self.__access_flags = Field.AccessFlags()
        self.__access_flags.parse(fd)
        self.__name_index = read_bytes.read_u2_int(fd)
        self.__descriptor_index = read_bytes.read_u2_int(fd)
        (self.__attributes_count, self.__attributes) = attributes.parse(fd, class_file)

    def debug_info(self):
        logging.debug('Field  - name index:' + str(self.__name_index))
        logging.debug('       - descriptor index:' + str(self.__descriptor_index))
        self.__access_flags.debug_info('       - ')
        logging.debug('       - attributes count:' + str(self.__attributes_count))
        for attr in self.__attributes:
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
        self.__access_flags = Method.AccessFlags()
        self.__access_flags.parse(fd)
        self.__name_index = read_bytes.read_u2_int(fd)
        self.__descriptor_index = read_bytes.read_u2_int(fd)
        self.__attributes_count, self.__attributes = attributes.parse(fd, class_file)

    def debug_info(self):
        logging.debug('Method - name index:' + str(self.__name_index))
        logging.debug('       - descriptor index:' + str(self.__descriptor_index))
        self.__access_flags.debug_info('       - ')
        logging.debug('       - attributes count:' + str(self.__attributes_count))
        for attr in self.__attributes:
            attr.debug_info('       - ')
