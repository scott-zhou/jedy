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
        main_method = run_time_data.method_area[classname].find_method('main')
        if not main_method:
            logging.error('Could not find or load main class ' + classname)
            return
        logging.debug('Now we are at the entrance of main function, almost there...')
        self.invoke_method('main', main_method)
        logging.debug('Thread exit')

    def invoke_method(self, name, method):
        frame = Frame()
        self.stack.append(frame)
        code = method.code()
        if not code:
            raise RuntimeError('Could not find code in method')
        frame.local_variables = [None for _ in range(code.max_locals)]
        logging.debug('size of instructions: {0}'.format(len(code.instructions)))
        i = 0
        while i < len(code.instructions):
            code.instructions[i].execute(frame)
            need_jump, to_address = code.instructions[i].jump()
            if need_jump:
                logging.debug('Opps jump to ' + str(to_address))
                i = 0
                while i < len(code.instructions):
                    if code.instructions[i].address == to_address:
                        break
                    i += 1
            else:
                i += 1
        self.stack.pop()
        logging.debug('Method {name} exit'.format(name=name))
