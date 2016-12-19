import logging
from lib import run_time_data
from lib.frame import Frame
from collections import deque


class Thread(object):
    def __init__(self):
        self.stack = deque()
        self.pc_register = None  # ? How to use it?

    def run(self, classname):
        if classname not in run_time_data.method_area:
            logging.error('Could not find or load main class ' + classname)
            return
        self.invoke_method(classname, 'main', [], [])
        logging.debug('Thread exit')

    def invoke_method(self, classname, funcname, param_types, params):
        klass = run_time_data.method_area[classname]
        method = klass.find_method(funcname)
        if not method:
            logging.error('Could not find method {m} in class {c}'.format(m=funcname, c=classname))
            return
        logging.debug('Now we are at the entrance of main function, almost there...')
        frame = Frame(
            run_time_data.method_area[classname],
            method,
            param_types,
            params
        )
        self.stack.append(frame)
        code = method.code()
        if not code:
            raise RuntimeError('Could not find code in method')
        logging.debug('size of instructions: {0}'.format(len(code.instructions)))
        i = 0
        while i < len(code.instructions):
            code.instructions[i].execute(frame)
            if code.instructions[i].invoke_method:
                return_v = self.invoke_method(
                    code.instructions[i].invoke_class_name,
                    code.instructions[i].invoke_method_name,
                    code.instructions[i].invoke_parameter_types,
                    code.instructions[i].invoke_parameters
                )
                logging.debug('Return of call is {v}'.format(v=return_v))
                if return_v is not None:
                    frame.operand_stack.append(return_v)
            need_jump, to_address = code.instructions[i].jump()
            if need_jump:
                logging.debug('Opps now a slow jump to ' + str(to_address))
                i = 0
                while i < len(code.instructions):
                    if code.instructions[i].address == to_address:
                        break
                    i += 1
            else:
                i += 1
        self.stack.pop()
        logging.debug('Method {name} exit'.format(name=funcname))
