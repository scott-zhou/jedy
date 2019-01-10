import logging
from enum import Enum, unique
from lib import constant_pool
from lib import run_time_data
from lib import descriptor
from lib import frame as FRAME

OPCODES = {}


def bytecode(code):
    def bytecode_decorator(klass):
        OPCODES[code] = klass
        return klass
    return bytecode_decorator


@unique
class NextStep(Enum):
    next_instruction = 0
    jump_to = 1
    invoke_method = 2
    method_return = 3


class _instruction(object):
    def __init__(self, address):
        self.address = address
        # For method internal loop
        self.need_jump = False
        self.jump_to_address = None
        # For call other method
        self.invoke_method = False
        self.invoke_class_name = None
        self.invoke_method_name = None
        self.invoke_objectref = None
        self.invoke_parameter_types = []
        self.invoke_parameters = []
        self.invoke_return = []
        # For return
        self.method_return = False
        self.return_value = None

    def init_jump(self):
        self.need_jump = False
        self.jump_to_address = None

    def init_invoke_method(self):
        self.invoke_method = False
        self.invoke_class_name = None
        self.invoke_method_name = None
        self.invoke_objectref = None
        self.invoke_parameter_types = []
        self.invoke_parameters = []
        self.invoke_return = []

    def len_of_operand(self):
        return 0

    def put_operands(self, operand_bytes):
        pass

    def class_name_and_address(self):
        return '{name} (addr:{address})'.format(name=type(self).__name__, address=self.address)

    def next_step(self):
        if self.invoke_method:
            return NextStep.invoke_method
        elif self.need_jump:
            return NextStep.jump_to
        elif self.method_return:
            return NextStep.method_return
        else:
            return NextStep.next_instruction

    def execute(self, frame):
        raise NotImplementedError('execute in base instruction is not implemented, instruction {name}'.format(name=self.class_name_and_address()))


class iconst_i(_instruction):
    def __init__(self, address, i=0):
        super().__init__(address)
        self.i = i

    def execute(self, frame):
        frame.operand_stack.append(self.i)
        logging.debug(
            'Instruction {na}: push {i} onto operand stack'.format(
                na=self.class_name_and_address(),
                i=self.i
            )
        )


@bytecode(0x02)
class iconst_m1(iconst_i):
    def __init__(self, address):
        super().__init__(address, -1)


@bytecode(0x03)
class iconst_0(iconst_i):
    def __init__(self, address):
        super().__init__(address, 0)


@bytecode(0x04)
class iconst_1(iconst_i):
    def __init__(self, address):
        super().__init__(address, 1)


@bytecode(0x05)
class iconst_2(iconst_i):
    def __init__(self, address):
        super().__init__(address, 2)


@bytecode(0x06)
class iconst_3(iconst_i):
    def __init__(self, address):
        super().__init__(address, 3)


@bytecode(0x07)
class iconst_4(iconst_i):
    def __init__(self, address):
        super().__init__(address, 4)


@bytecode(0x08)
class iconst_5(iconst_i):
    def __init__(self, address):
        super().__init__(address, 5)


@bytecode(0x10)
class bipush(iconst_i):
    def __init__(self, address):
        super().__init__(address)

    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        assert type(operand_bytes[0]) is int
        self.i = operand_bytes[0]


@bytecode(0x11)
class sipush(iconst_i):
    def __init__(self, address):
        super().__init__(address)

    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 2
        self.i = int.from_bytes(operand_bytes, byteorder='big', signed=False)


class iload_n(_instruction):
    def __init__(self, address, n=0):
        super().__init__(address)
        self.n = n

    def execute(self, frame):
        assert type(frame.local_variables[self.n]) is int
        frame.operand_stack.append(frame.local_variables[self.n])
        logging.debug(
            'Instruction {na}: push {i} onto operand stack from local variable {n}'.format(
                na=self.class_name_and_address(),
                i=frame.local_variables[self.n],
                n=self.n
            )
        )


@bytecode(0x15)
class iload(iload_n):
    def __init__(self, address):
        super().__init__(address)

    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        assert type(operand_bytes[0]) is int
        self.n = operand_bytes[0]


@bytecode(0x1a)
class iload_0(iload_n):
    def __init__(self, address):
        super().__init__(address, 0)


@bytecode(0x1b)
class iload_1(iload_n):
    def __init__(self, address):
        super().__init__(address, 1)


@bytecode(0x1c)
class iload_2(iload_n):
    def __init__(self, address):
        super().__init__(address, 2)


