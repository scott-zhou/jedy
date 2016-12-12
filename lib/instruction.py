import logging


class _instruction(object):
    def len_of_operand(self):
        return 0

    def put_operands(self, operand_bytes):
        pass


class iconst_i(_instruction):
    def __init__(self, i):
        self.i = i

    def execute(self, frame):
        frame.operand_stack.append(self.i)
        logging.debug('Instruction: push {i} onto operand stack'.format(i=self.i))


class bipush(iconst_i):
    def __init__(self):
        pass

    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        assert type(operand_bytes[0]) is int
        self.i = operand_bytes[0]


class iconst_m1(iconst_i):
    def __init__(self):
        super().__init__(-1)


class iconst_0(iconst_i):
    def __init__(self):
        super().__init__(0)


class iconst_1(iconst_i):
    def __init__(self):
        super().__init__(1)


class iconst_2(iconst_i):
    def __init__(self):
        super().__init__(2)


class iconst_3(iconst_i):
    def __init__(self):
        super().__init__(3)


class iconst_4(iconst_i):
    def __init__(self):
        super().__init__(4)


class iconst_5(iconst_i):
    def __init__(self):
        super().__init__(5)


class istore_n(_instruction):
    def __init__(self, n):
        self.n = n

    def execute(self, frame):
        i = frame.operand_stack.pop()
        assert type(i) is int
        frame.local_variables[self.n] = i
        logging.debug('Instruction: pop {i} from operand stack and set to local variable {n}'.format(i=i, n=self.n))


class istore(istore_n):
    def __init__(self):
        pass

    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        assert type(operand_bytes[0]) is int
        self.n = operand_bytes[0]


class istore_0(istore_n):
    def __init__(self):
        super().__init__(0)


class istore_1(istore_n):
    def __init__(self):
        super().__init__(1)


class istore_2(istore_n):
    def __init__(self):
        super().__init__(2)


class istore_3(istore_n):
    def __init__(self):
        super().__init__(3)


class iload_n(_instruction):
    def __init__(self, n):
        self.n = n

    def execute(self, frame):
        assert type(frame.local_variables[self.n]) is int
        frame.operand_stack.append(frame.local_variables[self.n])
        logging.debug('Instruction: push {i} onto operand stack from local variable {n}'.format(i=frame.local_variables[self.n], n=self.n))


class iload(iload_n):
    def __init__(self):
        pass

    def len_of_operand(self):
        return 1

    def put_operands(self, operand_bytes):
        assert type(operand_bytes[0]) is int
        self.n = operand_bytes[0]


class iload_0(iload_n):
    def __init__(self):
        super().__init__(0)


class iload_1(iload_n):
    def __init__(self):
        super().__init__(1)


class iload_2(iload_n):
    def __init__(self):
        super().__init__(2)


class iload_3(iload_n):
    def __init__(self):
        super().__init__(3)


types = {
    0x02: iconst_m1,
    0x03: iconst_0,
    0x04: iconst_1,
    0x05: iconst_2,
    0x06: iconst_3,
    0x07: iconst_4,
    0x08: iconst_5,
    0x10: bipush,
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
}
