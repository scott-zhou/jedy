'''Parse JVM class file, according JAVA SE 8 spec
'''
import logging
import struct


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
        self.__magic = _read_u4_int(fd)
        assert self.__magic == 0xCAFEBABE, 'Magic number ({0}) in class file is wrong'.format(self.__magic)
        self.__minor_version = _read_u2_int(fd)
        self.__major_version = _read_u2_int(fd)
        # The constant_pool table is indexed from 1 to constant_pool_count - 1.
        # Which means the actual count is constant_pool_count - 1
        self.__constant_pool_count = _read_u2_int(fd)
        long_or_double = False
        for _ in range(self.__constant_pool_count - 1):
            constant = GenericConstant.parse(fd, long_or_double)
            long_or_double = type(constant) in (ConstantLong, ConstantDouble)
            self.__constant_pool.append(constant)
        self.__validate_constant_pool()
        self.__access_flags = AccessFlags()
        self.__access_flags.parse(fd)
        self.__this_class = _read_u2_int(fd)
        self.__super_class = _read_u2_int(fd)
        self.__interfaces_count = _read_u2_int(fd)
        for _ in range(self.__interfaces_count):
            self.__interfaces.append(_read_u2_int(fd))
        self.__fields_count = _read_u2_int(fd)
        for _ in range(self.__fields_count):
            field = Field()
            field.parse(fd, self)
            self.__fields.append(field)
        self.__methods_count = _read_u2_int(fd)
        for _ in range(self.__methods_count):
            method = Method()
            method.parse(fd, self)
            self.__methods.append(method)
        self.__attributes_count = _read_u2_int(fd)
        for _ in range(self.__attributes_count):
            attribute = Attribute.parse(fd, self)
            self.__attributes.append(attribute)
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


def _read_ux_int(fd, x):
    return int.from_bytes(fd.read(x), byteorder='big')


def _read_u1_int(fd):
    return _read_ux_int(fd, 1)


def _read_u2_int(fd):
    return _read_ux_int(fd, 2)


def _read_u4_int(fd):
    return _read_ux_int(fd, 4)


def _read_u8_int(fd):
    return _read_ux_int(fd, 8)


def _read_u4_float(fd):
    return struct.unpack('>f', fd.read(4))


def _read_u8_float(fd):
    return struct.unpack('>f', fd.read(8))


def _read_string(fd, length):
    return fd.read(length).decode()


class GenericConstant(object):
    '''Base type for elements in constant_pool
    '''
    CONSTANT_Class     = 7
    CONSTANT_Fieldref  = 9
    CONSTANT_Methodref = 10
    CONSTANT_InterfaceMethodref = 11
    CONSTANT_String    = 8
    CONSTANT_Integer   = 3
    CONSTANT_Float     = 4
    CONSTANT_Long      = 5
    CONSTANT_Double    = 6
    CONSTANT_NameAndType        = 12
    CONSTANT_Utf8      = 1
    CONSTANT_MethodHandle       = 15
    CONSTANT_MethodType         = 16
    CONSTANT_InvokeDynamic      = 18

    def __init__(self, tag):
        self.__tag = tag
        self.__usable = True

    @staticmethod
    def parse(fd, prev_long_or_double):
        '''Parse one constant in constant_pool. Set constant be unusable
        if previous constant is long or double.
        '''
        tag = _read_u1_int(fd)
        constant_type = {
            GenericConstant.CONSTANT_Class: ConstantClass,
            GenericConstant.CONSTANT_Fieldref: ConstantFieldref,
            GenericConstant.CONSTANT_Methodref: ConstantMethodref,
            GenericConstant.CONSTANT_InterfaceMethodref: ConstantInterfaceMethodref,
            GenericConstant.CONSTANT_String: ConstantString,
            GenericConstant.CONSTANT_Integer: ConstantInteger,
            GenericConstant.CONSTANT_Float: ConstantFloat,
            GenericConstant.CONSTANT_Long: ConstantLong,
            GenericConstant.CONSTANT_Double: ConstantDouble,
            GenericConstant.CONSTANT_NameAndType: ConstantNameAndType,
            GenericConstant.CONSTANT_Utf8: ConstantUtf8,
            GenericConstant.CONSTANT_MethodHandle: ConstantMethodHandle,
            GenericConstant.CONSTANT_MethodType: ConstantMethodType,
            GenericConstant.CONSTANT_InvokeDynamic: ConstantInvokeDynamic
        }.get(tag, None)
        if not constant_type:
            raise ValueError(
                'Constant tag {0} is not valid.'.format(tag)
            )
        constant = constant_type()
        constant.parse(fd)
        if prev_long_or_double:
            constant.unuse()
        return constant

    def unuse(self):
        self.__usable = False

    def debug_info(self, prefix):
        pass


