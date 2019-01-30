from collections import deque
from lib import class_loader


class Object(object):
    def __init__(self, klass):
        self.klass = klass
        self.fields = {}

    def __repr__(self):
        return f'Object({self.klass.name()})'

    def __str__(self):
        return f'Object of class {self.klass.name()}'

    def set_field(self, field_klass_name, field_type, field_name, field_value):
        self.fields[f'{field_type} {field_klass_name}.{field_name}'] = \
            field_value

    def set_field_default(self, field_klass_name, field_type, field_name):
        value = 0
        if field_type == 'C':
            value = ''
        elif field_type == 'Z':
            value = False
        elif len(field_type) > 1 and field_type[0] == 'L':
            # TODO: It's a reference, shoule init it, skip for now
            value = None
        elif len(field_type) > 1 and field_type[0] == '[':
            value = []
        self.fields[f'{field_type} {field_klass_name}.{field_name}'] = value

    def get_field(self, field_klass_name, field_type, field_name):
        return self.fields[f'{field_type} {field_klass_name}.{field_name}']


class _LocalVariables(list):
    def __init__(self, onSetLocalVariable=None):
        self.onSetLocalVariable = onSetLocalVariable
        super().__init__()

    def __setitem__(self, idx, value):
        if self.onSetLocalVariable:
            self.onSetLocalVariable(idx, value)
        return super().__setitem__(idx, value)


class Frame(object):
    def __init__(self, klass, method, objectref, parameter_types, parameters):
        self.operand_stack = deque()
        self.klass = klass
        self.method = method
        self.next_ops_address = 0
        self.code = method.code()
        if not self.code:
            raise RuntimeError('Could not find code in method')
        self.local_variables = _LocalVariables(
            class_loader.local_variable_callbacks.get(
                method.name, None
            )
        )
        for _ in range(self.code.max_locals):
            self.local_variables.append(None)
        offset = 0
        if objectref:
            self.local_variables[0] = objectref
            offset = 1
        for i in range(len(parameter_types)):
            self.local_variables[i + offset] = parameters[i]
            if parameter_types[i] in ('D', 'J'):
                # Double or Long
                offset += 1

    def operand_debug_str(self):
        operand_stack_str = \
            f'[{", ".join(str(v) for v in self.operand_stack)}]'
        return f'operand stack: {operand_stack_str}'

    def local_variable_debug_str(self):
        local_variable_str = \
            f'[{", ".join(str(v) for v in self.local_variables)}]'
        return f'local variables: {local_variable_str}'
