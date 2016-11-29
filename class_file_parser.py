'''Parse JVM class file, according JAVA SE 8 spec
'''
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
            long_or_double = self.__parse_constant_pool(fd, long_or_double)
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
            self.__fields.append(field)
        self.__methods_count = _read_u2_int(fd)
        for _ in range(self.__methods_count):
            method = Method()
            method.parse(fd)
            self.__methods.append(method)
        self.__attributes_count = _read_u2_int(fd)
        for _ in range(self.__attributes_count):
            attribute = Attribute()
            attribute.parse(fd)
            self.__attributes.append(attribute)
        assert len(fd.read(1)) == 0, 'Class file is finish parsed, but still data left in tail.'

    def __parse_constant_pool(self, fd, prev_long_or_double):
        '''Parse one constant in constant_pool. Set constant be unusable
        if previous constant is long or double.
        '''
        tag = _read_u1_int(fd)
        long_or_double = False
        constant_type = {
            _GenericConstant.CONSTANT_Class: ConstantClass,
            _GenericConstant.CONSTANT_Fieldref: ConstantFieldref,
            _GenericConstant.CONSTANT_Methodref: ConstantMethodref,
            _GenericConstant.CONSTANT_InterfaceMethodref: ConstantInterfaceMethodref,
            _GenericConstant.CONSTANT_String: ConstantString,
            _GenericConstant.CONSTANT_Integer: ConstantInteger,
            _GenericConstant.CONSTANT_Float: ConstantFloat,
            _GenericConstant.CONSTANT_Long: ConstantLong,
            _GenericConstant.CONSTANT_Double: ConstantDouble,
            _GenericConstant.CONSTANT_NameAndType: ConstantNameAndType,
            _GenericConstant.CONSTANT_Utf8: ConstantUtf8,
            _GenericConstant.CONSTANT_MethodHandle: ConstantMethodHandle,
            _GenericConstant.CONSTANT_MethodType: ConstantMethodType,
            _GenericConstant.CONSTANT_InvokeDynamic: ConstantInvokeDynamic
        }.get(tag, _GenericConstant)
        if _GenericConstant == constant_type:
            raise NotImplementedError(
                'Constant tag {0} is not implemented in parse.'.format(tag)
            )
        elif ConstantLong == constant_type or ConstantDouble == constant_type:
            long_or_double = True
        constant = constant_type()
        constant.parse(fd)
        if prev_long_or_double:
            constant.unuse()
        self.__constant_pool.append(constant)
        return long_or_double

    def __validate_constant_pool(self):
        '''Valid if constant_pool according to spec
        Raise ValueError if any fail validation
        '''
        # Well, trust it now.
        pass

    def debug_info(self):
        print('Print class file info')
        print('Magic number: 0x{:X}'.format(self.__magic))
        print('Major version:', self.__major_version)
        print('Monor version:', self.__minor_version)
        print('Constant count:', self.__constant_pool_count)
        for index in range(self.__constant_pool_count - 1):
            self.__constant_pool[index].debug_info('\tCONSTANT_POOL[{0}] ->'.format(index + 1))
        self.__access_flags.debug_info()
        print('This class index:', self.__this_class)
        print('Super class index:', self.__super_class)
        print('Interface count:', self.__interfaces_count)
        for interface in self.__interfaces:
            print('\tinterface index in constant_pool:', interface)
        print('Fields count:', self.__fields_count)
        print('Methods count:', self.__methods_count)
        for method in self.__methods:
            method.debug_info()
        print('Attributes count:', self.__attributes_count)
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


class _GenericConstant(object):
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

    def parse(self, fd):
        '''To be implement in children class
        '''
        raise NotImplementedError(
            'parse in _GenericConstant is not implemented.'
        )

    def unuse(self):
        self.__usable = False

    def debug_info(self, prefix):
        pass


class ConstantClass(_GenericConstant):
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
        print(prefix, 'CONSTANT_Class_info - name_index:', self.__name_index)


