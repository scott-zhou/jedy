
class Thread(object):
    def __init__(self):
        self.__stack = []

    def run(self, classname):
        print('start run thread to run class ' + classname)
