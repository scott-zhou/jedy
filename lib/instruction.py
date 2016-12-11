import logging


class iconst_i(object):
    def __init__(self, i):
        self.i = i

    def execute(self, frame):
        frame.operand_stack.append(self.i)
        logging.debug('Instruction: push {i} onto operand stack'.format(i=self.i))


class iconst_m1(iconst_i):
    def __init__(self):
        super().__init__(-1)


_t = {
    0x02: iconst_m1
}