class ConstantFieldref(_GenericConstant):
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
        print(
            prefix,
            'CONSTANT_Fieldref_info - class_index:',
            self.__class_index,
            '; name_and_type_index:',
            self.__name_and_type_index
        )


class ConstantMethodref(_GenericConstant):
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
        print(
            prefix,
            'ConstantMethodref - class_index:',
            self.__class_index,
            '; name_and_type_index:',
            self.__name_and_type_index
        )


class ConstantInterfaceMethodref(_GenericConstant):
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
        print(
            prefix,
            'ConstantInterfaceMethodref - class_index:',
            self.__class_index,
            '; name_and_type_index:',
            self.__name_and_type_index
        )


class ConstantString(_GenericConstant):
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
        print(
            prefix,
            'CONSTANT_String_info - string_index:',
            self.__string_index
        )


class ConstantInteger(_GenericConstant):
    '''The CONSTANT_Integer_info Structure in constant_pool.
    '''
    def __init__(self):
        super(ConstantInteger, self).__init__(self.CONSTANT_Integer)

    def parse(self, fd):
        self.__value = _read_u4_int(fd)
        # In spec it's bytes, use veriable name __value.

    def debug_info(self, prefix):
        print(
            prefix,
            'CONSTANT_Integer_info - value:',
            self.__value
        )


class ConstantFloat(_GenericConstant):
    '''The CONSTANT_Float_info Structures in constant_pool.
    '''
    def __init__(self):
        super(ConstantFloat, self).__init__(self.CONSTANT_Float)

    def parse(self, fd):
        self.__value = _read_u4_float(fd)
        # In spec it's bytes, use veriable name __value.

    def debug_info(self, prefix):
        print(
            prefix,
            'CONSTANT_Float_info - value:',
            self.__value
        )


class ConstantLong(_GenericConstant):
    '''The CONSTANT_Long_info represent 8-byte numeric long constants
    In python, use integer for long long C type
    '''
    def __init__(self):
        super(ConstantLong, self).__init__(self.CONSTANT_Long)

    def parse(self, fd):
        self.__value = _read_u8_int(fd)

    def debug_info(self, prefix):
        print(
            prefix,
            'CONSTANT_Long_info - value:',
            self.__value
        )


class ConstantDouble(_GenericConstant):
    '''The CONSTANT_Double_info represent 8-byte numeric double constants
    In python, use float for double C type
    '''
    def __init__(self):
        super(ConstantDouble, self).__init__(self.CONSTANT_Double)

    def parse(self, fd):
        self.__value = _read_u8_float(fd)

    def debug_info(self, prefix):
        print(
            prefix,
            'CONSTANT_Double_info - value:',
            self.__value
        )


class ConstantNameAndType(_GenericConstant):
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
        print(
            prefix,
            'CONSTANT_NameAndType_info - name_index:',
            self.__name_index,
            '; descriptor_index:',
            self.__descriptor_index
        )


class ConstantUtf8(_GenericConstant):
    '''The CONSTANT_Utf8_info structure is used to represent constant string values
    '''
    def __init__(self):
        super(ConstantUtf8, self).__init__(self.CONSTANT_Utf8)

    def parse(self, fd):
        length = _read_u2_int(fd)
        self.__str_value = _read_string(fd, length)

    def debug_info(self, prefix):
        print(
            prefix,
            'CONSTANT_Utf8_info - string value:',
            self.__str_value
        )


class ConstantMethodHandle(_GenericConstant):
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
        print(
            prefix,
            'CONSTANT_MethodHandle_info - reference_kind:',
            self.__reference_kind,
            '; reference_index:',
            self.__reference_index
        )


class ConstantMethodType(_GenericConstant):
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
        print(
            prefix,
            'CONSTANT_MethodType_info - descriptor_index:',
            self.__descriptor_index
        )


