'''Parse JVM class file, according JAVA SE 8 spec
'''
import os
import logging
from lib import (
    attributes,
    constant_pool,
    descriptor,
    frame,
    read_bytes,
    run_time_data
)
from lib.hijack_jre_methods import get_jdk_method

classpath = './'
jrelibpath = './openjdk_jre/lib'
java_home = ''
java_library_path = ''
printclass = False

local_variable_callbacks = {}


class ClassStruct(object):
    '''Store compiled class structures such as the run-time
    constant pool, field and method data, and the code for
    methods and constructors, including the special methods
    used in class and instance initialization and interface
    initialization.
    '''

    def __init__(self):
        self.magic = 0
        self.minor_version = 0
        self.major_version = 0
        self.constant_pool = None
        self.access_flags = 0
        self.this_class = 0
        self.super_class = 0
        self.interfaces_count = 0
        self.interfaces = []
        self.fields_count = 0
        self.fields = []
        self.methods_count = 0
        self.methods = []
        self.attributes_count = 0
        self.attributes = []
        self._name = None
        self._super_klass = None
        self.methods_dict = {}
        self.selected_methods = {}
        self.subclass_cache = {}
        # Class initialization state: None means not initialized
        # 'initializing' or 'initialized'
        self.init_state = None

    def name(self):
        if self._name is None:
            self._name = self.constant_pool.get_constant_class_name(
                self.this_class)
        return self._name

    def get_field(self, field):
        return (
            self.constant_pool[field.name_index].value(),
            self.constant_pool[field.descriptor_index].value()
        )

    def has_field(self, field_name, field_descriptor):
        for field in self.fields:
            if self.get_field(field) == (field_name, field_descriptor):
                return True
        return False

    def field_resolution(self, field_name, field_descriptor):
        '''Field resolution according JVM spec 5.4.3.2, return the class
        which declares the field.
        '''
        if self.has_field(field_name, field_descriptor):
            return self
        for interface in self.superinterfaces():
            klass = interface.field_resolution(field_name, field_descriptor)
            if klass:
                return klass
        super_class = self.get_super_class()
        if super_class:
            return super_class.field_resolution(field_name, field_descriptor)
        return None

    def get_method(self, method_name, method_description):
        return self.methods_dict.get((method_name, method_description))

    def method_resolution(self, method_name, method_description):
        klass = self
        while klass:
            method = klass.get_method(method_name, method_description)
            if method:
                return klass, method
            klass = klass.get_super_class()
        return None, None

    def interface_resolution(self, method_name, method_description):
        resolved_class, resolved_method = self.method_resolution(
            method_name, method_description
        )
        if resolved_class and resolved_method:
            return resolved_class, resolved_method
        return self.superinterface_method(method_name, method_description)

    def superinterface_method(self, method_name, method_description):
        '''Find method in all superinterfaces, prefer the non abstract one
        (default method).
        '''
        found = None
        klass = self
        while klass:
            for interface in klass.all_superinterfaces():
                method = interface.get_method(method_name, method_description)
                if method and not method.access_flags.static() and \
                        not method.access_flags.private():
                    if not method.access_flags.abstract():
                        return interface, method
                    if not found:
                        found = (interface, method)
            klass = klass.get_super_class()
        return found if found else (None, None)

    def select_method(self, method_name, method_description):
        '''Method selection for invokevirtual and invokeinterface, according
        the runtime class of the object.
        '''
        key = (method_name, method_description)
        if key not in self.selected_methods:
            klass, method = self.method_resolution(
                method_name, method_description)
            if not method or method.access_flags.abstract():
                default_klass, default_method = self.superinterface_method(
                    method_name, method_description)
                if default_method:
                    klass, method = default_klass, default_method
            self.selected_methods[key] = (klass, method)
        return self.selected_methods[key]

    def method_name(self, method):
        return self.constant_pool[method.name_index].value()

    def get_super_class(self):
        if self.super_class == 0:
            # No super class
            return None
        if self._super_klass is None:
            self._super_klass = run_time_data.method_area[
                self.constant_pool.get_constant_class_name(self.super_class)
            ]
        return self._super_klass

    def superinterfaces(self):
        for i in self.interfaces:
            yield run_time_data.method_area[
                self.constant_pool.get_constant_class_name(i)
            ]

    def all_superinterfaces(self):
        for interface in self.superinterfaces():
            yield interface
            yield from interface.all_superinterfaces()

    def is_interface(self):
        return self.access_flags.interface()

    def is_subclass_of(self, class_name):
        '''Return True if this class is the class `class_name`, or a
        subclass of it, or implements it.
        '''
        if class_name not in self.subclass_cache:
            result = False
            if self.name() == class_name:
                result = True
            else:
                super_class = self.get_super_class()
                if super_class and super_class.is_subclass_of(class_name):
                    result = True
                else:
                    for interface in self.superinterfaces():
                        if interface.is_subclass_of(class_name):
                            result = True
                            break
            self.subclass_cache[class_name] = result
        return self.subclass_cache[class_name]

    def prepare(self):
        '''Preparation, create static fields and initialize them to default
        values, or the ConstantValue attribute.
        '''
        static_fields = run_time_data.class_static_fields[self.name()]
        for field in self.fields:
            if not field.access_flags.static():
                continue
            name, descriptor = self.get_field(field)
            value = frame.default_value(descriptor)
            for attr in field.attributes:
                if type(attr) is attributes.ConstantValueAttribute:
                    constant = self.constant_pool[attr.constantvalue_index]
                    if type(constant) is constant_pool.ConstantString:
                        value = run_time_data.java_string(
                            self.constant_pool[constant.string_index].value())
                    else:
                        value = constant.value
            static_fields[(name, descriptor)] = value

    def instance_field_defaults(self):
        '''All instance fields of this class and super classes with default
        values, as {(declaring class name, field name): value}.
        '''
        if not hasattr(self, '_instance_field_defaults'):
            defaults = {}
            super_class = self.get_super_class()
            if super_class:
                defaults.update(super_class.instance_field_defaults())
            for field in self.fields:
                if field.access_flags.static():
                    continue
                name, field_descriptor = self.get_field(field)
                defaults[(self.name(), name)] = frame.default_value(field_descriptor)
            self._instance_field_defaults = defaults
        return self._instance_field_defaults

    def source_file(self):
        for attr in self.attributes:
            if type(attr) is attributes.SourceFileAttribute:
                return attr.source_file
        return None

    def validate(self):
        '''Valid if class struct according to spec
        Raise ValueError if any fail validation
        '''
        # Well, trust it now.
        pass

    def debug_info(self):
        if not printclass:
            return
        logging.debug('Class file info')
        logging.debug('Magic number: 0x{:X}'.format(self.magic))
        logging.debug('Major version:' + str(self.major_version))
        logging.debug('Minor version:' + str(self.minor_version))
        logging.debug('Constant count:' + str(self.constant_pool.count))
        for index in range(1, self.constant_pool.count):
            self.constant_pool[index].debug_info(
                f'\tCONSTANT_POOL[{index}] ->', self)
        self.access_flags.debug_info()
        logging.debug(
            'This class index: {0} ({1})'.format(
                str(self.this_class),
                self.constant_pool.get_constant_class_name(self.this_class)
            )
        )
        if self.super_class == 0:
            logging.debug(
                'This class do not have super class, must be '
                'java/lang/Object'
            )
        else:
            super_class_name =\
                self.constant_pool.get_constant_class_name(self.super_class)
            logging.debug(
                f'Super class index: {self.super_class} ({super_class_name})'
            )
        logging.debug('Interface count:' + str(self.interfaces_count))
        for interface in self.interfaces:
            logging.debug(
                '\tinterface index in constant_pool:' + str(interface))
        logging.debug('Fields count:' + str(self.fields_count))
        logging.debug('Methods count:' + str(self.methods_count))
        for method in self.methods:
            method.debug_info(self)
        logging.debug('Attributes count:' + str(self.attributes_count))
        for attr in self.attributes:
            attr.debug_info()


