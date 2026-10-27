import logging
from lib import run_time_data
from lib import class_loader
from lib import frame as FRAME
from lib.frame import Frame, PAD
from lib import hijack_jre_methods

trace = False


class JavaException(Exception):
    '''Python exception to carry a thrown java/lang/Throwable object'''

    def __init__(self, throwable):
        super().__init__(throwable)
        self.throwable = throwable

    def __str__(self):
        try:
            message = run_time_data.py_string(self.throwable.get_field(
                'java/lang/Throwable', 'detailMessage'))
        except KeyError:
            message = None
        name = self.throwable.class_name().replace('/', '.')
        return f'{name}: {message}' if message is not None else name


_NO_IMPL = object()


def method_implementation(klass, method):
    '''Python implementation for native method, or hijacked JRE method.
    None if the method should be executed as bytecode.
    '''
    impl = getattr(method, '_impl', _NO_IMPL)
    if impl is _NO_IMPL:
        class_name = klass.name()
        name = method.method_name.value()
        impl = hijack_jre_methods.get_jdk_method(
            class_name, name, method.descriptor)
        if impl is None and method.access_flags.native():
            impl = hijack_jre_methods.get_native_method(
                class_name, name, method.descriptor)
            if impl is None:
                impl = _unimplemented_native(class_name, name, method)
        method._impl = impl
    return impl


def _unimplemented_native(class_name, name, method):
    def unimplemented(thread, args):
        raise NotImplementedError(
            f'Native method {class_name}.{name}{method.descriptor} '
            'is not implemented.')
    return unimplemented


