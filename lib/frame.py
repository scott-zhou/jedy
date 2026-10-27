from lib import class_loader


class _Pad(object):
    '''Category 2 values (long and double) take two slots in local
    variables and operand stack. The value is stored in the first slot,
    the second slot is filled with PAD.
    '''

    def __repr__(self):
        return '<pad>'


PAD = _Pad()


def is_category2(field_type):
    return field_type in ('J', 'D')


def default_value(field_type):
    if field_type in ('F', 'D'):
        return 0.0
    if field_type[0] in ('L', '['):
        return None
    return 0


class Object(object):
    __slots__ = ('klass', 'fields', '__dict__')

    def __init__(self, klass):
        self.klass = klass
        self.fields = {}

    def __repr__(self):
        return f'Object({self.klass.name()})'

    def __str__(self):
        return f'Object of class {self.klass.name()}'

    def class_name(self):
        return self.klass.name()

    def set_field(self, field_klass_name, field_name, field_value):
        self.fields[(field_klass_name, field_name)] = field_value

    def get_field(self, field_klass_name, field_name):
        return self.fields[(field_klass_name, field_name)]


class ArrayObject(Object):
    '''Array instance. `array_type` is the descriptor of the array class,
    such as `[I` or `[Ljava/lang/String;`. Elements are stored in a python
    list `values`.
    '''
    __slots__ = ('array_type', 'values')

    def __init__(self, klass, array_type, values):
        super().__init__(klass)
        self.array_type = array_type
        self.values = values

    def __repr__(self):
        return f'Array({self.array_type}, len={len(self.values)})'

    __str__ = __repr__

    def class_name(self):
        return self.array_type

    def component_type(self):
        return self.array_type[1:]


class _LocalVariables(list):
    def __init__(self, onSetLocalVariable=None):
        self.onSetLocalVariable = onSetLocalVariable
        super().__init__()

    def __setitem__(self, idx, value):
        if self.onSetLocalVariable:
            self.onSetLocalVariable(idx, value)
        return super().__setitem__(idx, value)


class Frame(object):
    __slots__ = (
        'operand_stack', 'klass', 'method', 'code', 'pc',
        'local_variables', 'is_base', 'current_pc'
    )

    def __init__(self, klass, method, slots):
        '''`slots` is the argument values as they are on the operand stack
        of the invoker, starts with the objectref for instance method, and
        category 2 values take two slots.
        '''
        self.operand_stack = []
        self.klass = klass
        self.method = method
        self.pc = 0
        self.current_pc = 0
        # The bottom frame of a nested interpreter loop, returns the
        # value to python caller instead of the operand stack of the
        # previous frame.
        self.is_base = False
        self.code = method.code()
        if not self.code:
            raise RuntimeError(f'Could not find code in method {method.name}')
        local_variables = list(slots)
        local_variables.extend([None] * (self.code.max_locals - len(slots)))
        callback = class_loader.local_variable_callbacks.get(method.name, None)
        if callback:
            self.local_variables = _LocalVariables(callback)
            for value in local_variables:
                self.local_variables.append(value)
        else:
            self.local_variables = local_variables


    def operand_debug_str(self):
        operand_stack_str = \
            f'[{", ".join(str(v) for v in self.operand_stack)}]'
        return f'operand stack: {operand_stack_str}'

    def local_variable_debug_str(self):
        local_variable_str = \
            f'[{", ".join(str(v) for v in self.local_variables)}]'
        return f'local variables: {local_variable_str}'


def pad_arguments(method, arguments):
    '''Convert argument values to slots, see Frame.__init__'''
    slots = []
    offset = 0
    if not method.access_flags.static():
        slots.append(arguments[0])
        offset = 1
    for i, param_type in enumerate(method.parameter_types):
        slots.append(arguments[i + offset])
        if is_category2(param_type):
            slots.append(PAD)
    return slots


def unpad_arguments(slots):
    return [v for v in slots if v is not PAD]