@bytecode(0x1d)
class iload_3(iload_n):
    def __init__(self, address):
        super().__init__(address, 3)


class aload_n(_instruction):
    def __init__(self, address, n=0):
        super().__init__(address)
        self.n = n

    def execute(self, frame):
        # assert type(frame.local_variables[self.n]) is what
        # TODO: assert the type is reference, then the problem is how to represent a reference?
        frame.operand_stack.append(frame.local_variables[self.n])
        logging.debug(
            'Instruction {na}: push {a} onto operand stack from local variable {n}'.format(
                na=self.class_name_and_address(),
                a=frame.local_variables[self.n],
                n=self.n
            )
        )


@bytecode(0x25)
class aload(aload_n):
    def __init__(self, address):
        super().__init__(address)

    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        assert type(operand_bytes[0]) is int
        self.n = operand_bytes[0]


@bytecode(0x2a)
class aload_0(aload_n):
    def __init__(self, address):
        super().__init__(address, 0)


@bytecode(0x2b)
class aload_1(aload_n):
    def __init__(self, address):
        super().__init__(address, 1)


@bytecode(0x2c)
class aload_2(aload_n):
    def __init__(self, address):
        super().__init__(address, 2)


@bytecode(0x2d)
class aload_3(aload_n):
    def __init__(self, address):
        super().__init__(address, 3)


class istore_n(_instruction):
    def __init__(self, address, n=0):
        super().__init__(address)
        self.n = n

    def execute(self, frame):
        i = frame.operand_stack.pop()
        assert type(i) is int
        frame.local_variables[self.n] = i
        logging.debug(
            'Instruction {na}: pop {i} from operand stack and set to local variable {n}'.format(
                na=self.class_name_and_address(),
                i=i,
                n=self.n
            )
        )


@bytecode(0x36)
class istore(istore_n):
    def __init__(self, address):
        super().__init__(address)

    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        assert type(operand_bytes[0]) is int
        self.n = operand_bytes[0]


@bytecode(0x3b)
class istore_0(istore_n):
    def __init__(self, address):
        super().__init__(address, 0)


@bytecode(0x3c)
class istore_1(istore_n):
    def __init__(self, address):
        super().__init__(address, 1)


@bytecode(0x3d)
class istore_2(istore_n):
    def __init__(self, address):
        super().__init__(address, 2)


@bytecode(0x3e)
class istore_3(istore_n):
    def __init__(self, address):
        super().__init__(address, 3)


@bytecode(0x59)
class dup(_instruction):
    def execute(self, frame):
        frame.operand_stack.append(frame.operand_stack[-1])
        logging.debug(
            f'Instruction {self.class_name_and_address()}: '
            'Duplicate the top operand stack value'
        )


@bytecode(0x60)
class iadd(_instruction):
    def execute(self, frame):
        value2 = frame.operand_stack.pop()
        value1 = frame.operand_stack.pop()
        assert type(value1) is int
        assert type(value2) is int
        value = value1 + value2
        frame.operand_stack.append(value)
        logging.debug(
            'Instruction {na}: add value1 and value2, push {v} onto operand stack'.format(
                na=self.class_name_and_address(),
                v=value
            )
        )


@bytecode(0x70)
class irem(_instruction):
    def execute(self, frame):
        value2 = frame.operand_stack.pop()
        value1 = frame.operand_stack.pop()
        assert type(value1) is int
        assert type(value2) is int
        # That the defination in JRE document, but we can use % operator
        # value = int(value1 - int(value1 / value2) * value2)
        value = value1 % value2
        frame.operand_stack.append(value)
        logging.debug(
            f'Instruction {self.class_name_and_address()}: Remainder int, '
            f'value1 is {value1}, value2 is {value2}, '
            f'push result value {value} onto operand stack'
        )


@bytecode(0x64)
class isub(_instruction):
    def execute(self, frame):
        value2 = frame.operand_stack.pop()
        value1 = frame.operand_stack.pop()
        assert type(value1) is int
        assert type(value2) is int
        value = value1 - value2
        frame.operand_stack.append(value)
        logging.debug(
            'Instruction {na}: Subtract value1 and value2, push {v} onto operand stack'.format(
                na=self.class_name_and_address(),
                v=value
            )
        )

