import logging
from collections import deque
from lib import run_time_data
from lib.frame import Frame
from lib import instruction


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

    def ops_invoke_method(self, classname, funcname, param_types, params):
        klass = run_time_data.method_area[classname]
        method = klass.find_method(funcname)
        if not method:
            logging.error('Could not find method {m} in class {c}'.format(m=funcname, c=classname))
            return
        frame = Frame(
            klass,
            method,
            param_types,
            params
        )
        code = method.code()
        if not code:
            raise RuntimeError('Could not find code in method')
        return frame, code

    def invoke_method(self, classname, funcname, param_types, params):
        logging.debug('Now we are at the entrance of main function, almost there...')
        frame, code = self.ops_invoke_method(classname, funcname, param_types, params)
        self.stack.append(frame)
        logging.debug('size of instructions: {0}'.format(len(code.instructions)))
        i = 0
        while i < code.code_length:
            ops = code.instructions[i]
            ops.execute(frame)
            next_step = ops.next_step()
            if next_step == instruction.NextStep.invoke_method:
                frame.next_ops_address = i + 1 + ops.len_of_operand()  # store the next
                frame, code = self.ops_invoke_method(
                    ops.invoke_class_name,
                    ops.invoke_method_name,
                    ops.invoke_parameter_types,
                    ops.invoke_parameters
                )
                self.stack.append(frame)
                i = 0
            elif next_step == instruction.NextStep.jump_to:
                i = ops.jump_to_address
            elif next_step == instruction.NextStep.method_return:
                if len(self.stack) == 1:
                    # TODO: How to returen value?
                    break
                self.stack.pop()
                frame = self.stack[-1]
                code = frame.code
                i = frame.next_ops_address
                if ops.return_value is not None:
                    frame.operand_stack.append(ops.return_value)
            else:
                i = i + 1 + ops.len_of_operand()
        self.stack.pop()
        logging.debug('Method {name} exit'.format(name=funcname))