class BootstrapClassLoader(object):
    '''Class for parse and store a JAVA class file
    '''

    def __init__(self):
        pass

    def parse(self, fd) -> ClassStruct:
        class_struct = ClassStruct()
        class_struct.magic = read_bytes.read_u4_int(fd)
        assert class_struct.magic == 0xCAFEBABE,\
            f'Magic number ({class_struct.magic}) in class file is wrong'
        class_struct.minor_version = read_bytes.read_u2_int(fd)
        class_struct.major_version = read_bytes.read_u2_int(fd)
        class_struct.constant_pool = constant_pool.parse(fd)
        class_struct.access_flags = AccessFlags()
        class_struct.access_flags.parse(fd)
        class_struct.this_class = read_bytes.read_u2_int(fd)
        class_struct.super_class = read_bytes.read_u2_int(fd)
        class_struct.interfaces_count = read_bytes.read_u2_int(fd)
        for _ in range(class_struct.interfaces_count):
            class_struct.interfaces.append(read_bytes.read_u2_int(fd))
        class_struct.fields_count = read_bytes.read_u2_int(fd)
        for _ in range(class_struct.fields_count):
            field = Field()
            field.parse(fd, class_struct)
            class_struct.fields.append(field)
        class_struct.methods_count = read_bytes.read_u2_int(fd)
        for _ in range(class_struct.methods_count):
            method = Method()
            method.parse(fd, class_struct)
            class_struct.methods.append(method)
            class_struct.methods_dict[
                (method.method_name.value(), method.descriptor)] = method
        (class_struct.attributes_count, class_struct.attributes) =\
            attributes.parse(fd, class_struct)
        assert len(fd.read(1)) == 0,\
            'Class file is finish parsed, but still data left in tail.'
        class_struct.validate()
        return class_struct