class ConstantClass(GenericConstant):
    '''The CONSTANT_Class_info structure in constant_pool,
    used to represent a class or an interface.
    '''
    def __init__(self):
        super(ConstantClass, self).__init__(self.CONSTANT_Class)

    def parse(self, fd):
        self.__name_index = _read_u2_int(fd)
        # TODO: check index availability after pool parsed
        # In spec 4.4.1. The CONSTANT_Class_info Structure

    def debug_info(self, prefix):
        logging.debug(prefix + 'CONSTANT_Class_info - name_index:' + str(self.__name_index))


class ConstantFieldref(GenericConstant):
    '''The CONSTANT_Fieldref_info structure in constant_pool
    '''
    def __init__(self):
        super(ConstantFieldref, self).__init__(self.CONSTANT_Fieldref)

    def parse(self, fd):
        self.__class_index = _read_u2_int(fd)
        self.__name_and_type_index = _read_u2_int(fd)
        # TODO: validate index may be either a class type or an interface type
        # In spec 4.4.2

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'CONSTANT_Fieldref_info - class_index:' +
            str(self.__class_index) +
            '; name_and_type_index:' +
            str(self.__name_and_type_index)
        )


class ConstantMethodref(GenericConstant):
    '''The ConstantMethodref structure in constant_pool
    '''
    def __init__(self):
        super(ConstantMethodref, self).__init__(self.CONSTANT_Methodref)

    def parse(self, fd):
        self.__class_index = _read_u2_int(fd)
        self.__name_and_type_index = _read_u2_int(fd)
        # TODO: validate index must be a class type
        # In spec 4.4.2

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'ConstantMethodref - class_index:' +
            str(self.__class_index) +
            '; name_and_type_index:' +
            str(self.__name_and_type_index)
        )


class ConstantInterfaceMethodref(GenericConstant):
    '''The CONSTANT_Fieldref_info structure in constant_pool
    '''
    def __init__(self):
        super(ConstantInterfaceMethodref, self).__init__(
            self.CONSTANT_InterfaceMethodref
        )

    def parse(self, fd):
        self.__class_index = _read_u2_int(fd)
        self.__name_and_type_index = _read_u2_int(fd)
        # TODO: validate index must be an interface type
        # In spec 4.4.2

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'ConstantInterfaceMethodref - class_index:' +
            str(self.__class_index) +
            '; name_and_type_index:' +
            str(self.__name_and_type_index)
        )


class ConstantString(GenericConstant):
    '''The CONSTANT_String_info Structure in constant_pool,
    used to represent constant objects of the type String
    '''
    def __init__(self):
        super(ConstantString, self).__init__(self.CONSTANT_String)

    def parse(self, fd):
        self.__string_index = _read_u2_int(fd)
        # TODO: validate index entry must be a CONSTANT_Utf8_info structure
        # In spec 4.4.3

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'CONSTANT_String_info - string_index:' +
            str(self.__string_index)
        )


class ConstantInteger(GenericConstant):
    '''The CONSTANT_Integer_info Structure in constant_pool.
    '''
    def __init__(self):
        super(ConstantInteger, self).__init__(self.CONSTANT_Integer)

    def parse(self, fd):
        self.__value = _read_u4_int(fd)
        # In spec it's bytes, use veriable name __value.

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'CONSTANT_Integer_info - value:' +
            str(self.__value)
        )


