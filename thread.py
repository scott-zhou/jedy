
class Thread(object):
    def __init__(self):
        self.__stack = []

    def bootstrap(self, class_object):
        print('bootstrap class loader')