class _GenericAccessFlags(object):
    '''Generic part for access_flags item for class, interface, field and method
    '''

    def __init__(self):
        self._flags = 0

    def parse(self, fd):
        self._flags = read_bytes.read_u2_int(fd)

    def public(self):
        return (self._flags & 0x0001 > 0)

    def private(self):
        return (self._flags & 0x0002 > 0)

    def protected(self):
        return (self._flags & 0x0004 > 0)

    def static(self):
        return (self._flags & 0x0008 > 0)

    def final(self):
        return (self._flags & 0x0010 > 0)

    def abstract(self):
        return (self._flags & 0x0400 > 0)

    def synthetic(self):
        return (self._flags & 0x1000 > 0)

    def enum(self):
        return (self._flags & 0x4000 > 0)


class AccessFlags(_GenericAccessFlags):
    '''access_flags item is a mask of flags used to denote access
    permissions to and properties of this class or interface
    '''

    def __init__(self):
        super(AccessFlags, self).__init__()

    def super(self):
        return (self._flags & 0x0020 > 0)

    def interface(self):
        return (self._flags & 0x0200 > 0)

    def annotation(self):
        return (self._flags & 0x2000 > 0)

    def debug_info(self):
        logging.debug('access_flags - ACC_PUBLIC:' + str(self.public()))
        logging.debug('access_flags - ACC_FINAL:' + str(self.final()))
        logging.debug('access_flags - ACC_SUPER:' + str(self.super()))
        logging.debug('access_flags - ACC_INTERFACE:' + str(self.interface()))
        logging.debug('access_flags - ACC_ABSTRACT:' + str(self.abstract()))
        logging.debug('access_flags - ACC_SYNTHETIC:' + str(self.synthetic()))
        logging.debug(
            'access_flags - ACC_ANNOTATION:' + str(self.annotation()))
        logging.debug('access_flags - ACC_ENUM:' + str(self.enum()))