class ConstantFloat(GenericConstant):
    '''The CONSTANT_Float_info Structures in constant_pool.
    '''
    def __init__(self):
        super(ConstantFloat, self).__init__(self.CONSTANT_Float)

    def parse(self, fd):
        self.__value = _read_u4_float(fd)
        # In spec it's bytes, use veriable name __value.

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'CONSTANT_Float_info - value:' +
            str(self.__value)
        )


class ConstantLong(GenericConstant):
    '''The CONSTANT_Long_info represent 8-byte numeric long constants
    In python, use integer for long long C type
    '''
    def __init__(self):
        super(ConstantLong, self).__init__(self.CONSTANT_Long)

    def parse(self, fd):
        self.__value = _read_u8_int(fd)

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'CONSTANT_Long_info - value:' +
            str(self.__value)
        )


class ConstantDouble(GenericConstant):
    '''The CONSTANT_Double_info represent 8-byte numeric double constants
    In python, use float for double C type
    '''
    def __init__(self):
        super(ConstantDouble, self).__init__(self.CONSTANT_Double)

    def parse(self, fd):
        self.__value = _read_u8_float(fd)

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'CONSTANT_Double_info - value:' +
            str(self.__value)
        )


class ConstantNameAndType(GenericConstant):
    '''The CONSTANT_NameAndType_info structure is used to represent a field
    or method, without indicating which class or interface type it belongs to.
    '''
    def __init__(self):
        super(ConstantNameAndType, self).__init__(self.CONSTANT_NameAndType)

    def parse(self, fd):
        self.__name_index = _read_u2_int(fd)
        self.__descriptor_index = _read_u2_int(fd)
        # TODO: validate indexs in constant_pool after parse all
        # In spec 4.4.6

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'CONSTANT_NameAndType_info - name_index:' +
            str(self.__name_index) +
            '; descriptor_index:' +
            str(self.__descriptor_index)
        )


class ConstantUtf8(GenericConstant):
    '''The CONSTANT_Utf8_info structure is used to represent constant string values
    '''
    def __init__(self):
        super(ConstantUtf8, self).__init__(self.CONSTANT_Utf8)

    def parse(self, fd):
        length = _read_u2_int(fd)
        self.__str_value = _read_string(fd, length)

    def value(self):
        return self.__str_value

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'CONSTANT_Utf8_info - string value:' +
            str(self.__str_value)
        )


class ConstantMethodHandle(GenericConstant):
    '''The CONSTANT_MethodHandle_info structure is used to represent
    a method handle
    '''
    def __init__(self):
        super(ConstantMethodHandle, self).__init__(self.CONSTANT_MethodHandle)

    def parse(self, fd):
        self.__reference_kind = _read_u1_int(fd)
        self.__reference_index = _read_u2_int(fd)
        # TODO: validate type and index after parse all
        # In spec 4.6.8

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'CONSTANT_MethodHandle_info - reference_kind:' +
            str(self.__reference_kind) +
            '; reference_index:' +
            str(self.__reference_index)
        )


class ConstantMethodType(GenericConstant):
    '''The CONSTANT_MethodType_info structure is used to represent
    a method type
    '''
    def __init__(self):
        super(ConstantMethodType, self).__init__(self.CONSTANT_MethodType)

    def parse(self, fd):
        self.__descriptor_index = _read_u2_int(fd)
        # TODO: validate  index after parse all
        # In spec 4.6.9

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'CONSTANT_MethodType_info - descriptor_index:' +
            str(self.__descriptor_index)
        )


class ConstantInvokeDynamic(GenericConstant):
    '''The CONSTANT_InvokeDynamic_info structure is used by an
    invokedynamic instruction
    to specify a bootstrap method
    '''
    def __init__(self):
        super(ConstantInvokeDynamic, self).__init__(self.CONSTANT_InvokeDynamic)

    def parse(self, fd):
        self.__bootstrap_method_attr_index = _read_u2_int(fd)
        self.__name_and_type_index = _read_u2_int(fd)
        # TODO: validate  index after parse all
        # In spec 4.6.10

    def debug_info(self, prefix):
        logging.debug(
            prefix +
            'CONSTANT_InvokeDynamic_info - bootstrap_method_attr_index:' +
            str(self.__bootstrap_method_attr_index) +
            '; name_and_type_index:' +
            str(self.__name_and_type_index)
        )