@bytecode(0x68)
class imul(_instruction):
    def execute(self, frame):
        value2 = frame.operand_stack.pop()
        value1 = frame.operand_stack.pop()
        assert type(value1) is int
        assert type(value2) is int
        value = value1 * value2
        frame.operand_stack.append(value)
        logging.debug(
            'Instruction {na}: multiply value1 and value2, push {v} onto operand stack'.format(
                na=self.class_name_and_address(),
                v=value
            )
        )


@bytecode(0x6c)
class idiv(_instruction):
    def execute(self, frame):
        value2 = frame.operand_stack.pop()
        value1 = frame.operand_stack.pop()
        assert type(value1) is int
        assert type(value2) is int
        if value2 == 0:
            raise NotImplementedError('Exception have not implemented. Should through ArithmeticException')
        value = value1 // value2
        frame.operand_stack.append(value)
        logging.debug(
            'Instruction {na}: Divide value1 and value2, push {v} onto operand stack'.format(
                na=self.class_name_and_address(),
                v=value
            )
        )


@bytecode(0x84)
class iinc(_instruction):
    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 2
        self.index = int.from_bytes(operand_bytes[:1], byteorder='big', signed=False)
        self.const = int.from_bytes(operand_bytes[1:], byteorder='big', signed=True)

    def execute(self, frame):
        frame.local_variables[self.index] = frame.local_variables[self.index] + self.const
        logging.debug(
            'Instruction {na}: increate local value {i} by {v} to value {fv}'.format(
                na=self.class_name_and_address(),
                i=self.index,
                v=self.const,
                fv=frame.local_variables[self.index]
            )
        )


class if_icmpcond(_instruction):
    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 2
        self.offset = int.from_bytes(operand_bytes, byteorder='big', signed=True)

    def execute(self, frame):
        self.init_jump()
        value2 = frame.operand_stack.pop()
        value1 = frame.operand_stack.pop()
        if self.cmp(value1, value2):
            self.need_jump = True
            self.jump_to_address = self.address + self.offset
        logging.debug(
            'Instruction {na}: compare value1 and value2 from stack, result need {j}'.format(
                na=self.class_name_and_address(),
                j='jump to address {0}'.format(self.jump_to_address) if self.need_jump else 'not jump'
            )
        )

    def cmp(self, value1, value2):
        raise NotImplementedError('cmp function in if_icmpcond will not be implement.')


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


@bytecode(0xa7)
class goto(_instruction):
    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 2
        self.offset = int.from_bytes(operand_bytes, byteorder='big', signed=True)

    def execute(self, frame):
        self.need_jump = True
        self.jump_to_address = self.address + self.offset
        logging.debug(
            'Instruction {na}: jump to address {a}'.format(
                na=self.class_name_and_address(),
                a=self.jump_to_address
            )
        )


@bytecode(0xac)
class ireturn(_instruction):
    def execute(self, frame):
        self.method_return = True
        self.return_value = frame.operand_stack.pop()
        assert type(self.return_value) is int, 'ireturn, but get value from operand in type {t}'.format(type(self.return_value))
        logging.debug(
            'Instruction {na}: return value {v}'.format(
                na=self.class_name_and_address(),
                v=self.return_value
            )
        )


@bytecode(0xb0)
class areturn(_instruction):
    def execute(self, frame):
        self.method_return = True
        self.return_value = frame.operand_stack.pop()
        assert type(self.return_value) is FRAME.Object, \
            f'areturn, but get value from operand in type {type(self.return_value)}'
        logging.debug(
            'Instruction {na}: return value {v}'.format(
                na=self.class_name_and_address(),
                v=self.return_value
            )
        )


@bytecode(0xb1)
class instruction_return(_instruction):
    def execute(self, frame):
        self.method_return = True
        logging.debug(
            'Instruction {na}: void return'.format(
                na=self.class_name_and_address()
            )
        )


@bytecode(0xb2)
class getstatic(_instruction):
    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 2
        self.index = int.from_bytes(operand_bytes, byteorder='big', signed=False)

    def execute(self, frame):
        field_ref = frame.klass.constant_pool[self.index]
        logging.debug(type(field_ref))
        assert type(field_ref) is constant_pool.ConstantFieldref
        class_name = field_ref.get_class(frame.klass.constant_pool)
        logging.debug(type(class_name))
        name, field = field_ref.get_name_descriptor(frame.klass.constant_pool)
        field = descriptor.parse_field_descriptor(field)
        logging.debug(
            'Instruction {na}: resolute filed {name}({field}) in class {class_name}'.format(
                na=self.class_name_and_address(),
                **vars()
            )
        )
        logging.error('Execute getstatic havent been implemented.')


