import logging
from lib import read_bytes


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


class ConstantPool(object):
    def __init__(self, constant_pool_count):
        # index valid from 1 to constant_pool_count - 1
        # which means the max size is constant_pool_count - 1
        self.max_size = constant_pool_count - 1
        self.pool = []

    @property
    def count(self):
        return self.max_size + 1

    def append(self, constant):
        self.pool.append(constant)

    def __getitem__(self, index):
        assert index >= 1 and index <= self.max_size, 'Invalid constant index {0}'.format(index)
        return self.pool[index - 1]

    def get_constant_class_name(self, index):
        return self[self[index].name_index].value()


def parse(fd):
    '''Parse constant_pool
    The constant_pool table is indexed from 1 to constant_pool_count - 1.
    Which means the actual count is constant_pool_count - 1
    '''
    count = read_bytes.read_u2_int(fd)
    pool = ConstantPool(count)
    long_or_double = False
    for _ in range(count - 1):
        constant = parse_entry(fd, long_or_double)
        long_or_double = type(constant) in (ConstantLong, ConstantDouble)
        pool.append(constant)
    return pool


def parse_entry(fd, prev_long_or_double):
    '''Parse one constant in constant_pool. Set constant be unusable
    if previous constant is long or double.
    '''
    tag = read_bytes.read_u1_int(fd)
    constant_type = {
        CONSTANT_Class: ConstantClass,
        CONSTANT_Fieldref: ConstantFieldref,
        CONSTANT_Methodref: ConstantMethodref,
        CONSTANT_InterfaceMethodref: ConstantInterfaceMethodref,
        CONSTANT_String: ConstantString,
        CONSTANT_Integer: ConstantInteger,
        CONSTANT_Float: ConstantFloat,
        CONSTANT_Long: ConstantLong,
        CONSTANT_Double: ConstantDouble,
        CONSTANT_NameAndType: ConstantNameAndType,
        CONSTANT_Utf8: ConstantUtf8,
        CONSTANT_MethodHandle: ConstantMethodHandle,
        CONSTANT_MethodType: ConstantMethodType,
        CONSTANT_InvokeDynamic: ConstantInvokeDynamic
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


class GenericConstant(object):
    '''Base type for elements in constant_pool
    '''
    def __init__(self, tag):
        self.tag = tag
        self.usable = True

    def unuse(self):
        self.usable = False

    def debug_info(self, prefix, class_struct):
        pass


class ConstantClass(GenericConstant):
    '''The CONSTANT_Class_info structure in constant_pool,
    used to represent a class or an interface.
    '''
    def __init__(self):
        super().__init__(CONSTANT_Class)

    def parse(self, fd):
        self.name_index = read_bytes.read_u2_int(fd)
        # TODO: check index availability after pool parsed
        # In spec 4.4.1. The CONSTANT_Class_info Structure

    def debug_info(self, prefix, class_struct):
        class_name = class_struct.constant_pool[self.name_index].value()
        logging.debug(prefix + 'CONSTANT_Class_info - name_index:' + str(self.name_index) + ' ("{0}")'.format(class_name))


class FieldMethodInterfacemethodRef(GenericConstant):
    '''For 3 similar structures fields, methods, and interface methods
    '''
    def __init__(self, tag):
        super().__init__(tag)

    def parse(self, fd):
        self.class_index = read_bytes.read_u2_int(fd)
        self.name_and_type_index = read_bytes.read_u2_int(fd)

    def get_class(self, pool):
        class_info = pool[self.class_index]
        class_name = pool[class_info.name_index]
        return class_name.str_value

    def get_method(self, pool):
        name_type = pool[self.name_and_type_index]
        method_name = pool[name_type.name_index].str_value
        method_describ = pool[name_type.descriptor_index].str_value
        return method_name, method_describ


class ConstantFieldref(FieldMethodInterfacemethodRef):
    '''The CONSTANT_Fieldref_info structure in constant_pool
    '''
    def __init__(self):
        super().__init__(CONSTANT_Fieldref)

    def debug_info(self, prefix, class_struct):
        logging.debug(
            prefix +
            'CONSTANT_Fieldref_info - class_index:' +
            str(self.class_index) +
            '; name_and_type_index:' +
            str(self.name_and_type_index)
        )

    def get_method(self, pool):
        raise NotImplemented('Disable get_method function for field.')

    def get_name_descriptor(self, pool):
        name_type = pool[self.name_and_type_index]
        assert type(name_type) is ConstantNameAndType
        name = pool[name_type.name_index]
        field_descriptor = pool[name_type.descriptor_index]
        return name.value(), field_descriptor.value()


class ConstantMethodref(FieldMethodInterfacemethodRef):
    '''The ConstantMethodref structure in constant_pool
    '''
    def __init__(self):
        super().__init__(CONSTANT_Methodref)

    def debug_info(self, prefix, class_struct):
        logging.debug(
            prefix +
            'ConstantMethodref - class_index:' +
            str(self.class_index) +
            '; name_and_type_index:' +
            str(self.name_and_type_index)
        )


class ConstantInterfaceMethodref(FieldMethodInterfacemethodRef):
    '''The CONSTANT_Fieldref_info structure in constant_pool
    '''
    def __init__(self):
        super().__init__(CONSTANT_InterfaceMethodref)

    def debug_info(self, prefix, class_struct):
        logging.debug(
            prefix +
            'ConstantInterfaceMethodref - class_index:' +
            str(self.class_index) +
            '; name_and_type_index:' +
            str(self.name_and_type_index)
        )


class ConstantString(GenericConstant):
    '''The CONSTANT_String_info Structure in constant_pool,
    used to represent constant objects of the type String
    '''
    def __init__(self):
        super().__init__(CONSTANT_String)

    def parse(self, fd):
        self.string_index = read_bytes.read_u2_int(fd)
        # TODO: validate index entry must be a CONSTANT_Utf8_info structure
        # In spec 4.4.3

    def debug_info(self, prefix, class_struct):
        logging.debug(
            prefix +
            'CONSTANT_String_info - string_index:' +
            str(self.string_index)
        )


class ConstantInteger(GenericConstant):
    '''The CONSTANT_Integer_info Structure in constant_pool.
    '''
    def __init__(self):
        super().__init__(CONSTANT_Integer)

    def parse(self, fd):
        self.value = read_bytes.read_u4_int(fd)
        # In spec it's bytes, use veriable name __value.

    def debug_info(self, prefix, class_struct):
        logging.debug(
            prefix +
            'CONSTANT_Integer_info - value:' +
            str(self.value)
        )


class ConstantFloat(GenericConstant):
    '''The CONSTANT_Float_info Structures in constant_pool.
    '''
    def __init__(self):
        super().__init__(CONSTANT_Float)

    def parse(self, fd):
        self.value = read_bytes.read_u4_float(fd)
        # In spec it's bytes, use veriable name __value.

    def debug_info(self, prefix, class_struct):
        logging.debug(
            prefix +
            'CONSTANT_Float_info - value:' +
            str(self.value)
        )


class ConstantLong(GenericConstant):
    '''The CONSTANT_Long_info represent 8-byte numeric long constants
    In python, use integer for long long C type
    '''
    def __init__(self):
        super().__init__(CONSTANT_Long)

    def parse(self, fd):
        self.value = read_bytes.read_u8_int(fd)

    def debug_info(self, prefix, class_struct):
        logging.debug(
            prefix +
            'CONSTANT_Long_info - value:' +
            str(self.value)
        )


class ConstantDouble(GenericConstant):
    '''The CONSTANT_Double_info represent 8-byte numeric double constants
    In python, use float for double C type
    '''
    def __init__(self):
        super().__init__(CONSTANT_Double)

    def parse(self, fd):
        self.value = read_bytes.read_u8_float(fd)

    def debug_info(self, prefix, class_struct):
        logging.debug(
            prefix +
            'CONSTANT_Double_info - value:' +
            str(self.value)
        )


class ConstantNameAndType(GenericConstant):
    '''The CONSTANT_NameAndType_info structure is used to represent a field
    or method, without indicating which class or interface type it belongs to.
    '''
    def __init__(self):
        super().__init__(CONSTANT_NameAndType)

    def parse(self, fd):
        self.name_index = read_bytes.read_u2_int(fd)
        self.descriptor_index = read_bytes.read_u2_int(fd)
        # TODO: validate indexs in constant_pool after parse all
        # In spec 4.4.6

    def debug_info(self, prefix, class_struct):
        name = class_struct.constant_pool[self.name_index].value()
        descript = class_struct.constant_pool[self.descriptor_index].value()
        logging.debug(
            prefix +
            'CONSTANT_NameAndType_info - name_index:' +
            str(self.name_index) +
            ' ("{0}")'.format(name) +
            '; descriptor_index:' +
            str(self.descriptor_index) +
            ' ("{0}")'.format(descript)
        )


class ConstantUtf8(GenericConstant):
    '''The CONSTANT_Utf8_info structure is used to represent constant string values
    '''
    def __init__(self):
        super().__init__(CONSTANT_Utf8)

    def parse(self, fd):
        length = read_bytes.read_u2_int(fd)
        self.str_value = read_bytes.read_string(fd, length)

    def value(self):
        return self.str_value

    def debug_info(self, prefix, class_struct):
        logging.debug(
            prefix +
            'CONSTANT_Utf8_info - string value:' +
            str(self.str_value)
        )


class ConstantMethodHandle(GenericConstant):
    '''The CONSTANT_MethodHandle_info structure is used to represent
    a method handle
    '''
    def __init__(self):
        super().__init__(CONSTANT_MethodHandle)

    def parse(self, fd):
        self.reference_kind = read_bytes.read_u1_int(fd)
        self.reference_index = read_bytes.read_u2_int(fd)
        # TODO: validate type and index after parse all
        # In spec 4.6.8

    def debug_info(self, prefix, class_struct):
        logging.debug(
            prefix +
            'CONSTANT_MethodHandle_info - reference_kind:' +
            str(self.reference_kind) +
            '; reference_index:' +
            str(self.reference_index)
        )


class ConstantMethodType(GenericConstant):
    '''The CONSTANT_MethodType_info structure is used to represent
    a method type
    '''
    def __init__(self):
        super().__init__(CONSTANT_MethodType)

    def parse(self, fd):
        self.descriptor_index = read_bytes.read_u2_int(fd)
        # TODO: validate  index after parse all
        # In spec 4.6.9

    def debug_info(self, prefix, class_struct):
        logging.debug(
            prefix +
            'CONSTANT_MethodType_info - descriptor_index:' +
            str(self.descriptor_index)
        )


class ConstantInvokeDynamic(GenericConstant):
    '''The CONSTANT_InvokeDynamic_info structure is used by an
    invokedynamic instruction
    to specify a bootstrap method
    '''
    def __init__(self):
        super().__init__(CONSTANT_InvokeDynamic)

    def parse(self, fd):
        self.bootstrap_method_attr_index = read_bytes.read_u2_int(fd)
        self.name_and_type_index = read_bytes.read_u2_int(fd)
        # TODO: validate  index after parse all
        # In spec 4.6.10

    def debug_info(self, prefix, class_struct):
        logging.debug(
            prefix +
            'CONSTANT_InvokeDynamic_info - bootstrap_method_attr_index:' +
            str(self.bootstrap_method_attr_index) +
            '; name_and_type_index:' +
            str(self.name_and_type_index)
        )
