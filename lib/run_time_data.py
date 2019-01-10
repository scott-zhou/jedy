from lib import class_loader


'''Defind all run-time data for JVM
'''

# pc Register in thread

# Stack in thread

heap = []


class MethodAreaDict(dict):
    def __getitem__(self, klass_name):
        if klass_name not in self:
            class_struct = class_loader.load_class(klass_name)
            assert class_struct, f'Load class {klass_name} fail.'

            class_struct.debug_info()
        return super().__getitem__(klass_name)


method_area = MethodAreaDict()

thread_pool = []
