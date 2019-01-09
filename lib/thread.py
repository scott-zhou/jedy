import logging
from collections import deque
from lib import run_time_data
from lib.frame import Frame
from lib import instruction


class Thread(object):
    def __init__(self, class_name, method_name, method_descriptor, argv):
        self.class_name = class_name
        self.method_name = method_name
        self.method_descriptor = method_descriptor
        self.argv = argv

        self.stack = deque()
        self.pc_register = 0

    def run(self):
        if self.class_name not in run_time_data.method_area:
            logging.error(
                f'Could not find or load main class {self.class_name}')
            return
        logging.debug('Now we are at the entrance of thread function.')
        frame, code = self.method_entrance(
            self.class_name,
            self.method_name,
            [],  # Ignore the parameters for main function for now.
            []
        )
        self.run_thread_method(frame, code)
        logging.debug('Method {name} exit'.format(name=self.method_name))
        logging.debug('Thread exit')

    def method_entrance(self, class_name, method_name, param_types, params):
        klass = run_time_data.method_area[class_name]
        method = klass.find_method(method_name)
        if not method:
            logging.error(
                f'Could not find method {method_name} in class {class_name}')
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

    def run_thread_method(self, frame, code):
        self.stack.append(frame)
        i = 0
        while i < code.code_length:
            self.pc_register = i
            instr = code.instructions[i]
            instr.execute(frame)
            next_step = instr.next_step()
            if next_step == instruction.NextStep.invoke_method:
                # store the next
                frame.next_ops_address = i + 1 + instr.len_of_operand()
                frame, code = self.method_entrance(
                    instr.invoke_class_name,
                    instr.invoke_method_name,
                    instr.invoke_parameter_types,
                    instr.invoke_parameters
                )
                logging.debug(
                    'Invoke method, new frame local_variables: '
                    f'{frame.local_variables}, parameter type: '
                    f'{instr.invoke_parameter_types}'
                )
                self.stack.append(frame)
                i = 0
            elif next_step == instruction.NextStep.jump_to:
                i = instr.jump_to_address
            elif next_step == instruction.NextStep.method_return:
                if len(self.stack) == 1:
                    break  # First frame is for main function, not return value
                self.stack.pop()
                frame = self.stack[-1]
                code = frame.code
                i = frame.next_ops_address
                if instr.return_value is not None:
                    frame.operand_stack.append(instr.return_value)
            else:
                i = i + 1 + instr.len_of_operand()
        self.stack.pop()
