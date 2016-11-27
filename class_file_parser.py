'''Parse JVM class file, according JAVA SE 8 spec
'''
import struct


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
    CONSTANT_MethodHandle = 15
    CONSTANT_MethodType = 16
    CONSTANT_InvokeDynamic = 18

    def __init__(self, tag):
        self.__tag = tag

    def parse(self, fd):
        '''To be implement in children class
        '''
        raise NotImplementedError(
            'parse in _GenericConstant is not implemented.'
        )


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


class ConstantMethodref(_GenericConstant):
    '''The CONSTANT_Fieldref_info structure in constant_pool
    '''
    def __init__(self):
        super(ConstantMethodref, self).__init__(self.CONSTANT_Methodref)

    def parse(self, fd):
        self.__class_index = _read_u2_int(fd)
        self.__name_and_type_index = _read_u2_int(fd)
        # TODO: validate index must be a class type
        # In spec 4.4.2


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


class ConstantInteger(_GenericConstant):
    '''The CONSTANT_Integer_info Structure in constant_pool.
    '''
    def __init__(self):
        super(ConstantInteger, self).__init__(self.CONSTANT_Integer)

    def parse(self, fd):
        self.__value = _read_u4_int(fd)
        # In spec it's bytes, use veriable name __value.


class ConstantFloat(_GenericConstant):
    '''The CONSTANT_Float_info Structures in constant_pool.
    '''
    def __init__(self):
        super(ConstantFloat, self).__init__(self.CONSTANT_Float)

    def parse(self, fd):
        self.__value = _read_u4_float(fd)
        print('Read U4 float, need verify if it is correct:', self.__value)
        # In spec it's bytes, use veriable name __value.


class ConstantLong(_GenericConstant):
    '''The CONSTANT_Long_info represent 8-byte numeric long constants
    In python, use integer for long long C type
    '''
    def __init__(self):
        super(ConstantLong, self).__init__(self.CONSTANT_Long)

    def parse(self, fd):
        self.__value = _read_u8_int(fd)
        print('Read U8 long, need verify if it is correct:', self.__value)


class ConstantDouble(_GenericConstant):
    '''The CONSTANT_Double_info represent 8-byte numeric double constants
    In python, use float for double C type
    '''
    def __init__(self):
        super(ConstantDouble, self).__init__(self.CONSTANT_Double)

    def parse(self, fd):
        self.__value = _read_u8_float(fd)
        print('Read U8 double, need verify if it is correct:', self.__value)


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


class ConstantUtf8(_GenericConstant):
    '''The CONSTANT_Utf8_info structure is used to represent constant string values
    '''
    def __init__(self):
        super(ConstantUtf8, self).__init__(self.CONSTANT_Utf8)

    def parse(self, fd):
        length = _read_u2_int(fd)
        self.__str_value = _read_string(fd, length)


class ConstantMethodHandle(_GenericConstant):
    '''The CONSTANT_MethodHandle_info structure is used to represent a method handle
    '''
    def __init__(self):
        super(ConstantMethodHandle, self).__init__(self.CONSTANT_MethodHandle)

    def parse(self, fd):
        self.__reference_kind = _read_u1_int(fd)
        self.__reference_index = _read_u2_int(fd)
        # TODO: validate type and index after parse all
        # In spec 4.6.8


class ConstantMethodType(_GenericConstant):
    '''The CONSTANT_MethodType_info structure is used to represent a method type
    '''
    def __init__(self):
        super(ConstantMethodType, self).__init__(self.CONSTANT_MethodType)

    def parse(self, fd):
        self.__descriptor_index = _read_u2_int(fd)
        # TODO: validate  index after parse all
        # In spec 4.6.9


class ConstantInvokeDynamic(_GenericConstant):
    '''The CONSTANT_InvokeDynamic_info structure is used by an invokedynamic instruction
    to specify a bootstrap method
    '''
    def __init__(self):
        super(ConstantInvokeDynamic, self).__init__(self.CONSTANT_InvokeDynamic)

    def parse(self, fd):
        self.__bootstrap_method_attr_index = _read_u2_int(fd)
        self.__name_and_type_index = _read_u2_int(fd)
        # TODO: validate  index after parse all
        # In spec 4.6.10


class ClassFile(object):
    '''Class for parse and store a JAVA class file
    '''
    def __init__(self, fd):
        self.__magic = _read_u4_int(fd)
        print('READ magic:', self.__magic)
        print('expected magic:', 0xCAFEBABE)
        assert(self.__magic == 0xCAFEBABE)
        self.__minor_version = _read_u2_int(fd)
        self.__major_version = _read_u2_int(fd)
        self.__constant_pool_count = _read_u2_int(fd) - 1
        self.__constant_pool = []
        for _ in range(self.__constant_pool_count):
            self.__parse_constant_pool(fd)
        self.__validate_constant_pool()

    def __parse_constant_pool(self, fd):
        tag = _read_u1_int(fd)
        constant = None
        if tag == _GenericConstant.CONSTANT_Class:
            constant = ConstantClass()
        elif tag == _GenericConstant.CONSTANT_Fieldref:
            constant = ConstantFieldref()
        elif tag == _GenericConstant.CONSTANT_Methodref:
            constant = ConstantMethodref()
        elif tag == _GenericConstant.CONSTANT_InterfaceMethodref:
            constant = ConstantInterfaceMethodref()
        elif tag == _GenericConstant.CONSTANT_String:
            constant = ConstantString()
        elif tag == _GenericConstant.CONSTANT_Integer:
            constant = ConstantInteger()
        elif tag == _GenericConstant.CONSTANT_Float:
            constant = ConstantFloat()
        elif tag == _GenericConstant.CONSTANT_Long:
            constant = ConstantLong()
        elif tag == _GenericConstant.CONSTANT_Double:
            constant = ConstantDouble()
        elif tag == _GenericConstant.CONSTANT_NameAndType:
            constant = ConstantNameAndType()
        elif tag == _GenericConstant.CONSTANT_Utf8:
            constant = ConstantUtf8()
        elif tag == _GenericConstant.CONSTANT_MethodHandle:
            constant = ConstantMethodHandle()
        elif tag == _GenericConstant.CONSTANT_MethodType:
            constant = ConstantMethodType()
        elif tag == _GenericConstant.CONSTANT_InvokeDynamic:
            constant = ConstantInvokeDynamic()
        if not constant:
            raise NotImplementedError(
                'Constant tag {0} is not implemented in parse.'.format(constant)
            )
        constant.parse(fd)
        self.__constant_pool.append(constant)

    def __validate_constant_pool(self):
        '''Valid if constant_pool according to spec
        Raise ValueError if any fail validation
        '''
        pass

    def debug_info(self):
        print('Print class file info')
        print('Magic number: 0x{:X}'.format(self.__magic))
        print('Major version: ', self.__major_version)
        print('Monor version: ', self.__minor_version)
        print('Constant count: ', self.__constant_pool_count)


