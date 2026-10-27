from collections import defaultdict
from lib import class_loader
from lib import frame as FRAME


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
        return super().__getitem__(klass_name)


method_area = MethodAreaDict()

class_static_fields = defaultdict(dict)

thread_pool = []

# Interned java/lang/String objects, python str -> String object
string_pool = {}

# java/lang/Class objects, class name -> Class object.
# Class name is the internal name ('java/lang/String'), array descriptor
# ('[I') or primitive type name ('int')
class_mirrors = {}

PRIMITIVE_TYPES = {
    'B': 'byte',
    'C': 'char',
    'D': 'double',
    'F': 'float',
    'I': 'int',
    'J': 'long',
    'S': 'short',
    'Z': 'boolean',
    'V': 'void',
}


def new_object(klass):
    obj = FRAME.Object(klass)
    obj.fields = dict(klass.instance_field_defaults())
    return obj


def new_array(array_type, length):
    '''Create array object, `array_type` is the array descriptor, such as
    `[I` or `[[Ljava/lang/Object;`
    '''
    value = FRAME.default_value(array_type[1:])
    return FRAME.ArrayObject(
        method_area['java/lang/Object'], array_type, [value] * length)


def new_array_from_values(array_type, values):
    return FRAME.ArrayObject(
        method_area['java/lang/Object'], array_type, values)


def new_java_string(py_str):
    '''Create a java/lang/String object from python str, which is not
    interned.
    '''
    encoded = py_str.encode('utf-16-be', 'surrogatepass')
    chars = [
        (encoded[i] << 8) | encoded[i + 1] for i in range(0, len(encoded), 2)
    ]
    string = new_object(method_area['java/lang/String'])
    string.set_field('java/lang/String', 'value', new_array_from_values(
        '[C', chars))
    return string


def java_string(py_str):
    '''Interned java/lang/String object of the python str, for string
    literals.
    '''
    string = string_pool.get(py_str)
    if string is None:
        string = new_java_string(py_str)
        string_pool[py_str] = string
    return string


def intern_string(string):
    py_str = py_string(string)
    if py_str not in string_pool:
        string_pool[py_str] = string
    return string_pool[py_str]


def chars_to_py_string(chars):
    data = bytearray()
    for c in chars:
        data.append((c >> 8) & 0xFF)
        data.append(c & 0xFF)
    return data.decode('utf-16-be', 'surrogatepass')


def py_string(string):
    '''Convert java/lang/String object to python str'''
    if string is None:
        return None
    return chars_to_py_string(
        string.get_field('java/lang/String', 'value').values)


def class_mirror(class_name):
    '''Get the java/lang/Class object of the class'''
    mirror = class_mirrors.get(class_name)
    if mirror is None:
        mirror = new_object(method_area['java/lang/Class'])
        mirror.mirror_name = class_name
        class_mirrors[class_name] = mirror
    return mirror


def descriptor_to_class_name(descriptor):
    '''Convert field descriptor to the name used in class mirrors'''
    if descriptor in PRIMITIVE_TYPES:
        return PRIMITIVE_TYPES[descriptor]
    if descriptor[0] == 'L':
        return descriptor[1:-1]
    return descriptor


def class_name_to_descriptor(class_name):
    for descriptor, name in PRIMITIVE_TYPES.items():
        if name == class_name:
            return descriptor
    if class_name[0] == '[':
        return class_name
    return f'L{class_name};'


def is_assignable(source, target):
    '''Return True if a value of type `source` can be assigned to type
    `target`. Both are class names in class mirror format.
    '''
    if source == target:
        return True
    if source in PRIMITIVE_TYPES.values() or \
            target in PRIMITIVE_TYPES.values():
        return False
    if source[0] == '[':
        if target[0] != '[':
            return target in (
                'java/lang/Object', 'java/lang/Cloneable',
                'java/io/Serializable')
        return is_assignable(
            descriptor_to_class_name(source[1:]),
            descriptor_to_class_name(target[1:]))
    if target[0] == '[':
        return False
    return method_area[source].is_subclass_of(target)


def is_instance_of(obj, target):
    return is_assignable(obj.class_name(), target)