class ConstantInvokeDynamic(_GenericConstant):
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
        print(
            prefix,
            'CONSTANT_InvokeDynamic_info - bootstrap_method_attr_index:',
            self.__bootstrap_method_attr_index,
            '; name_and_type_index:',
            self.__name_and_type_index
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
        print('access_flags - ACC_PUBLIC:', self.public())
        print('access_flags - ACC_FINAL:', self.final())
        print('access_flags - ACC_SUPER:', self.super())
        print('access_flags - ACC_INTERFACE:', self.interface())
        print('access_flags - ACC_ABSTRACT:', self.abstract())
        print('access_flags - ACC_SYNTHETIC:', self.synthetic())
        print('access_flags - ACC_ANNOTATION:', self.annotation())
        print('access_flags - ACC_ENUM:', self.enum())


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
            print(prefix + 'access_flags - ACC_PUBLIC:', self.public())
            print(prefix + 'access_flags - ACC_PRIVATE:', self.public())
            print(prefix + 'access_flags - ACC_PROTECTED:', self.public())
            print(prefix + 'access_flags - ACC_STATIC:', self.public())
            print(prefix + 'access_flags - ACC_FINAL:', self.final())
            print(prefix + 'access_flags - ACC_VOLATILE:', self.volatile())
            print(prefix + 'access_flags - ACC_TRANSIENT:', self.transient())
            print(prefix + 'access_flags - ACC_SYNTHETIC:', self.synthetic())
            print(prefix + 'access_flags - ACC_ENUM:', self.enum())

    def parse(self, fd):
        self.__access_flags = Field.AccessFlags()
        self.__access_flags.parse(fd)
        self.__name_index = _read_u2_int(fd)
        self.__descriptor_index = _read_u2_int(fd)
        self.__attributes_count = _read_u2_int(fd)
        self.__attributes = []
        for _ in range(self.__attributes_count):
            attribute = Attribute()
            attribute.parse(fd)
            self.__attributes.append(attribute)

    def debug_info(self):
        print('Field  - name index:', self.__name_index)
        print('       - descriptor index:', self.__descriptor_index)
        self.__access_flags.debug_info('       - ')
        print('       - attributes count:', self.__attributes_count)
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
            print(prefix + 'access_flags - ACC_PUBLIC:', self.public())
            print(prefix + 'access_flags - ACC_PRIVATE:', self.public())
            print(prefix + 'access_flags - ACC_PROTECTED:', self.public())
            print(prefix + 'access_flags - ACC_STATIC:', self.public())
            print(prefix + 'access_flags - ACC_FINAL:', self.final())
            print(prefix + 'access_flags - ACC_SYNCHRONIZED:', self.synchronized())
            print(prefix + 'access_flags - ACC_BRIDGE:', self.bridge())
            print(prefix + 'access_flags - ACC_VARARGS:', self.varargs())
            print(prefix + 'access_flags - ACC_NATIVE:', self.native())
            print(prefix + 'access_flags - ACC_ABSTRACT:', self.abstract())
            print(prefix + 'access_flags - ACC_STRICT:', self.strict())
            print(prefix + 'access_flags - ACC_SYNTHETIC:', self.synthetic())

    def parse(self, fd):
        self.__access_flags = Method.AccessFlags()
        self.__access_flags.parse(fd)
        self.__name_index = _read_u2_int(fd)
        self.__descriptor_index = _read_u2_int(fd)
        self.__attributes_count = _read_u2_int(fd)
        self.__attributes = []
        for _ in range(self.__attributes_count):
            attribute = Attribute()
            attribute.parse(fd)
            self.__attributes.append(attribute)

    def debug_info(self):
        print('Method - name index:', self.__name_index)
        print('       - descriptor index:', self.__descriptor_index)
        self.__access_flags.debug_info('       - ')
        print('       - attributes count:', self.__attributes_count)
        for attr in self.__attributes:
            attr.debug_info('       - ')


class Attribute(object):
    def __init__(self):
        pass

    def parse(self, fd):
        self.__attribute_name_index = _read_u2_int(fd)
        self.__attribute_length = _read_u4_int(fd)
        self.__info = fd.read(self.__attribute_length)  # Let's do it latter

    def debug_info(self, prefix=''):
        print(prefix + 'Attribute name index:', self.__attribute_name_index)
        print(prefix + 'Attribute length:', self.__attribute_length)
