import logging


class _instruction(object):
    def __init__(self, address):
        self.address = address
        self.need_jump = False
        self.jump_to_address = None

    def len_of_operand(self):
        return 0

    def put_operands(self, operand_bytes):
        pass

    def class_name_and_address(self):
        return '{name} ({address})'.format(name=type(self).__name__, address=self.address)

    def jump(self):
        return self.need_jump, self.jump_to_address


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


class bipush(iconst_i):
    def __init__(self, address):
        super().__init__(address)

    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        assert type(operand_bytes[0]) is int
        self.i = operand_bytes[0]


class iconst_m1(iconst_i):
    def __init__(self, address):
        super().__init__(address, -1)


class iconst_0(iconst_i):
    def __init__(self, address):
        super().__init__(address, 0)


class iconst_1(iconst_i):
    def __init__(self, address):
        super().__init__(address, 1)


class iconst_2(iconst_i):
    def __init__(self, address):
        super().__init__(address, 2)


class iconst_3(iconst_i):
    def __init__(self, address):
        super().__init__(address, 3)


class iconst_4(iconst_i):
    def __init__(self, address):
        super().__init__(address, 4)


class iconst_5(iconst_i):
    def __init__(self, address):
        super().__init__(address, 5)


class sipush(iconst_i):
    def __init__(self, address):
        super().__init__(address)

    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 2
        self.i = int.from_bytes(operand_bytes, byteorder='big', signed=False)


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


class istore(istore_n):
    def __init__(self, address):
        super().__init__(address)

    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        assert type(operand_bytes[0]) is int
        self.n = operand_bytes[0]


class istore_0(istore_n):
    def __init__(self, address):
        super().__init__(address, 0)


class istore_1(istore_n):
    def __init__(self, address):
        super().__init__(address, 1)


class istore_2(istore_n):
    def __init__(self, address):
        super().__init__(address, 2)


class istore_3(istore_n):
    def __init__(self, address):
        super().__init__(address, 3)


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


class iload(iload_n):
    def __init__(self, address):
        super().__init__(address)

    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        assert type(operand_bytes[0]) is int
        self.n = operand_bytes[0]


class iload_0(iload_n):
    def __init__(self, address):
        super().__init__(address, 0)


class iload_1(iload_n):
    def __init__(self, address):
        super().__init__(address, 1)


class iload_2(iload_n):
    def __init__(self, address):
        super().__init__(address, 2)


class iload_3(iload_n):
    def __init__(self, address):
        super().__init__(address, 3)


class if_icmpcond(_instruction):
    def len_of_operand(self):
        return 2

    def put_operands(self, operand_bytes):
        assert len(operand_bytes) == 2
        self.offset = int.from_bytes(operand_bytes, byteorder='big', signed=True)

    def execute(self, frame):
        self.need_jump = False
        self.jump_to_address = None
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


class if_icmpeq(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 == value2


class if_icmpne(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 != value2


class if_icmplt(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 < value2


class if_icmpge(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 >= value2


class if_icmpgt(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 > value2


class if_icmple(if_icmpcond):
    def cmp(self, value1, value2):
        return value1 <= value2


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


class instruction_return(_instruction):
    def execute(self, frame):
        logging.debug(
            'Instruction {na}: void return'.format(
                na=self.class_name_and_address()
            )
        )


types = {
    0x02: iconst_m1,
    0x03: iconst_0,
    0x04: iconst_1,
    0x05: iconst_2,
    0x06: iconst_3,
    0x07: iconst_4,
    0x08: iconst_5,
    0x10: bipush,
    0x11: sipush,
    0x15: iload,
    0x1a: iload_0,
    0x1b: iload_1,
    0x1c: iload_2,
    0x1d: iload_3,
    0x36: istore,
    0x3b: istore_0,
    0x3c: istore_1,
    0x3d: istore_2,
    0x3e: istore_3,
    0x60: iadd,
    0x68: imul,
    0x84: iinc,
    0x9f: if_icmpeq,
    0xa0: if_icmpne,
    0xa1: if_icmplt,
    0xa2: if_icmpge,
    0xa3: if_icmpgt,
    0xa4: if_icmple,
    0xa7: goto,
    0xb1: instruction_return,
}
