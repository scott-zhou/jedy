import logging
import read_bytes
import constant_pool


SAME = 0
SAME_LOCALS_1_STACK_ITEM = 64
SAME_LOCALS_1_STACK_ITEM_EXTENDED = 247
CHOP = 248
SAME_FRAME_EXTENDED = 251
APPEND = 252
FULL_FRAME = 255


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


class StackMapTableAttribute(Attribute):
    def parse_info(self, fd, class_file):
        self.__number_of_entries = read_bytes.read_u2_int(fd)
        self.__stack_map_frame_entries = []
        for _ in range(self.__number_of_entries):
            frame = parse_stack_map_frame(fd)
            self.__stack_map_frame_entries.append(frame)

    def debug_info(self, prefix=''):
        super().debug_info(prefix)
        logging.debug(prefix + 'Num of entries:' + str(self.__number_of_entries))
        for frame in self.__stack_map_frame_entries:
            pass
            # frame.debug_info(prefix + '       - ')


class ExceptionsAttribute(Attribute):
    pass


class BootstrapMethodsAttribute(Attribute):
    pass


class StackMapFrame(object):
    def __init__(self, frame_type):
        self.__frame_type = frame_type
        self.__offset_delta = 0

    def parse(self, fd):
        raise NotImplementedError('Parse not implemented for generic stack map frame.')

    def get_frame_type(self):
        return self.__frame_type

    def set_offset_delta(self, offset_delta):
        self.__offset_delta = offset_delta

    def get_offset_delta(self):
        return self.__offset_delta


class SameFrame(StackMapFrame):
    def __init__(self, frame_type):
        '''The offset_delta value for the frame is the value
        of the tag item, frame_type.
        '''
        super().__init__(SAME)
        self.set_offset_delta(frame_type)

    def parse(self, fd):
        pass


class SameLocals1StackItemFrame(StackMapFrame):
    def __init__(self, frame_type):
        '''The offset_delta value for the frame is given by
        the formula frame_type - 64
        '''
        super().__init__(SAME_LOCALS_1_STACK_ITEM)
        self.set_offset_delta(frame_type - 64)

    def parse(self, fd):
        self.__verification_type_info = parse_verification_type_info(fd)


class SameLocals1StackItemFrameExtended(StackMapFrame):
    def __init__(self, frame_type):
        super().__init__(SAME_LOCALS_1_STACK_ITEM_EXTENDED)

    def parse(self, fd):
        self.set_offset_delta(read_bytes.read_u2_int(fd))
        self.__verification_type_info = parse_verification_type_info(fd)


class ChopFrame(StackMapFrame):
    def __init__(self, frame_type):
        super().__init__(CHOP)
        self.__num_of_absent = 251 - frame_type

    def parse(self, fd):
        self.set_offset_delta(read_bytes.read_u2_int(fd))


class SameFrameExtended(StackMapFrame):
    def __init__(self, frame_type):
        super().__init__(SAME_FRAME_EXTENDED)

    def parse(self, fd):
        self.set_offset_delta(read_bytes.read_u2_int(fd))


class AppendFrame(StackMapFrame):
    def __init__(self, frame_type):
        super().__init__(APPEND)
        self.__locals = []
        self.__num_of_additional = frame_type - 251

    def parse(self, fd):
        self.set_offset_delta(read_bytes.read_u2_int(fd))
        for _ in range(self.__num_of_additional):
            v_type_info = parse_verification_type_info(fd)
            self.__locals.append(v_type_info)


class FullFrame(StackMapFrame):
    def __init__(self, frame_type):
        super().__init__(FULL_FRAME)
        self.__locals = []
        self.__stack = []

    def parse(self, fd):
        self.set_offset_delta(read_bytes.read_u2_int(fd))
        self.__number_of_locals = read_bytes.read_u2_int(fd)
        for _ in range(self.__number_of_locals):
            v_type_info = parse_verification_type_info(fd)
            self.__locals.append(v_type_info)
        self.__number_of_stack_items = read_bytes.read_u2_int(fd)
        for _ in range(self.__number_of_stack_items):
            v_type_info = parse_verification_type_info(fd)
            self.__stack.append(v_type_info)


_frame_type = {
    SAME: SameFrame,
    SAME_LOCALS_1_STACK_ITEM: SameLocals1StackItemFrame,
    SAME_LOCALS_1_STACK_ITEM_EXTENDED: SameLocals1StackItemFrameExtended,
    CHOP: ChopFrame,
    SAME_FRAME_EXTENDED: SameFrameExtended,
    APPEND: AppendFrame,
    FULL_FRAME: FullFrame
}


ITEM_Top = 0
ITEM_Integer = 1
ITEM_Float = 2
ITEM_Null = 5
ITEM_UninitializedThis = 6
ITEM_Object = 7
ITEM_Uninitialized = 8
ITEM_Long = 4
ITEM_Double = 3


def _convert_frame_type(frame_type):
    if frame_type in range(0, 64):
        return SAME
    if frame_type in range(64, 128):
        return SAME_LOCALS_1_STACK_ITEM
    if frame_type == 247:
        return SAME_LOCALS_1_STACK_ITEM_EXTENDED
    if frame_type in range(248, 251):
        return CHOP
    if frame_type == 251:
        return SAME_FRAME_EXTENDED
    if frame_type in range(252, 255):
        return APPEND
    if frame_type == 255:
        return FULL_FRAME
    raise ValueError('Invalid frame type value {0}'.format(frame_type))


def parse_stack_map_frame(fd):
    frame_type = read_bytes.read_u1_int(fd)
    cvt_type = _convert_frame_type(frame_type)
    frame_class = _frame_type[cvt_type]
    frame = frame_class(frame_type)
    frame.parse(fd)
    return frame


def parse_verification_type_info(fd):
    tag = read_bytes.read_u1_int(fd)
    if tag in (
        ITEM_Top,
        ITEM_Integer,
        ITEM_Float,
        ITEM_Null,
        ITEM_UninitializedThis,
        ITEM_Long,
        ITEM_Double
    ):
        return (tag, None)
    if tag == ITEM_Object:
        cpool_index = read_bytes.read_u2_int(fd)
        return (tag, cpool_index)
    if tag == ITEM_Uninitialized:
        offset = read_bytes.read_u2_int(fd)
        return (tag, offset)
    raise ValueError('Invalid verification_type_info tag value {0}'.format(tag))