@bytecode(0xb7)
class invokespecial(_instruction):
    '''Currently only for call super class constructioin
    '''

    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 2
        self.index = int.from_bytes(
            operand_bytes, byteorder='big', signed=False)

    def execute(self, frame):
        self.init_invoke_method()
        method_ref = frame.klass.constant_pool[self.index]
        assert type(method_ref) in (
            constant_pool.ConstantMethodref,
            constant_pool.ConstantInterfaceMethodref
        )
        class_name = method_ref.get_class(frame.klass.constant_pool)
        method_name, method_describ = method_ref.get_method(
            frame.klass.constant_pool)
        parameters, rt = descriptor.parse_method_descriptor(method_describ)
        # Find klass is not correct implemented now, but enough for invoke
        # super class construction
        klass = run_time_data.method_area[class_name]
        method = klass.find_method(method_name)
        is_initialization_method = method_name in ['<init>', '<clinit>']
        super_class_name = frame.klass.constant_pool[
            frame.klass.constant_pool[frame.klass.super_class].name_index
        ]
        is_super_class = type(method_ref) is constant_pool.ConstantMethodref\
            and class_name == super_class_name
        if not is_initialization_method and is_super_class\
                and frame.klass.access_flags.super():
            klass = run_time_data.method_area[super_class_name]
            method = klass.find_method(method_name)
        else:
            # Otherwise, let C be the class or interface named by the symbolic
            # reference. Which don't need do anything
            pass
        assert not method.access_flags.native(),\
            'Not support native method yet.'
        assert not method.access_flags.synchronized(),\
            'Not support synchronized method yet.'
        logging.debug(
            'Instruction {na}: {kl}:{me}'.format(
                na=self.class_name_and_address(),
                kl=class_name,
                me=method_name
            )
        )
        self.invoke_method = True
        self.invoke_class_name = class_name
        self.invoke_method_name = method_name
        self.invoke_parameter_types = parameters
        self.invoke_return = rt
        for _ in range(len(self.invoke_parameter_types)):
            self.invoke_parameters.append(frame.operand_stack.pop())
        # Pop objectref from operand stack
        self.invoke_objectref = frame.operand_stack.pop()
        self.invoke_parameters.reverse()


@bytecode(0xb8)
class invokestatic(_instruction):
    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 2
        self.index = int.from_bytes(
            operand_bytes, byteorder='big', signed=False)

    def execute(self, frame):
        self.init_invoke_method()
        method_ref = frame.klass.constant_pool[self.index]
        assert type(method_ref) in (
            constant_pool.ConstantMethodref,
            constant_pool.ConstantInterfaceMethodref
        )
        class_name = method_ref.get_class(frame.klass.constant_pool)
        method_name, method_describ = method_ref.get_method(
            frame.klass.constant_pool)
        parameters, rt = descriptor.parse_method_descriptor(method_describ)
        klass = run_time_data.method_area[class_name]
        method = klass.find_method(method_name)
        assert not method.access_flags.native(),\
            'Not support native method yet.'
        assert not method.access_flags.synchronized(),\
            'Not support synchronized method yet.'
        logging.debug(
            'Instruction {na}: {kl}:{me}'.format(
                na=self.class_name_and_address(),
                kl=class_name,
                me=method_name
            )
        )
        self.invoke_method = True
        self.invoke_class_name = class_name
        self.invoke_method_name = method_name
        self.invoke_parameter_types = parameters
        self.invoke_return = rt
        for _ in range(len(self.invoke_parameter_types)):
            self.invoke_parameters.append(frame.operand_stack.pop())
        self.invoke_parameters.reverse()


@bytecode(0xbb)
class new(_instruction):
    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 2
        self.index = int.from_bytes(
            operand_bytes, byteorder='big', signed=False)

    def execute(self, frame):
        class_info = frame.klass.constant_pool[self.index]
        assert type(class_info) is constant_pool.ConstantClass
        class_name = frame.klass.constant_pool[class_info.name_index]
        assert type(class_name) is constant_pool.ConstantUtf8
        klass = run_time_data.method_area[class_name.str_value]
        obj = FRAME.Object(klass)
        # TODO: haven't initialized
        frame.operand_stack.append(obj)
        logging.debug(
            f'Instruction {self.class_name_and_address()}: '
            f'push reference {obj} onto operand stack'
        )
