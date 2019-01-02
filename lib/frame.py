from collections import deque


class Frame(object):
    def __init__(self, klass, method, parameter_types, parameters):
        self.operand_stack = deque()
        self.klass = klass
        # self.class_constant_pool = klass.constant_pool
        self.next_ops_address = 0
        self.code = method.code()
        if not self.code:
            raise RuntimeError('Could not find code in method')
        self.local_variables = [None for _ in range(self.code.max_locals)]
        offset = 0
        for i in range(len(parameter_types)):
            self.local_variables[i + offset] = parameters[i]
            if parameter_types[i] in ('D', 'J'):
                # Double or Long
                offset += 1
