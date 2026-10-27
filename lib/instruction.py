'''JVM instructions, according JVM spec (Java SE 8 Edition) chapter 6.

Each instruction object is created when the method code is parsed, and only
holds the decoded operands. `execute(frame, thread)` executes the
instruction on the frame, returns True if the current frame is changed
(invoke a method, return from method), so the interpreter loop should
reload the top frame.

Category 2 values (long and double) take two slots in operand stack and
local variables, the value is in the first slot and the second slot is
filled with frame.PAD.
'''
import math
import struct
from lib import constant_pool
from lib import run_time_data
from lib import class_loader
from lib.frame import PAD

OPCODES = {}


def bytecode(code):
    def bytecode_decorator(klass):
        OPCODES[code] = klass
        return klass
    return bytecode_decorator


def i32(value):
    return ((value + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def i64(value):
    return ((value + 0x8000000000000000) & 0xFFFFFFFFFFFFFFFF) - \
        0x8000000000000000


def f32(value):
    '''Round python float (double) to float precision'''
    try:
        return struct.unpack('>f', struct.pack('>f', value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def _java_div(value1, value2):
    '''Integer division which rounds towards 0'''
    q = abs(value1) // abs(value2)
    return q if (value1 >= 0) == (value2 >= 0) else -q


def _java_rem(value1, value2):
    return value1 - _java_div(value1, value2) * value2


def _float_div(value1, value2):
    try:
        return value1 / value2
    except ZeroDivisionError:
        if value1 == 0 or math.isnan(value1):
            return math.nan
        return math.copysign(math.inf, value1) * math.copysign(1, value2)


def _float_rem(value1, value2):
    if value2 == 0 or math.isinf(value1) or math.isnan(value2):
        return math.nan
    if math.isinf(value2):
        return value1
    return math.fmod(value1, value2)


def _float_to_int(value, bits):
    if math.isnan(value):
        return 0
    max_value = (1 << (bits - 1)) - 1
    min_value = -(1 << (bits - 1))
    if value >= max_value:
        return max_value
    if value <= min_value:
        return min_value
    return int(value)


def _float_cmp(value1, value2, nan_result):
    if math.isnan(value1) or math.isnan(value2):
        return nan_result
    if value1 > value2:
        return 1
    if value1 == value2:
        return 0
    return -1


class _instruction(object):
    def __init__(self, address):
        self.address = address
        self.next_pc = None

    def len_of_operand(self):
        return 0

    def put_operands(self, operand_bytes):
        pass

    def decode(self, code):
        '''Decode operands from method code, return the address of next
        instruction.
        '''
        start = self.address + 1
        end = start + self.len_of_operand()
        self.put_operands(bytes(code[start:end]))
        return end

    def class_name_and_address(self):
        return '{name} (addr:{address})'.format(
            name=type(self).__name__, address=self.address)

    def execute(self, frame, thread):
        raise NotImplementedError(
            'execute in base instruction is not implemented, '
            f'instruction {self.class_name_and_address()}')


class _u1_index_instruction(_instruction):
    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        self.index = operand_bytes[0]


class _u2_index_instruction(_instruction):
    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        self.index = int.from_bytes(
            operand_bytes, byteorder='big', signed=False)


class _branch_instruction(_instruction):
    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        self.offset = int.from_bytes(
            operand_bytes, byteorder='big', signed=True)
        self.jump_to_address = self.address + self.offset


@bytecode(0x00)
class nop(_instruction):
    def execute(self, frame, thread):
        pass


@bytecode(0x01)
class aconst_null(_instruction):
    def execute(self, frame, thread):
        frame.operand_stack.append(None)


class iconst_i(_instruction):
    '''Push constant value onto operand stack'''
    category2 = False

    def __init__(self, address, i=0):
        super().__init__(address)
        self.i = i

    def execute(self, frame, thread):
        frame.operand_stack.append(self.i)
        if self.category2:
            frame.operand_stack.append(PAD)


def _const_instruction(code, name, value, category2=False):
    def __init__(self, address):
        iconst_i.__init__(self, address, value)
    klass = type(name, (iconst_i,), {
        '__init__': __init__, 'category2': category2})
    bytecode(code)(klass)
    globals()[name] = klass


for _i, _name in enumerate(
        ['iconst_m1', 'iconst_0', 'iconst_1', 'iconst_2', 'iconst_3',
         'iconst_4', 'iconst_5']):
    _const_instruction(0x02 + _i, _name, _i - 1)
_const_instruction(0x09, 'lconst_0', 0, True)
_const_instruction(0x0a, 'lconst_1', 1, True)
_const_instruction(0x0b, 'fconst_0', 0.0)
_const_instruction(0x0c, 'fconst_1', 1.0)
_const_instruction(0x0d, 'fconst_2', 2.0)
_const_instruction(0x0e, 'dconst_0', 0.0, True)
_const_instruction(0x0f, 'dconst_1', 1.0, True)


@bytecode(0x10)
class bipush(iconst_i):
    def __init__(self, address):
        super().__init__(address)

    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        self.i = int.from_bytes(operand_bytes, byteorder='big', signed=True)


@bytecode(0x11)
class sipush(iconst_i):
    def __init__(self, address):
        super().__init__(address)

    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 2
        self.i = int.from_bytes(operand_bytes, byteorder='big', signed=True)


def _load_constant(frame, index):
    pool = frame.klass.constant_pool
    constant = pool[index]
    constant_type = type(constant)
    if constant_type is constant_pool.ConstantString:
        return run_time_data.java_string(pool[constant.string_index].value())
    if constant_type in (
        constant_pool.ConstantInteger,
        constant_pool.ConstantFloat,
        constant_pool.ConstantLong,
        constant_pool.ConstantDouble,
    ):
        return constant.value
    if constant_type is constant_pool.ConstantClass:
        return run_time_data.class_mirror(
            pool[constant.name_index].value())
    raise NotImplementedError(
        f'Load constant type {constant_type} is not supported yet')


@bytecode(0x12)
class ldc(_u1_index_instruction):
    def execute(self, frame, thread):
        frame.operand_stack.append(_load_constant(frame, self.index))


@bytecode(0x13)
class ldc_w(_u2_index_instruction):
    def execute(self, frame, thread):
        frame.operand_stack.append(_load_constant(frame, self.index))


@bytecode(0x14)
class ldc2_w(_u2_index_instruction):
    def execute(self, frame, thread):
        frame.operand_stack.append(_load_constant(frame, self.index))
        frame.operand_stack.append(PAD)


class _load_n(_instruction):
    '''Load value from local variable n'''
    category2 = False

    def __init__(self, address, n=0):
        super().__init__(address)
        self.n = n

    def execute(self, frame, thread):
        frame.operand_stack.append(frame.local_variables[self.n])
        if self.category2:
            frame.operand_stack.append(PAD)


class _load(_load_n):
    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        self.n = operand_bytes[0]


class _store_n(_instruction):
    '''Store value into local variable n'''
    category2 = False

    def __init__(self, address, n=0):
        super().__init__(address)
        self.n = n

    def execute(self, frame, thread):
        if self.category2:
            frame.operand_stack.pop()
            frame.local_variables[self.n] = frame.operand_stack.pop()
            frame.local_variables[self.n + 1] = PAD
        else:
            frame.local_variables[self.n] = frame.operand_stack.pop()


class _store(_store_n):
    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        self.n = operand_bytes[0]


def _local_variable_instructions():
    for kind, (base_code, base_n_code, base_class, base_n_class) in {
        'load': (0x15, 0x1a, _load, _load_n),
        'store': (0x36, 0x3b, _store, _store_n),
    }.items():
        for t_index, t in enumerate('ilfda'):
            category2 = t in 'ld'
            name = f'{t}{kind}'
            klass = type(name, (base_class,), {'category2': category2})
            bytecode(base_code + t_index)(klass)
            globals()[name] = klass
            n_base = type(f'{t}{kind}_n', (base_n_class,), {
                'category2': category2})
            globals()[f'{t}{kind}_n'] = n_base
            for n in range(4):
                name = f'{t}{kind}_{n}'

                def __init__(self, address, n=n, n_base=n_base):
                    n_base.__init__(self, address, n)
                klass = type(name, (n_base,), {'__init__': __init__})
                bytecode(base_n_code + t_index * 4 + n)(klass)
                globals()[name] = klass


_local_variable_instructions()


def _check_array_index(thread, array, index):
    if array is None:
        thread.throw_new('java/lang/NullPointerException')
    if index < 0 or index >= len(array.values):
        thread.throw_new(
            'java/lang/ArrayIndexOutOfBoundsException', str(index))


class _array_load(_instruction):
    category2 = False

    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        index = operand_stack.pop()
        array = operand_stack.pop()
        _check_array_index(thread, array, index)
        operand_stack.append(array.values[index])
        if self.category2:
            operand_stack.append(PAD)


class _array_store(_instruction):
    category2 = False

    def convert(self, array, value):
        return value

    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        if self.category2:
            operand_stack.pop()
        value = operand_stack.pop()
        index = operand_stack.pop()
        array = operand_stack.pop()
        _check_array_index(thread, array, index)
        array.values[index] = self.convert(array, value)


def _array_instructions():
    for t_index, t in enumerate('ilfdabcs'):
        category2 = t in 'ld'
        name = f'{t}aload'
        klass = type(name, (_array_load,), {'category2': category2})
        bytecode(0x2e + t_index)(klass)
        globals()[name] = klass
        name = f'{t}astore'
        klass = type(name, (_array_store,), {'category2': category2})
        bytecode(0x4f + t_index)(klass)
        globals()[name] = klass


_array_instructions()


def _bastore_convert(self, array, value):
    if array.array_type == '[Z':
        return value & 1
    return ((value + 0x80) & 0xFF) - 0x80


bastore.convert = _bastore_convert  # noqa: F821
castore.convert = lambda self, array, value: value & 0xFFFF  # noqa: F821
sastore.convert = \
    lambda self, array, value: ((value + 0x8000) & 0xFFFF) - 0x8000  # noqa


@bytecode(0x57)
class pop(_instruction):
    def execute(self, frame, thread):
        frame.operand_stack.pop()


@bytecode(0x58)
class pop2(_instruction):
    def execute(self, frame, thread):
        del frame.operand_stack[-2:]


@bytecode(0x59)
class dup(_instruction):
    def execute(self, frame, thread):
        frame.operand_stack.append(frame.operand_stack[-1])


@bytecode(0x5a)
class dup_x1(_instruction):
    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        operand_stack.insert(-2, operand_stack[-1])


@bytecode(0x5b)
class dup_x2(_instruction):
    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        operand_stack.insert(-3, operand_stack[-1])


@bytecode(0x5c)
class dup2(_instruction):
    def execute(self, frame, thread):
        frame.operand_stack.extend(frame.operand_stack[-2:])


@bytecode(0x5d)
class dup2_x1(_instruction):
    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        top = operand_stack[-2:]
        operand_stack[-3:-3] = top


@bytecode(0x5e)
class dup2_x2(_instruction):
    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        top = operand_stack[-2:]
        operand_stack[-4:-4] = top


@bytecode(0x5f)
class swap(_instruction):
    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        operand_stack[-1], operand_stack[-2] = \
            operand_stack[-2], operand_stack[-1]


class _binary_op(_instruction):
    '''Binary operation on two category 1 values'''

    def op(self, thread, value1, value2):
        raise NotImplementedError

    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        value2 = operand_stack.pop()
        value1 = operand_stack[-1]
        operand_stack[-1] = self.op(thread, value1, value2)


class _binary_op2(_instruction):
    '''Binary operation on two category 2 values'''

    def op(self, thread, value1, value2):
        raise NotImplementedError

    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        value2 = operand_stack[-2]
        value1 = operand_stack[-4]
        del operand_stack[-2:]
        operand_stack[-2] = self.op(thread, value1, value2)


class _shift_op2(_instruction):
    '''Shift long value by int value'''

    def op(self, value1, value2):
        raise NotImplementedError

    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        value2 = operand_stack.pop()
        operand_stack[-2] = self.op(operand_stack[-2], value2 & 0x3F)


def _div_by_zero(thread):
    thread.throw_new('java/lang/ArithmeticException', '/ by zero')


def _idiv(self, thread, value1, value2):
    if value2 == 0:
        _div_by_zero(thread)
    return i32(_java_div(value1, value2))


def _ldiv(self, thread, value1, value2):
    if value2 == 0:
        _div_by_zero(thread)
    return i64(_java_div(value1, value2))


def _irem(self, thread, value1, value2):
    if value2 == 0:
        _div_by_zero(thread)
    return i32(_java_rem(value1, value2))


def _lrem(self, thread, value1, value2):
    if value2 == 0:
        _div_by_zero(thread)
    return i64(_java_rem(value1, value2))


def _arithmetic_instructions():
    ops = [
        # name, code, base, function
        ('iadd', 0x60, _binary_op, lambda s, t, a, b: i32(a + b)),
        ('ladd', 0x61, _binary_op2, lambda s, t, a, b: i64(a + b)),
        ('fadd', 0x62, _binary_op, lambda s, t, a, b: f32(a + b)),
        ('dadd', 0x63, _binary_op2, lambda s, t, a, b: a + b),
        ('isub', 0x64, _binary_op, lambda s, t, a, b: i32(a - b)),
        ('lsub', 0x65, _binary_op2, lambda s, t, a, b: i64(a - b)),
        ('fsub', 0x66, _binary_op, lambda s, t, a, b: f32(a - b)),
        ('dsub', 0x67, _binary_op2, lambda s, t, a, b: a - b),
        ('imul', 0x68, _binary_op, lambda s, t, a, b: i32(a * b)),
        ('lmul', 0x69, _binary_op2, lambda s, t, a, b: i64(a * b)),
        ('fmul', 0x6a, _binary_op, lambda s, t, a, b: f32(a * b)),
        ('dmul', 0x6b, _binary_op2, lambda s, t, a, b: a * b),
        ('idiv', 0x6c, _binary_op, _idiv),
        ('ldiv', 0x6d, _binary_op2, _ldiv),
        ('fdiv', 0x6e, _binary_op,
         lambda s, t, a, b: f32(_float_div(a, b))),
        ('ddiv', 0x6f, _binary_op2, lambda s, t, a, b: _float_div(a, b)),
        ('irem', 0x70, _binary_op, _irem),
        ('lrem', 0x71, _binary_op2, _lrem),
        ('frem', 0x72, _binary_op,
         lambda s, t, a, b: f32(_float_rem(a, b))),
        ('drem', 0x73, _binary_op2, lambda s, t, a, b: _float_rem(a, b)),
        ('ishl', 0x78, _binary_op, lambda s, t, a, b: i32(a << (b & 0x1F))),
        ('ishr', 0x7a, _binary_op, lambda s, t, a, b: a >> (b & 0x1F)),
        ('iushr', 0x7c, _binary_op,
         lambda s, t, a, b: i32((a & 0xFFFFFFFF) >> (b & 0x1F))),
        ('iand', 0x7e, _binary_op, lambda s, t, a, b: a & b),
        ('land', 0x7f, _binary_op2, lambda s, t, a, b: a & b),
        ('ior', 0x80, _binary_op, lambda s, t, a, b: a | b),
        ('lor', 0x81, _binary_op2, lambda s, t, a, b: a | b),
        ('ixor', 0x82, _binary_op, lambda s, t, a, b: a ^ b),
        ('lxor', 0x83, _binary_op2, lambda s, t, a, b: a ^ b),
        ('lshl', 0x79, _shift_op2, lambda s, a, b: i64(a << b)),
        ('lshr', 0x7b, _shift_op2, lambda s, a, b: a >> b),
        ('lushr', 0x7d, _shift_op2,
         lambda s, a, b: i64((a & 0xFFFFFFFFFFFFFFFF) >> b)),
    ]
    for name, code, base, function in ops:
        klass = type(name, (base,), {'op': function})
        bytecode(code)(klass)
        globals()[name] = klass


_arithmetic_instructions()


@bytecode(0x74)
class ineg(_instruction):
    def execute(self, frame, thread):
        frame.operand_stack[-1] = i32(-frame.operand_stack[-1])


@bytecode(0x75)
class lneg(_instruction):
    def execute(self, frame, thread):
        frame.operand_stack[-2] = i64(-frame.operand_stack[-2])


@bytecode(0x76)
class fneg(_instruction):
    def execute(self, frame, thread):
        frame.operand_stack[-1] = -frame.operand_stack[-1]


@bytecode(0x77)
class dneg(_instruction):
    def execute(self, frame, thread):
        frame.operand_stack[-2] = -frame.operand_stack[-2]


@bytecode(0x84)
class iinc(_instruction):
    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 2
        self.index = int.from_bytes(
            operand_bytes[:1], byteorder='big', signed=False)
        self.const = int.from_bytes(
            operand_bytes[1:], byteorder='big', signed=True)

    def execute(self, frame, thread):
        frame.local_variables[self.index] = \
            i32(frame.local_variables[self.index] + self.const)


class _conversion(_instruction):
    '''Convert the value on top of operand stack. `from2` and `to2` are
    True if the type converted from or to is category 2.
    '''
    from2 = False
    to2 = False

    def convert(self, value):
        raise NotImplementedError

    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        if self.from2:
            operand_stack.pop()
        value = self.convert(operand_stack.pop())
        operand_stack.append(value)
        if self.to2:
            operand_stack.append(PAD)


def _conversion_instructions():
    conversions = [
        ('i2l', 0x85, False, True, lambda s, v: v),
        ('i2f', 0x86, False, False, lambda s, v: f32(float(v))),
        ('i2d', 0x87, False, True, lambda s, v: float(v)),
        ('l2i', 0x88, True, False, lambda s, v: i32(v)),
        ('l2f', 0x89, True, False, lambda s, v: f32(float(v))),
        ('l2d', 0x8a, True, True, lambda s, v: float(v)),
        ('f2i', 0x8b, False, False, lambda s, v: _float_to_int(v, 32)),
        ('f2l', 0x8c, False, True, lambda s, v: _float_to_int(v, 64)),
        ('f2d', 0x8d, False, True, lambda s, v: v),
        ('d2i', 0x8e, True, False, lambda s, v: _float_to_int(v, 32)),
        ('d2l', 0x8f, True, True, lambda s, v: _float_to_int(v, 64)),
        ('d2f', 0x90, True, False, lambda s, v: f32(v)),
        ('i2b', 0x91, False, False, lambda s, v: ((v + 0x80) & 0xFF) - 0x80),
        ('i2c', 0x92, False, False, lambda s, v: v & 0xFFFF),
        ('i2s', 0x93, False, False,
         lambda s, v: ((v + 0x8000) & 0xFFFF) - 0x8000),
    ]
    for name, code, from2, to2, function in conversions:
        klass = type(name, (_conversion,), {
            'from2': from2, 'to2': to2, 'convert': function})
        bytecode(code)(klass)
        globals()[name] = klass


_conversion_instructions()


@bytecode(0x94)
class lcmp(_binary_op2):
    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        value2 = operand_stack[-2]
        value1 = operand_stack[-4]
        del operand_stack[-4:]
        operand_stack.append(
            1 if value1 > value2 else (0 if value1 == value2 else -1))


@bytecode(0x95)
class fcmpl(_binary_op):
    def op(self, thread, value1, value2):
        return _float_cmp(value1, value2, -1)


@bytecode(0x96)
class fcmpg(_binary_op):
    def op(self, thread, value1, value2):
        return _float_cmp(value1, value2, 1)


@bytecode(0x97)
class dcmpl(_instruction):
    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        value2 = operand_stack[-2]
        value1 = operand_stack[-4]
        del operand_stack[-4:]
        operand_stack.append(_float_cmp(value1, value2, -1))


@bytecode(0x98)
class dcmpg(_instruction):
    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        value2 = operand_stack[-2]
        value1 = operand_stack[-4]
        del operand_stack[-4:]
        operand_stack.append(_float_cmp(value1, value2, 1))


class if_cond(_branch_instruction):
    '''Branch if int comparison with zero succeeds'''

    def cmp(self, value):
        raise NotImplementedError

    def execute(self, frame, thread):
        if self.cmp(frame.operand_stack.pop()):
            frame.pc = self.jump_to_address


@bytecode(0x99)
class ifeq(if_cond):
    def cmp(self, value):
        return value == 0


@bytecode(0x9a)
class ifne(if_cond):
    def cmp(self, value):
        return value != 0


@bytecode(0x9b)
class iflt(if_cond):
    def cmp(self, value):
        return value < 0


@bytecode(0x9c)
class ifge(if_cond):
    def cmp(self, value):
        return value >= 0


@bytecode(0x9d)
class ifgt(if_cond):
    def cmp(self, value):
        return value > 0


@bytecode(0x9e)
class ifle(if_cond):
    def cmp(self, value):
        return value <= 0


@bytecode(0xc6)
class ifnull(if_cond):
    def cmp(self, value):
        return value is None


@bytecode(0xc7)
class ifnonnull(if_cond):
    def cmp(self, value):
        return value is not None


class if_icmpcond(_branch_instruction):
    def execute(self, frame, thread):
        value2 = frame.operand_stack.pop()
        value1 = frame.operand_stack.pop()
        if self.cmp(value1, value2):
            frame.pc = self.jump_to_address

    def cmp(self, value1, value2):
        raise NotImplementedError(
            'cmp function in if_icmpcond will not be implement.')


@bytecode(0x9f)
class if_icmpeq(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 == value2


@bytecode(0xa0)
class if_icmpne(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 != value2


@bytecode(0xa1)
class if_icmplt(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 < value2


@bytecode(0xa2)
class if_icmpge(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 >= value2


@bytecode(0xa3)
class if_icmpgt(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 > value2


@bytecode(0xa4)
class if_icmple(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 <= value2


@bytecode(0xa5)
class if_acmpeq(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 is value2


@bytecode(0xa6)
class if_acmpne(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 is not value2


@bytecode(0xa7)
class goto(_branch_instruction):
    def execute(self, frame, thread):
        frame.pc = self.jump_to_address


@bytecode(0xc8)
class goto_w(_branch_instruction):
    def len_of_operand(self):
        return 4

    def execute(self, frame, thread):
        frame.pc = self.jump_to_address


def _read_s4(code, pos):
    return int.from_bytes(code[pos:pos + 4], byteorder='big', signed=True)


@bytecode(0xaa)
class tableswitch(_instruction):
    def decode(self, code):
        pos = self.address + 1
        pos += (4 - pos % 4) % 4
        self.default = self.address + _read_s4(code, pos)
        self.low = _read_s4(code, pos + 4)
        self.high = _read_s4(code, pos + 8)
        pos += 12
        self.jump_offsets = []
        for _ in range(self.high - self.low + 1):
            self.jump_offsets.append(self.address + _read_s4(code, pos))
            pos += 4
        return pos

    def execute(self, frame, thread):
        index = frame.operand_stack.pop()
        if self.low <= index <= self.high:
            frame.pc = self.jump_offsets[index - self.low]
        else:
            frame.pc = self.default


@bytecode(0xab)
class lookupswitch(_instruction):
    def decode(self, code):
        pos = self.address + 1
        pos += (4 - pos % 4) % 4
        self.default = self.address + _read_s4(code, pos)
        npairs = _read_s4(code, pos + 4)
        pos += 8
        self.pairs = {}
        for _ in range(npairs):
            self.pairs[_read_s4(code, pos)] = \
                self.address + _read_s4(code, pos + 4)
            pos += 8
        return pos

    def execute(self, frame, thread):
        key = frame.operand_stack.pop()
        frame.pc = self.pairs.get(key, self.default)


class _return(_instruction):
    category2 = False

    def execute(self, frame, thread):
        operand_stack = frame.operand_stack
        if self.category2:
            operand_stack.pop()
        thread.method_return(frame, operand_stack.pop(), self.category2)
        return True


@bytecode(0xac)
class ireturn(_return):
    pass


@bytecode(0xad)
class lreturn(_return):
    category2 = True


@bytecode(0xae)
class freturn(_return):
    pass


@bytecode(0xaf)
class dreturn(_return):
    category2 = True


@bytecode(0xb0)
class areturn(_return):
    pass


@bytecode(0xb1)
class instruction_return(_instruction):
    def execute(self, frame, thread):
        thread.method_return(frame, None)
        return True


class _field_instruction(_u2_index_instruction):
    def resolve(self, frame):
        '''Resolve the field reference, return the declaring class, field
        name and field descriptor.
        '''
        pool = frame.klass.constant_pool
        field_ref = pool[self.index]
        assert type(field_ref) is constant_pool.ConstantFieldref
        class_name = field_ref.get_class(pool)
        name, field_descriptor = field_ref.get_name_descriptor(pool)
        klass = run_time_data.method_area[class_name]
        declaring_class = klass.field_resolution(name, field_descriptor)
        assert declaring_class, \
            f'NoSuchFieldError: {class_name}.{name} {field_descriptor}'
        self.category2 = field_descriptor in ('J', 'D')
        return declaring_class, name, field_descriptor


class _static_field_instruction(_field_instruction):
    def resolve_static(self, frame, thread):
        declaring_class, name, field_descriptor = self.resolve(frame)
        class_loader.initialize_class(declaring_class, thread)
        self.declaring_class = declaring_class
        self.static_fields = \
            run_time_data.class_static_fields[declaring_class.name()]
        self.key = (name, field_descriptor)


@bytecode(0xb2)
class getstatic(_static_field_instruction):
    def execute(self, frame, thread):
        if not hasattr(self, 'static_fields'):
            self.resolve_static(frame, thread)
        frame.operand_stack.append(self.static_fields[self.key])
        if self.category2:
            frame.operand_stack.append(PAD)


@bytecode(0xb3)
class putstatic(_static_field_instruction):
    def execute(self, frame, thread):
        if not hasattr(self, 'static_fields'):
            self.resolve_static(frame, thread)
        if self.category2:
            frame.operand_stack.pop()
        self.static_fields[self.key] = frame.operand_stack.pop()


@bytecode(0xb4)
class getfield(_field_instruction):
    def execute(self, frame, thread):
        '''According JVM document, there are lots of checks for getfield
        instruction, for type check and for access permission. But they are
        all ignored, as we assume this is correct JAVA class file.
        '''
        if not hasattr(self, 'key'):
            declaring_class, name, _ = self.resolve(frame)
            self.key = (declaring_class.name(), name)
        obj = frame.operand_stack.pop()
        if obj is None:
            thread.throw_new('java/lang/NullPointerException')
        frame.operand_stack.append(obj.fields[self.key])
        if self.category2:
            frame.operand_stack.append(PAD)


@bytecode(0xb5)
class putfield(_field_instruction):
    def execute(self, frame, thread):
        if not hasattr(self, 'key'):
            declaring_class, name, _ = self.resolve(frame)
            self.key = (declaring_class.name(), name)
        operand_stack = frame.operand_stack
        if self.category2:
            operand_stack.pop()
        value = operand_stack.pop()
        obj = operand_stack.pop()
        if obj is None:
            thread.throw_new('java/lang/NullPointerException')
        obj.fields[self.key] = value


class _invoke_instruction(_u2_index_instruction):
    def resolve_method(self, frame):
        '''Method resolution, return the class and method'''
        pool = frame.klass.constant_pool
        method_ref = pool[self.index]
        assert type(method_ref) in (
            constant_pool.ConstantMethodref,
            constant_pool.ConstantInterfaceMethodref
        )
        class_name = method_ref.get_class(pool)
        method_name, method_describ = method_ref.get_method(pool)
        if class_name[0] == '[':
            # Method of array class, such as clone
            class_name = 'java/lang/Object'
        klass = run_time_data.method_area[class_name]
        resolved_class, method = klass.interface_resolution(
            method_name, method_describ)
        assert method, \
            f'NoSuchMethodError: {class_name}.{method_name}{method_describ}'
        self.method_name = method_name
        self.method_describ = method_describ
        return resolved_class, method

    def null_pointer(self, frame, thread):
        operand_stack = frame.operand_stack
        objectref = operand_stack[-self.arg_slots]
        if objectref is None:
            thread.throw_new(
                'java/lang/NullPointerException',
                f'invoke {self.method_name} on null object')
        return objectref


@bytecode(0xb6)
class invokevirtual(_invoke_instruction):
    def execute(self, frame, thread):
        if not hasattr(self, 'arg_slots'):
            _, method = self.resolve_method(frame)
            if method.isSignaturePolymorphic():
                raise NotImplementedError(
                    'Invoke signature polymorphic method is not '
                    'implemented.')
            self.arg_slots = method.arg_slots
        objectref = self.null_pointer(frame, thread)
        klass, method = objectref.klass.select_method(
            self.method_name, self.method_describ)
        if not method:
            thread.throw_new(
                'java/lang/AbstractMethodError',
                f'{objectref.class_name()}.{self.method_name}')
        return thread.invoke_from_frame(frame, klass, method)


@bytecode(0xb7)
class invokespecial(_invoke_instruction):
    def execute(self, frame, thread):
        if not hasattr(self, 'method'):
            klass, method = self.resolve_method(frame)
            current_class = frame.klass
            super_class = current_class.get_super_class()
            if self.method_name != '<init>' and \
                    not klass.is_interface() and \
                    current_class.access_flags.super() and \
                    super_class and \
                    current_class is not klass and \
                    current_class.is_subclass_of(klass.name()):
                klass, method = super_class.method_resolution(
                    self.method_name, self.method_describ)
            self.klass = klass
            self.method = method
            self.arg_slots = method.arg_slots
        self.null_pointer(frame, thread)
        return thread.invoke_from_frame(frame, self.klass, self.method)


@bytecode(0xb8)
class invokestatic(_invoke_instruction):
    def execute(self, frame, thread):
        if not hasattr(self, 'method'):
            klass, method = self.resolve_method(frame)
            class_loader.initialize_class(klass, thread)
            self.klass = klass
            self.method = method
        return thread.invoke_from_frame(frame, self.klass, self.method)


@bytecode(0xb9)
class invokeinterface(invokevirtual):
    def len_of_operand(self):
        return 4

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 4
        self.index = int.from_bytes(
            operand_bytes[:2], byteorder='big', signed=False)
        assert operand_bytes[2] > 0
        assert operand_bytes[3] == 0


@bytecode(0xba)
class invokedynamic(_instruction):
    def len_of_operand(self):
        return 4

    def execute(self, frame, thread):
        raise NotImplementedError('invokedynamic is not implemented yet.')


def _class_name(frame, index):
    pool = frame.klass.constant_pool
    class_info = pool[index]
    assert type(class_info) is constant_pool.ConstantClass
    return pool[class_info.name_index].value()


@bytecode(0xbb)
class new(_u2_index_instruction):
    def execute(self, frame, thread):
        if not hasattr(self, 'klass'):
            klass = run_time_data.method_area[_class_name(frame, self.index)]
            if klass.is_interface() or klass.access_flags.abstract():
                thread.throw_new('java/lang/InstantiationError', klass.name())
            self.klass = klass
        class_loader.initialize_class(self.klass, thread)
        frame.operand_stack.append(run_time_data.new_object(self.klass))


ARRAY_TYPES = {
    4: '[Z',
    5: '[C',
    6: '[F',
    7: '[D',
    8: '[B',
    9: '[S',
    10: '[I',
    11: '[J',
}


def _new_array(thread, array_type, count):
    if count < 0:
        thread.throw_new(
            'java/lang/NegativeArraySizeException', str(count))
    return run_time_data.new_array(array_type, count)


@bytecode(0xbc)
class newarray(_u1_index_instruction):
    def execute(self, frame, thread):
        count = frame.operand_stack.pop()
        frame.operand_stack.append(
            _new_array(thread, ARRAY_TYPES[self.index], count))


@bytecode(0xbd)
class anewarray(_u2_index_instruction):
    def execute(self, frame, thread):
        if not hasattr(self, 'array_type'):
            class_name = _class_name(frame, self.index)
            self.array_type = '[' + \
                run_time_data.class_name_to_descriptor(class_name)
        count = frame.operand_stack.pop()
        frame.operand_stack.append(_new_array(thread, self.array_type, count))


@bytecode(0xbe)
class arraylength(_instruction):
    def execute(self, frame, thread):
        array = frame.operand_stack.pop()
        if array is None:
            thread.throw_new('java/lang/NullPointerException')
        frame.operand_stack.append(len(array.values))


@bytecode(0xbf)
class athrow(_instruction):
    def execute(self, frame, thread):
        from lib.thread import JavaException
        throwable = frame.operand_stack.pop()
        if throwable is None:
            thread.throw_new('java/lang/NullPointerException')
        raise JavaException(throwable)


@bytecode(0xc0)
class checkcast(_u2_index_instruction):
    def execute(self, frame, thread):
        obj = frame.operand_stack[-1]
        if obj is None:
            return
        class_name = _class_name(frame, self.index)
        if not run_time_data.is_instance_of(obj, class_name):
            thread.throw_new(
                'java/lang/ClassCastException',
                f'{obj.class_name()} cannot be cast to {class_name}'
                .replace('/', '.'))


@bytecode(0xc1)
class instanceof(_u2_index_instruction):
    def execute(self, frame, thread):
        obj = frame.operand_stack.pop()
        if obj is None:
            frame.operand_stack.append(0)
            return
        class_name = _class_name(frame, self.index)
        frame.operand_stack.append(
            1 if run_time_data.is_instance_of(obj, class_name) else 0)


@bytecode(0xc2)
class monitorenter(_instruction):
    '''Only one thread for now, no need to lock'''

    def execute(self, frame, thread):
        if frame.operand_stack.pop() is None:
            thread.throw_new('java/lang/NullPointerException')


@bytecode(0xc3)
class monitorexit(monitorenter):
    pass


@bytecode(0xc4)
class wide(_instruction):
    '''Extend local variable index by additional bytes'''

    def decode(self, code):
        opcode = code[self.address + 1]
        self.instruction = OPCODES[opcode](self.address)
        index = int.from_bytes(
            code[self.address + 2:self.address + 4], byteorder='big')
        if opcode == 0x84:
            self.instruction.index = index
            self.instruction.const = int.from_bytes(
                code[self.address + 4:self.address + 6],
                byteorder='big', signed=True)
            return self.address + 6
        self.instruction.n = index
        return self.address + 4

    def execute(self, frame, thread):
        return self.instruction.execute(frame, thread)


@bytecode(0xc5)
class multianewarray(_instruction):
    def len_of_operand(self):
        return 3

    def put_operands(self, operand_bytes):
        self.index = int.from_bytes(operand_bytes[:2], byteorder='big')
        self.dimensions = operand_bytes[2]

    def create(self, thread, array_type, counts):
        array = _new_array(thread, array_type, counts[0])
        if len(counts) > 1:
            for i in range(counts[0]):
                array.values[i] = self.create(
                    thread, array_type[1:], counts[1:])
        return array

    def execute(self, frame, thread):
        array_type = _class_name(frame, self.index)
        operand_stack = frame.operand_stack
        counts = operand_stack[-self.dimensions:]
        del operand_stack[-self.dimensions:]
        for count in counts:
            if count < 0:
                thread.throw_new(
                    'java/lang/NegativeArraySizeException', str(count))
        operand_stack.append(self.create(thread, array_type, counts))
