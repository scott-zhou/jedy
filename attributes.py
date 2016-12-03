import logging
import read_bytes
import constant_pool


def parse(fd, class_file):
    '''Parse attributes
    '''
    count = read_bytes.read_u2_int(fd)
    attributes = []
    for _ in range(count):
        attr = parse_attr(fd, class_file)
        attributes.append(attr)
    return (count, attributes)


def parse_attr(fd, class_file):
    name_index = read_bytes.read_u2_int(fd)
    length = read_bytes.read_u4_int(fd)
    name_constant = class_file.constant(name_index)
    assert type(name_constant) == constant_pool.ConstantUtf8, 'Attribute name constant is not CONSTANT_Utf8_info.'
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


class Attribute(object):
    def __init__(self, name, length):
        self._name = name
        self._length = length

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
        self.__max_stack = read_bytes.read_u2_int(fd)
        self.__max_locals = read_bytes.read_u2_int(fd)
        self.__code_length = read_bytes.read_u4_int(fd)
        self.__code = fd.read(self.__code_length)
        self.__exception_table_length = read_bytes.read_u2_int(fd)
        self.__exception_table = []
        for _ in range(self.__exception_table_length):
            start_pc = read_bytes.read_u2_int(fd)
            end_pc = read_bytes.read_u2_int(fd)
            handler_pc = read_bytes.read_u2_int(fd)
            catch_type = read_bytes.read_u2_int(fd)
            self.__exception_table.append(tuple(start_pc, end_pc, handler_pc, catch_type))
        (self.__attributes_count, self.__attributes) = parse(fd, class_file)

    def debug_info(self, prefix=''):
        super().debug_info(prefix)
        logging.debug(prefix + 'code length:' + str(self.__code_length))
        logging.debug(prefix + 'attribute count:' + str(self.__attributes_count))
        for attr in self.__attributes:
            attr.debug_info(prefix + '       - ')


class StackMapFrame(object):
    pass


class StackMapTableAttribute(Attribute):
    def parse_info(self, fd, class_file):
        self.__number_of_entries = read_bytes.read_u2_int(fd)
        self.other = fd.read(self._length - 2)

    def debug_info(self, prefix=''):
        super().debug_info(prefix)
        logging.debug(prefix + 'Num of entries:' + str(self.__number_of_entries))
        logging.debug(prefix + 'bytes of entries:' + str(self.other))


class ExceptionsAttribute(Attribute):
    pass


class BootstrapMethodsAttribute(Attribute):
    pass