class _GenericAccessFlags(object):
    '''Generic part for access_flags item for class, interface, field and method
    '''
    def __init__(self):
        self._flags = 0

    def parse(self, fd):
        self._flags = _read_u2_int(fd)

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
        self.__name_index = _read_u2_int(fd)
        self.__descriptor_index = _read_u2_int(fd)
        self.__attributes_count = _read_u2_int(fd)
        self.__attributes = []
        for _ in range(self.__attributes_count):
            attribute = Attribute.parse(fd, class_file)
            self.__attributes.append(attribute)

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
        self.__name_index = _read_u2_int(fd)
        self.__descriptor_index = _read_u2_int(fd)
        self.__attributes_count = _read_u2_int(fd)
        self.__attributes = []
        for _ in range(self.__attributes_count):
            attribute = Attribute.parse(fd, class_file)
            self.__attributes.append(attribute)

    def debug_info(self):
        logging.debug('Method - name index:' + str(self.__name_index))
        logging.debug('       - descriptor index:' + str(self.__descriptor_index))
        self.__access_flags.debug_info('       - ')
        logging.debug('       - attributes count:' + str(self.__attributes_count))
        for attr in self.__attributes:
            attr.debug_info('       - ')


class Attribute(object):
    def __init__(self, name, length):
        self._name = name
        self._length = length

    @staticmethod
    def parse(fd, class_file):
        name_index = _read_u2_int(fd)
        length = _read_u4_int(fd)
        name_constant = class_file.constant(name_index)
        assert type(name_constant) == ConstantUtf8, 'Attribute name constant is not CONSTANT_Utf8_info.'
        attribute_type = {
            'ConstantValue': ConstantValueAttribute,
            'Code': CodeAttribute,
            'StackMapTable': StackMapTableAttribute,
            'Exceptions': ExceptionsAttribute,
            'BootstrapMethods': BootstrapMethodsAttribute
        }.get(name_constant.value(), Attribute)
        attr = attribute_type(name_constant.value(), length)
        attr.parse_info(fd, class_file)
        return attr

    def parse_info(self, fd, class_file):
        self.__info = fd.read(self._length)

    def debug_info(self, prefix=''):
        logging.debug(prefix + 'Attribute name:' + str(self._name))
        logging.debug(prefix + 'Attribute length:' + str(self._length))


'''Five critical attributes to correct interpretation of the class file'''


class ConstantValueAttribute(Attribute):
    pass


class CodeAttribute(Attribute):
    def parse_info(self, fd, class_file):
        self.__max_stack = _read_u2_int(fd)
        self.__max_locals = _read_u2_int(fd)
        self.__code_length = _read_u4_int(fd)
        self.__code = fd.read(self.__code_length)
        self.__exception_table_length = _read_u2_int(fd)
        self.__exception_table = []
        for _ in range(self.__exception_table_length):
            start_pc = _read_u2_int(fd)
            end_pc = _read_u2_int(fd)
            handler_pc = _read_u2_int(fd)
            catch_type = _read_u2_int(fd)
            self.__exception_table.append(tuple(start_pc, end_pc, handler_pc, catch_type))
        self.__attributes_count = _read_u2_int(fd)
        self.__attributes = []
        for _ in range(self.__attributes_count):
            attribute = Attribute.parse(fd, class_file)
            self.__attributes.append(attribute)

    def debug_info(self, prefix=''):
        super().debug_info(prefix)
        logging.debug(prefix + 'code length:' + str(self.__code_length))
        logging.debug(prefix + 'attribute count:' + str(self.__attributes_count))


class StackMapTableAttribute(Attribute):
    pass


class ExceptionsAttribute(Attribute):
    pass


class BootstrapMethodsAttribute(Attribute):
    pass