class Thread(object):
    def __init__(self, class_name, method_name, method_descriptor, argv):
        self.class_name = class_name
        self.method_name = method_name
        self.method_descriptor = method_descriptor
        self.argv = argv

        self.stack = []
        self.pc_register = 0
        # Return value of the bottom frame of the nested interpreter loop
        self.return_value = None
        # The java/lang/Thread object of this thread
        self.java_thread = None

    def run(self):
        if self.class_name not in run_time_data.method_area:
            logging.error(
                f'Could not find or load main class {self.class_name}')
            return
        logging.debug('Now we are at the entrance of thread function.')
        klass = run_time_data.method_area[self.class_name]
        method = klass.get_method(self.method_name, self.method_descriptor)
        if not method:
            logging.error(
                f'Could not find method {self.method_name} '
                f'in class {self.class_name}')
            return
        args = []
        if self.method_descriptor == '([Ljava/lang/String;)V':
            args.append(run_time_data.new_array_from_values(
                '[Ljava/lang/String;',
                [run_time_data.new_java_string(arg) for arg in self.argv]
            ))
        try:
            class_loader.initialize_class(klass, self)
            self.invoke(klass, method, args)
        except JavaException as e:
            self.uncaught_exception(e)
            raise
        logging.debug('Method {name} exit'.format(name=self.method_name))
        logging.debug('Thread exit')

    def uncaught_exception(self, exception):
        '''Print the stack trace of uncaught exception by
        Thread.dispatchUncaughtException, if System is initialized.
        '''
        system_err = run_time_data.class_static_fields['java/lang/System'].get(
            ('err', 'Ljava/io/PrintStream;'))
        if self.java_thread is not None and system_err is not None:
            try:
                self.invoke_virtual(
                    self.java_thread, 'dispatchUncaughtException',
                    '(Ljava/lang/Throwable;)V', [exception.throwable])
                return
            except JavaException:
                pass
        logging.error(f'Exception in thread "main" {exception}')

    def invoke(self, klass, method, args):
        '''Invoke method from python, run until the method return and get the
        return value. Category 2 values in args are not padded.
        '''
        impl = method_implementation(klass, method)
        if impl is not None:
            return impl(self, args)
        if method.access_flags.abstract():
            raise RuntimeError(f'Invoke abstract method {method.name}')
        frame = Frame(klass, method, FRAME.pad_arguments(method, args))
        frame.is_base = True
        base = len(self.stack)
        self.stack.append(frame)
        self.return_value = None
        self.execute(base)
        value = self.return_value
        self.return_value = None
        return value

    def invoke_virtual(self, objectref, method_name, method_descriptor, args):
        '''Invoke instance method from python, args not include objectref'''
        klass, method = objectref.klass.select_method(
            method_name, method_descriptor)
        assert method, \
            f'Could not find method {method_name}{method_descriptor} ' \
            f'in {objectref.class_name()}'
        return self.invoke(klass, method, [objectref] + list(args))

    def invoke_static(self, class_name, method_name, method_descriptor, args):
        klass = run_time_data.method_area[class_name]
        klass, method = klass.method_resolution(method_name, method_descriptor)
        assert method, \
            f'Could not find method {method_name}{method_descriptor} ' \
            f'in {class_name}'
        class_loader.initialize_class(klass, self)
        return self.invoke(klass, method, args)

    def invoke_from_frame(self, frame, klass, method):
        '''Invoke method from the instruction of frame, arguments are on the
        operand stack of the frame. Return True if a new frame is pushed.
        '''
        operand_stack = frame.operand_stack
        n = method.arg_slots
        if n:
            slots = operand_stack[-n:]
            del operand_stack[-n:]
        else:
            slots = []
        impl = method_implementation(klass, method)
        if impl is not None:
            value = impl(self, FRAME.unpad_arguments(slots))
            return_type = method.return_type
            if return_type != 'V':
                if return_type == 'Z' and type(value) is bool:
                    value = int(value)
                operand_stack.append(value)
                if return_type in ('J', 'D'):
                    operand_stack.append(PAD)
            return False
        if method.access_flags.abstract():
            self.throw_new(
                'java/lang/AbstractMethodError',
                f'{klass.name()}.{method.method_name.value()}')
        self.stack.append(Frame(klass, method, slots))
        return True

    def method_return(self, frame, value, category2=False):
        self.stack.pop()
        if frame.is_base:
            self.return_value = value
        elif frame.method.return_type != 'V':
            operand_stack = self.stack[-1].operand_stack
            operand_stack.append(value)
            if category2:
                operand_stack.append(PAD)

    def execute(self, base):
        '''Interpreter loop, execute until the frame at `base` returned.'''
        stack = self.stack
        while len(stack) > base:
            frame = stack[-1]
            instructions = frame.code.instructions
            try:
                while True:
                    pc = frame.pc
                    frame.current_pc = pc
                    instr = instructions[pc]
                    frame.pc = instr.next_pc
                    if trace:
                        logging.debug(
                            f'{frame.method.name} '
                            f'{instr.class_name_and_address()} '
                            f'{frame.operand_debug_str()}')
                    if instr.execute(frame, self):
                        # Frame changed by invoke, return, or jump into
                        # exception handler
                        break
            except JavaException as e:
                self.handle_exception(e, base)

    def handle_exception(self, exception, base):
        '''Find exception handler from the top frame, pop frames which can't
        handle the exception. Raise the exception again if can't be handled
        in frames above `base`.
        '''
        throwable = exception.throwable
        stack = self.stack
        while len(stack) > base:
            frame = stack[-1]
            handler_pc = self.find_exception_handler(frame, throwable)
            if handler_pc is not None:
                frame.operand_stack.clear()
                frame.operand_stack.append(throwable)
                frame.pc = handler_pc
                return
            stack.pop()
        raise exception

    def find_exception_handler(self, frame, throwable):
        pc = frame.current_pc
        pool = frame.klass.constant_pool
        for start_pc, end_pc, handler_pc, catch_type in \
                frame.code.exception_table:
            if start_pc <= pc < end_pc:
                if catch_type == 0:
                    return handler_pc
                catch_class = pool.get_constant_class_name(catch_type)
                if throwable.klass.is_subclass_of(catch_class):
                    return handler_pc
        return None

    def new_throwable(self, class_name, message=None):
        klass = run_time_data.method_area[class_name]
        class_loader.initialize_class(klass, self)
        throwable = run_time_data.new_object(klass)
        if message is None:
            method = klass.get_method('<init>', '()V')
            self.invoke(klass, method, [throwable])
        else:
            method = klass.get_method('<init>', '(Ljava/lang/String;)V')
            self.invoke(klass, method, [
                throwable, run_time_data.new_java_string(message)])
        return throwable

    def throw_new(self, class_name, message=None):
        raise JavaException(self.new_throwable(class_name, message))

    def current_class(self, depth=0):
        '''Class of the method in the frame, 0 is the top frame'''
        return self.stack[-1 - depth].klass
