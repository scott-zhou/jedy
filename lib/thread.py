import logging
from lib import run_time_data


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
        code = main_method.code()
        if not code:
            logging.error('Could not find or load main class ' + classname)
            return
        print('Now we are at the entrance of main function, almost there...')