class Field(object):
    def __init__(self):
        pass

    class AccessFlags(_GenericAccessFlags):
        '''access_flags item is a mask of flags used to denote access
        permission to and properties of this field.
        '''

        def __init__(self):
            super(Field.AccessFlags, self).__init__()

        def volatile(self):
            return (self._flags & 0x0040 > 0)

        def transient(self):
            return (self._flags & 0x0080 > 0)

        def debug_info(self, prefix):
            logging.debug(
                f'{prefix}access_flags - ACC_PUBLIC: {self.public()}')
            logging.debug(
                f'{prefix}access_flags - ACC_PRIVATE: {self.private()}')
            logging.debug(
                f'{prefix}access_flags - ACC_PROTECTED: {self.protected()}')
            logging.debug(
                f'{prefix}access_flags - ACC_STATIC: {self.static()}')
            logging.debug(
                f'{prefix}access_flags - ACC_FINAL: {self.final()}')
            logging.debug(
                f'{prefix}access_flags - ACC_VOLATILE: {self.volatile()}')
            logging.debug(
                f'{prefix}access_flags - ACC_TRANSIENT: {self.transient()}')
            logging.debug(
                f'{prefix}access_flags - ACC_SYNTHETIC: {self.synthetic()}')
            logging.debug(
                f'{prefix}access_flags - ACC_ENUM: {self.enum()}')

    def parse(self, fd, class_file):
        self.access_flags = Field.AccessFlags()
        self.access_flags.parse(fd)
        self.name_index = read_bytes.read_u2_int(fd)
        self.descriptor_index = read_bytes.read_u2_int(fd)
        (self.attributes_count, self.attributes) =\
            attributes.parse(fd, class_file)

    def debug_info(self):
        logging.debug(f'Field  - name index: {self.name_index}')
        logging.debug(f'       - descriptor index: {self.descriptor_index}')
        self.access_flags.debug_info('       - ')
        logging.debug(f'       - attributes count: {self.attributes_count}')
        for attr in self.attributes:
            attr.debug_info('       - ')


class Method(object):
    def __init__(self):
        pass

    class AccessFlags(_GenericAccessFlags):
        '''access_flags item is a mask of flags used to denote access
        permission to and properties of this method.
        '''

        def __init__(self):
            super(Method.AccessFlags, self).__init__()

        def synchronized(self):
            return (self._flags & 0x0020 > 0)

        def bridge(self):
            return (self._flags & 0x0040 > 0)

        def varargs(self):
            return (self._flags & 0x0080 > 0)

        def native(self):
            return (self._flags & 0x0100 > 0)

        def strict(self):
            return (self._flags & 0x0800 > 0)

        def debug_info(self, prefix):
            logging.debug(
                f'{prefix}access_flags - ACC_PUBLIC: {self.public()}')
            logging.debug(
                f'{prefix}access_flags - ACC_PRIVATE: {self.private()}')
            logging.debug(
                f'{prefix}access_flags - ACC_PROTECTED: {self.protected()}')
            logging.debug(
                f'{prefix}access_flags - ACC_STATIC: {self.static()}')
            logging.debug(
                f'{prefix}access_flags - ACC_FINAL: {self.final()}')
            logging.debug(f'{prefix}access_flags - ACC_SYNCHRONIZED: '
                          f'{self.synchronized()}')
            logging.debug(
                f'{prefix}access_flags - ACC_BRIDGE: {self.bridge()}')
            logging.debug(
                f'{prefix}access_flags - ACC_VARARGS: {self.varargs()}')
            logging.debug(
                f'{prefix}access_flags - ACC_NATIVE: {self.native()}')
            logging.debug(
                f'{prefix}access_flags - ACC_ABSTRACT: {self.abstract()}')
            logging.debug(
                f'{prefix}access_flags - ACC_STRICT: {self.strict()}')
            logging.debug(
                f'{prefix}access_flags - ACC_SYNTHETIC: {self.synthetic()}')

    def parse(self, fd, class_file):
        self.access_flags = Method.AccessFlags()
        self.access_flags.parse(fd)
        self.name_index = read_bytes.read_u2_int(fd)
        self.descriptor_index = read_bytes.read_u2_int(fd)
        self.attributes_count, self.attributes =\
            attributes.parse(fd, class_file)
        class_name = class_file.name()
        method_name = class_file.constant_pool[self.name_index]
        assert type(method_name) is constant_pool.ConstantUtf8,\
            'Parse method: method name_index in constant_pool is'\
            ' not CONSTANT_Utf8_info'
        self.class_name = class_name
        self.method_name = method_name
        self.name = f'{class_name}.{method_name.value()}'
        self.descriptor =\
            class_file.constant_pool[self.descriptor_index].value()
        self.parameter_types, return_type = \
            descriptor.parse_method_descriptor(self.descriptor)
        self.return_type = return_type[0]
        self.arg_slots = sum(
            2 if t in ('J', 'D') else 1 for t in self.parameter_types)
        if not self.access_flags.static():
            self.arg_slots += 1
        self._code = False

    def code(self):
        if self._code is False:
            self._code = None
            for attr in self.attributes:
                if type(attr) is attributes.CodeAttribute:
                    # Only one code attribute in Method
                    self._code = attr
                    break
        return self._code

    def debug_info(self, class_struct):
        name = class_struct.constant_pool[self.name_index].value()
        logging.debug(
            'Method - name index:' +
            str(self.name_index) +
            ' ("{0}")'.format(name)
        )
        logging.debug(
            '       - descriptor index:' +
            str(self.descriptor_index) +
            ' ("{0}")'.format(self.descriptor)
        )
        self.access_flags.debug_info('       - ')
        logging.debug(f'       - attributes count: {self.attributes_count}')
        for attr in self.attributes:
            attr.debug_info('       -       - ')

    def isSignaturePolymorphic(self):
        return self.class_name == 'java/lang/invoke/MethodHandle' and \
            self.descriptor == '([Ljava/lang/Object;)Ljava/lang/Object;' and \
            self.access_flags.varargs() and\
            self.access_flags.native()


