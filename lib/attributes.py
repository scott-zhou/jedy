import logging
from lib import read_bytes
from lib import constant_pool
from lib import instruction


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
        self.name = name
        self.length = length

    def parse_info(self, fd, class_file):
        self.info = fd.read(self.length)

    def debug_info(self, prefix=''):
        logging.debug(prefix + 'Attribute name:' + str(self.name))
        logging.debug(prefix + 'Attribute length:' + str(self.length))


'''Five critical attributes to correct interpretation of the class file'''


class ConstantValueAttribute(Attribute):
    pass


class CodeAttribute(Attribute):
    def code_to_instructions(self):
        pos = 0
        while pos < len(self.code):
            byte = self.code[pos]
            if byte not in instruction.BYTECODE:
                logging.warning('Not recognized instruction 0x{:02X} at pos {pos}, ignore the following parts in code.'.format(byte, pos=pos))
                break
            inst = instruction.BYTECODE[byte](pos)
            operands_start = pos + 1
            operands_end = operands_start + inst.len_of_operand()
            operands = bytes(self.code[operands_start:operands_end])
            inst.put_operands(operands)
            self.instructions.append(inst)
            pos = operands_end

    def parse_info(self, fd, class_file):
        self.max_stack = read_bytes.read_u2_int(fd)
        self.max_locals = read_bytes.read_u2_int(fd)
        self.code_length = read_bytes.read_u4_int(fd)
        self.code = fd.read(self.code_length)
        self.exception_table_length = read_bytes.read_u2_int(fd)
        self.exception_table = []
        for _ in range(self.exception_table_length):
            start_pc = read_bytes.read_u2_int(fd)
            end_pc = read_bytes.read_u2_int(fd)
            handler_pc = read_bytes.read_u2_int(fd)
            catch_type = read_bytes.read_u2_int(fd)
            self.exception_table.append(tuple(start_pc, end_pc, handler_pc, catch_type))
        (self.attributes_count, self.attributes) = parse(fd, class_file)
        self.instructions = []
        self.code_to_instructions()

    def debug_info(self, prefix=''):
        super().debug_info(prefix)
        logging.debug(prefix + 'max stack:' + str(self.max_stack))
        logging.debug(prefix + 'max locals:' + str(self.max_locals))
        logging.debug(prefix + 'code length:' + str(self.code_length))
        logging.debug(prefix + 'code: ' + ' '.join('0x{:02X}'.format(i) for i in self.code))
        logging.debug(prefix + 'attribute count:' + str(self.attributes_count))
        for attr in self.attributes:
            attr.debug_info(prefix + '       - ')


class StackMapTableAttribute(Attribute):
    '''A StackMapTable attribute is used during the process of
    verification by type checking, which maybe means, I can ignore
    it now.
    '''
    def parse_info(self, fd, class_file):
        self.number_of_entries = read_bytes.read_u2_int(fd)
        self.stack_map_frame_entries = []
        for _ in range(self.number_of_entries):
            frame = parse_stack_map_frame(fd)
            self.stack_map_frame_entries.append(frame)

    def debug_info(self, prefix=''):
        super().debug_info(prefix)
        logging.debug(prefix + 'Num of entries:' + str(self.number_of_entries))
        for frame in self.stack_map_frame_entries:
            frame.debug_info(prefix + '       - ')


class ExceptionsAttribute(Attribute):
    pass


class BootstrapMethodsAttribute(Attribute):
    pass


class StackMapFrame(object):
    def __init__(self, frame_type):
        self.frame_type = frame_type
        self.offset_delta = 0

    def parse(self, fd):
        raise NotImplementedError('Parse not implemented for generic stack map frame.')

    def debug_info(self, prefix):
        logging.debug(prefix + type(self).__name__ + ', offset delta {offset}'.format(offset=self.offset_delta))


class SameFrame(StackMapFrame):
    def __init__(self, frame_type):
        '''The offset_delta value for the frame is the value
        of the tag item, frame_type.
        '''
        super().__init__(SAME)
        self.offset_delta = frame_type

    def parse(self, fd):
        pass


class SameLocals1StackItemFrame(StackMapFrame):
    def __init__(self, frame_type):
        '''The offset_delta value for the frame is given by
        the formula frame_type - 64
        '''
        super().__init__(SAME_LOCALS_1_STACK_ITEM)
        self.offset_delta = frame_type - 64

    def parse(self, fd):
        self.verification_type_info = parse_verification_type_info(fd)


class SameLocals1StackItemFrameExtended(StackMapFrame):
    def __init__(self, frame_type):
        super().__init__(SAME_LOCALS_1_STACK_ITEM_EXTENDED)

    def parse(self, fd):
        self.offset_delta = read_bytes.read_u2_int(fd)
        self.verification_type_info = parse_verification_type_info(fd)


class ChopFrame(StackMapFrame):
    def __init__(self, frame_type):
        super().__init__(CHOP)
        self.num_of_absent = 251 - frame_type

    def parse(self, fd):
        self.offset_delta = read_bytes.read_u2_int(fd)


class SameFrameExtended(StackMapFrame):
    def __init__(self, frame_type):
        super().__init__(SAME_FRAME_EXTENDED)

    def parse(self, fd):
        self.offset_delta = read_bytes.read_u2_int(fd)


class AppendFrame(StackMapFrame):
    def __init__(self, frame_type):
        super().__init__(APPEND)
        self.locals = []
        self.num_of_additional = frame_type - 251

    def parse(self, fd):
        self.offset_delta = read_bytes.read_u2_int(fd)
        for _ in range(self.num_of_additional):
            v_type_info = parse_verification_type_info(fd)
            self.locals.append(v_type_info)


class FullFrame(StackMapFrame):
    def __init__(self, frame_type):
        super().__init__(FULL_FRAME)
        self.locals = []
        self.stack = []

    def parse(self, fd):
        self.offset_delta = read_bytes.read_u2_int(fd)
        self.number_of_locals = read_bytes.read_u2_int(fd)
        for _ in range(self.number_of_locals):
            v_type_info = parse_verification_type_info(fd)
            self.locals.append(v_type_info)
        self.number_of_stack_items = read_bytes.read_u2_int(fd)
        for _ in range(self.number_of_stack_items):
            v_type_info = parse_verification_type_info(fd)
            self.stack.append(v_type_info)


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
