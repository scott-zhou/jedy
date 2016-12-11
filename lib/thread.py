import logging
from lib import run_time_data
from lib.frame import Frame


class Thread(object):
    def __init__(self):
        self.stack = []
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
        self.invoke_method(main_method)

    def invoke_method(self, method):
        frame = Frame()
        self.stack.append(frame)
        code = method.code()
        if not code:
            raise RuntimeError('Could not find code in method')
        logging.debug('size of instructions: {0}'.format(len(code.instructions)))
        for i in code.instructions:
            i.execute(frame)