def parse(file_name: str, loader=BootstrapClassLoader):
    class_loader = loader()
    with open(file_name, 'rb') as java_class_file:
        class_struct = class_loader.parse(java_class_file)
    return class_struct


def initialize_class(class_struct: ClassStruct, current_thread) -> None:
    '''Class initialization according JVM spec 5.5, invoke class or
    interface initialization method. Single thread only.
    '''
    if class_struct.init_state is not None:
        # Initialized, or being initialized by current thread
        return
    class_struct.init_state = 'initializing'
    if not class_struct.is_interface():
        super_class = class_struct.get_super_class()
        if super_class:
            initialize_class(super_class, current_thread)
    class_name = class_struct.name()
    method_name, method_description = '<clinit>', '()V'
    hijacked_method = get_jdk_method(
        class_name, method_name, method_description)
    if hijacked_method:
        hijacked_method(current_thread, [])
    else:
        method = class_struct.get_method(method_name, method_description)
        if method:
            logging.debug(f'Initialize class {class_name}')
            current_thread.invoke(class_struct, method, [])
    # can be no class initialization method
    class_struct.init_state = 'initialized'


def find_class_file(classname: str):
    filename = classname + '.class'
    # First try class path, then try jre lib path
    for path in (classpath, jrelibpath):
        if path and os.path.isfile(os.path.join(path, filename)):
            return os.path.join(path, filename)
    return None


def load_class(classname: str) -> ClassStruct:
    """Load and link the class, but not initialize it. The class is loaded
    again if it's already in method area.
    :param classname: str, represent the name of class
    :return: ClassStruct object if the class is success loaded, otherwise None
    """
    possible_path = find_class_file(classname)
    if not possible_path:
        logging.warning(f'Can not find {classname} class file.')
        return None

    logging.debug(f'Load class {classname} from {possible_path}')
    class_struct = parse(possible_path)
    run_time_data.method_area[classname] = class_struct
    class_struct.debug_info()
    class_struct.prepare()
    return class_struct


def init_class_object(klass, obj):
    fields = obj.fields
    for key, value in klass.instance_field_defaults().items():
        fields[key] = value
