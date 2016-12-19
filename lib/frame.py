from collections import deque


class Frame(object):
    def __init__(self, klass, method, parameter_types, parameters):
        self.operand_stack = deque()
        self.class_constant_pool = klass.constant_pool
        code = method.code()
        if not code:
            raise RuntimeError('Could not find code in method')
        self.local_variables = [None for _ in range(code.max_locals)]
        offset = 0
        for i in range(len(parameter_types)):
            self.local_variables[i + offset] = parameters[i]
            if parameter_types[i] in ('D', 'J'):
                # Double or Long
                offset += 1
