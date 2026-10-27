'''We can't use the JVM native implementation, it's
integrated with it's JVM progress. So we provide hijacked
implementation in this file.

Both native methods and hijacked JRE methods are python functions as
`func(thread, args)`, `args` is the argument list (objectref is the first
one for instance method, category 2 values are not padded). The return
value of the function is the return value of the method.
'''

import logging
import math
import os
import struct
import sys
import time
from collections import defaultdict
from lib import (
    frame as FRAME,
    run_time_data
)


_NATIVE_IMPS = defaultdict(dict)
_JDK_M_IMPLS = defaultdict(dict)


def has_native_method(klass, method, descriptor):
    return klass in _NATIVE_IMPS and \
        (method, descriptor) in _NATIVE_IMPS[klass]


def get_native_method(klass, method, descriptor):
    if has_native_method(klass, method, descriptor):
        return _NATIVE_IMPS[klass][(method, descriptor)]
    return None


def has_jdk_method(klass, method, descriptor):
    return klass in _JDK_M_IMPLS and \
        (method, descriptor) in _JDK_M_IMPLS[klass]


def get_jdk_method(klass, method, descriptor):
    if has_jdk_method(klass, method, descriptor):
        return _JDK_M_IMPLS[klass][(method, descriptor)]
    return None


def native_method(klass, method, descriptor):
    def native_method_decorator(m):
        _NATIVE_IMPS[klass][(method, descriptor)] = m
        return m
    return native_method_decorator


def jdk_method(klass, method, descriptor):
    def jdk_method_decorator(m):
        _JDK_M_IMPLS[klass][(method, descriptor)] = m
        return m
    return jdk_method_decorator


def _no_op(thread, args):
    return None


for _klass in (
    'java/lang/Object',
    'java/lang/Class',
    'java/lang/System',
    'java/lang/Thread',
    'java/lang/ClassLoader',
    'sun/misc/Unsafe',
    'sun/misc/Perf',
):
    native_method(_klass, 'registerNatives', '()V')(_no_op)

for _klass in (
    'java/io/FileDescriptor',
    'java/io/FileInputStream',
    'java/io/FileOutputStream',
    'java/io/UnixFileSystem',
    'java/lang/ClassLoader$NativeLibrary',
):
    native_method(_klass, 'initIDs', '()V')(_no_op)


def _field(obj, class_name, field_name):
    return obj.fields[(class_name, field_name)]


def _set_field(obj, class_name, field_name, value):
    obj.fields[(class_name, field_name)] = value


def _jstr(py_str):
    return run_time_data.new_java_string(py_str)


def _pystr(string):
    return run_time_data.py_string(string)


def _identity_hash(obj):
    if obj is None:
        return 0
    return (id(obj) >> 4) & 0x7FFFFFFF


'''java/lang/Object'''


@native_method('java/lang/Object', 'getClass', '()Ljava/lang/Class;')
def java_lang_object_getClass(thread, args):
    return run_time_data.class_mirror(args[0].class_name())


@native_method('java/lang/Object', 'hashCode', '()I')
def java_lang_object_hashCode(thread, args):
    return _identity_hash(args[0])


@native_method('java/lang/Object', 'clone', '()Ljava/lang/Object;')
def java_lang_object_clone(thread, args):
    obj = args[0]
    if isinstance(obj, FRAME.ArrayObject):
        return run_time_data.new_array_from_values(
            obj.array_type, list(obj.values))
    if not obj.klass.is_subclass_of('java/lang/Cloneable'):
        thread.throw_new(
            'java/lang/CloneNotSupportedException',
            obj.class_name().replace('/', '.'))
    clone = FRAME.Object(obj.klass)
    clone.fields = dict(obj.fields)
    return clone


native_method('java/lang/Object', 'notify', '()V')(_no_op)
native_method('java/lang/Object', 'notifyAll', '()V')(_no_op)
native_method('java/lang/Object', 'wait', '(J)V')(_no_op)


'''java/lang/Class'''


def _mirror_name(mirror):
    return mirror.mirror_name


def _mirror_class(mirror):
    '''ClassStruct of the class mirror, None for array and primitive'''
    name = mirror.mirror_name
    if name[0] == '[' or name in run_time_data.PRIMITIVE_TYPES.values():
        return None
    return run_time_data.method_area[name]


@native_method(
    'java/lang/Class', 'getPrimitiveClass',
    '(Ljava/lang/String;)Ljava/lang/Class;')
def java_lang_class_getPrimitiveClass(thread, args):
    return run_time_data.class_mirror(_pystr(args[0]))


@native_method(
    'java/lang/Class', 'desiredAssertionStatus0', '(Ljava/lang/Class;)Z')
def java_lang_class_desiredAssertionStatus0(thread, args):
    return 0


@native_method('java/lang/Class', 'getName0', '()Ljava/lang/String;')
def java_lang_class_getName0(thread, args):
    return run_time_data.java_string(
        _mirror_name(args[0]).replace('/', '.'))


@native_method('java/lang/Class', 'isArray', '()Z')
def java_lang_class_isArray(thread, args):
    return 1 if _mirror_name(args[0])[0] == '[' else 0


@native_method('java/lang/Class', 'isPrimitive', '()Z')
def java_lang_class_isPrimitive(thread, args):
    return 1 if _mirror_name(args[0]) in \
        run_time_data.PRIMITIVE_TYPES.values() else 0


@native_method('java/lang/Class', 'isInterface', '()Z')
def java_lang_class_isInterface(thread, args):
    klass = _mirror_class(args[0])
    return 1 if klass and klass.is_interface() else 0


@native_method('java/lang/Class', 'getSuperclass', '()Ljava/lang/Class;')
def java_lang_class_getSuperclass(thread, args):
    name = _mirror_name(args[0])
    if name[0] == '[':
        return run_time_data.class_mirror('java/lang/Object')
    klass = _mirror_class(args[0])
    if not klass or klass.is_interface():
        return None
    super_class = klass.get_super_class()
    if not super_class:
        return None
    return run_time_data.class_mirror(super_class.name())


@native_method('java/lang/Class', 'getInterfaces0', '()[Ljava/lang/Class;')
def java_lang_class_getInterfaces0(thread, args):
    klass = _mirror_class(args[0])
    interfaces = []
    if klass:
        interfaces = [
            run_time_data.class_mirror(i.name())
            for i in klass.superinterfaces()
        ]
    elif _mirror_name(args[0])[0] == '[':
        interfaces = [
            run_time_data.class_mirror('java/lang/Cloneable'),
            run_time_data.class_mirror('java/io/Serializable'),
        ]
    return run_time_data.new_array_from_values(
        '[Ljava/lang/Class;', interfaces)


@native_method('java/lang/Class', 'getComponentType', '()Ljava/lang/Class;')
def java_lang_class_getComponentType(thread, args):
    name = _mirror_name(args[0])
    if name[0] != '[':
        return None
    return run_time_data.class_mirror(
        run_time_data.descriptor_to_class_name(name[1:]))


@native_method('java/lang/Class', 'isAssignableFrom', '(Ljava/lang/Class;)Z')
def java_lang_class_isAssignableFrom(thread, args):
    if args[1] is None:
        thread.throw_new('java/lang/NullPointerException')
    return 1 if run_time_data.is_assignable(
        _mirror_name(args[1]), _mirror_name(args[0])) else 0


@native_method('java/lang/Class', 'isInstance', '(Ljava/lang/Object;)Z')
def java_lang_class_isInstance(thread, args):
    if args[1] is None:
        return 0
    return 1 if run_time_data.is_instance_of(
        args[1], _mirror_name(args[0])) else 0


@native_method('java/lang/Class', 'getModifiers', '()I')
def java_lang_class_getModifiers(thread, args):
    klass = _mirror_class(args[0])
    if not klass:
        # public final abstract
        return 0x0001 | 0x0010 | 0x0400
    return klass.access_flags._flags & 0x7631


@native_method(
    'java/lang/Class', 'forName0',
    '(Ljava/lang/String;ZLjava/lang/ClassLoader;Ljava/lang/Class;)'
    'Ljava/lang/Class;')
def java_lang_class_forName0(thread, args):
    from lib import class_loader
    name = _pystr(args[0]).replace('.', '/')
    if name[0] == '[':
        return run_time_data.class_mirror(name)
    klass = None
    if name in run_time_data.method_area or \
            class_loader.find_class_file(name):
        klass = run_time_data.method_area[name]
    if not klass:
        thread.throw_new(
            'java/lang/ClassNotFoundException', name.replace('/', '.'))
    if args[1]:
        class_loader.initialize_class(klass, thread)
    return run_time_data.class_mirror(name)


for _method, _descriptor in (
    ('getDeclaringClass0', '()Ljava/lang/Class;'),
    ('getEnclosingMethod0', '()[Ljava/lang/Object;'),
    ('getGenericSignature0', '()Ljava/lang/String;'),
    ('getRawAnnotations', '()[B'),
    ('getRawTypeAnnotations', '()[B'),
    ('getProtectionDomain0', '()Ljava/security/ProtectionDomain;'),
    ('getSigners', '()[Ljava/lang/Object;'),
):
    native_method('java/lang/Class', _method, _descriptor)(_no_op)


@native_method(
    'java/lang/Class', 'getDeclaredFields0',
    '(Z)[Ljava/lang/reflect/Field;')
def java_lang_class_getDeclaredFields0(thread, args):
    mirror, public_only = args
    klass = _mirror_class(mirror)
    fields = []
    if klass:
        field_class = run_time_data.method_area['java/lang/reflect/Field']
        constructor = field_class.get_method(
            '<init>',
            '(Ljava/lang/Class;Ljava/lang/String;Ljava/lang/Class;IILjava/'
            'lang/String;[B)V')
        for slot, field in enumerate(klass.fields):
            if public_only and not field.access_flags.public():
                continue
            name, descriptor = klass.get_field(field)
            field_obj = run_time_data.new_object(field_class)
            thread.invoke(field_class, constructor, [
                field_obj,
                mirror,
                run_time_data.java_string(name),
                run_time_data.class_mirror(
                    run_time_data.descriptor_to_class_name(descriptor)),
                field.access_flags._flags,
                slot,
                None,
                None,
            ])
            fields.append(field_obj)
    return run_time_data.new_array_from_values(
        '[Ljava/lang/reflect/Field;', fields)


@native_method(
    'java/lang/Class', 'getDeclaredConstructors0',
    '(Z)[Ljava/lang/reflect/Constructor;')
def java_lang_class_getDeclaredConstructors0(thread, args):
    mirror, public_only = args
    klass = _mirror_class(mirror)
    constructors = []
    if klass:
        constructor_class = run_time_data.method_area[
            'java/lang/reflect/Constructor']
        init = constructor_class.get_method(
            '<init>',
            '(Ljava/lang/Class;[Ljava/lang/Class;[Ljava/lang/Class;IILjava/'
            'lang/String;[B[B)V')
        for slot, method in enumerate(klass.methods):
            if method.method_name.value() != '<init>':
                continue
            if public_only and not method.access_flags.public():
                continue
            parameter_types = run_time_data.new_array_from_values(
                '[Ljava/lang/Class;', [
                    run_time_data.class_mirror(
                        run_time_data.descriptor_to_class_name(t))
                    for t in method.parameter_types
                ])
            constructor = run_time_data.new_object(constructor_class)
            thread.invoke(constructor_class, init, [
                constructor,
                mirror,
                parameter_types,
                run_time_data.new_array('[Ljava/lang/Class;', 0),
                method.access_flags._flags,
                slot,
                None,
                None,
                None,
            ])
            constructors.append(constructor)
    return run_time_data.new_array_from_values(
        '[Ljava/lang/reflect/Constructor;', constructors)


'''java/lang/System'''


@native_method('java/lang/System', 'currentTimeMillis', '()J')
def java_lang_system_currentTimeMillis(thread, args):
    return int(time.time() * 1000)


@native_method('java/lang/System', 'nanoTime', '()J')
def java_lang_system_nanoTime(thread, args):
    return time.monotonic_ns()


@native_method('java/lang/System', 'identityHashCode', '(Ljava/lang/Object;)I')
def java_lang_system_identityHashCode(thread, args):
    return _identity_hash(args[0])


@native_method(
    'java/lang/System', 'arraycopy',
    '(Ljava/lang/Object;ILjava/lang/Object;II)V')
def java_lang_system_arraycopy(thread, args):
    src, src_pos, dest, dest_pos, length = args
    if src is None or dest is None:
        thread.throw_new('java/lang/NullPointerException')
    if not isinstance(src, FRAME.ArrayObject) or \
            not isinstance(dest, FRAME.ArrayObject):
        thread.throw_new('java/lang/ArrayStoreException')
    if src_pos < 0 or dest_pos < 0 or length < 0 or \
            src_pos + length > len(src.values) or \
            dest_pos + length > len(dest.values):
        thread.throw_new('java/lang/ArrayIndexOutOfBoundsException')
    dest.values[dest_pos:dest_pos + length] = \
        src.values[src_pos:src_pos + length]


def _system_properties():
    java_home = os.path.realpath(os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'openjdk_jre'))
    return {
        'java.home': java_home,
        'java.class.path': '.',
        'java.library.path': '',
        'java.vm.name': 'JEDY',
        'java.vm.vendor': 'JEDY',
        'java.vm.version': '0.1',
        'java.vm.specification.name': 'Java Virtual Machine Specification',
        'java.vm.specification.vendor': 'Oracle Corporation',
        'java.vm.specification.version': '1.8',
        'java.specification.version': '1.8',
        'java.class.version': '52.0',
        'java.io.tmpdir': '/tmp',
        'file.encoding': 'UTF-8',
        'sun.jnu.encoding': 'UTF-8',
        'file.encoding.pkg': 'sun.io',
        'file.separator': '/',
        'path.separator': ':',
        'line.separator': '\n',
        'os.name': 'Linux',
        'os.arch': 'amd64',
        'os.version': '',
        'user.name': os.environ.get('USER', ''),
        'user.home': os.path.expanduser('~'),
        'user.dir': os.getcwd(),
        'user.language': 'en',
        'sun.arch.data.model': '64',
        'sun.cpu.endian': 'little',
        'sun.io.unicode.encoding': 'UnicodeLittle',
        'sun.boot.library.path': '',
        'sun.boot.class.path': os.path.join(java_home, 'lib'),
    }


@native_method(
    'java/lang/System', 'initProperties',
    '(Ljava/util/Properties;)Ljava/util/Properties;')
def java_lang_system_initProperties(thread, args):
    props = args[0]
    for key, value in _system_properties().items():
        thread.invoke_virtual(
            props, 'setProperty',
            '(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/Object;',
            [_jstr(key), _jstr(value)])
    return props


def _set_system_stream(name, descriptor):
    def set_stream(thread, args):
        run_time_data.class_static_fields['java/lang/System'][
            (name, descriptor)] = args[0]
    return set_stream


native_method('java/lang/System', 'setIn0', '(Ljava/io/InputStream;)V')(
    _set_system_stream('in', 'Ljava/io/InputStream;'))
native_method('java/lang/System', 'setOut0', '(Ljava/io/PrintStream;)V')(
    _set_system_stream('out', 'Ljava/io/PrintStream;'))
native_method('java/lang/System', 'setErr0', '(Ljava/io/PrintStream;)V')(
    _set_system_stream('err', 'Ljava/io/PrintStream;'))


@native_method(
    'java/lang/System', 'mapLibraryName',
    '(Ljava/lang/String;)Ljava/lang/String;')
def java_lang_system_mapLibraryName(thread, args):
    return _jstr(f'lib{_pystr(args[0])}.so')


@jdk_method('java/lang/System', 'loadLibrary', '(Ljava/lang/String;)V')
def java_lang_system_loadLibrary(thread, args):
    '''Native libraries are implemented in python, nothing to load'''
    pass


@jdk_method('java/lang/Terminator', 'setup', '()V')
def java_lang_terminator_setup(thread, args):
    '''Signal handlers are not supported'''
    pass


'''java/lang/Thread'''


@native_method('java/lang/Thread', 'currentThread', '()Ljava/lang/Thread;')
def java_lang_thread_currentThread(thread, args):
    return thread.java_thread


@native_method('java/lang/Thread', 'isAlive', '()Z')
def java_lang_thread_isAlive(thread, args):
    return 1 if args[0] is thread.java_thread else 0


@native_method('java/lang/Thread', 'start0', '()V')
def java_lang_thread_start0(thread, args):
    name = _pystr(_field(args[0], 'java/lang/Thread', 'name'))
    logging.debug(f'Thread is not supported, thread {name} is not started.')


@native_method('java/lang/Thread', 'isInterrupted', '(Z)Z')
def java_lang_thread_isInterrupted(thread, args):
    return 0


@native_method('java/lang/Thread', 'holdsLock', '(Ljava/lang/Object;)Z')
def java_lang_thread_holdsLock(thread, args):
    return 1


@native_method('java/lang/Thread', 'sleep', '(J)V')
def java_lang_thread_sleep(thread, args):
    time.sleep(args[0] / 1000)


native_method('java/lang/Thread', 'setPriority0', '(I)V')(_no_op)
native_method('java/lang/Thread', 'yield', '()V')(_no_op)
native_method('java/lang/Thread', 'interrupt0', '()V')(_no_op)
native_method('java/lang/Thread', 'setNativeName', '(Ljava/lang/String;)V')(
    _no_op)


'''java/lang/Throwable'''


@native_method(
    'java/lang/Throwable', 'fillInStackTrace',
    '(I)Ljava/lang/Throwable;')
def java_lang_throwable_fillInStackTrace(thread, args):
    throwable = args[0]
    backtrace = []
    skipping = True
    for frame in reversed(thread.stack):
        method_name = frame.method.method_name.value()
        if skipping:
            if method_name == 'fillInStackTrace' or (
                method_name == '<init>' and
                throwable.klass.is_subclass_of(frame.klass.name())
            ):
                continue
            skipping = False
        backtrace.append((
            frame.klass.name().replace('/', '.'),
            method_name,
            frame.klass.source_file(),
            frame.code.line_number(frame.current_pc),
        ))
    throwable.backtrace = backtrace
    return throwable


@native_method('java/lang/Throwable', 'getStackTraceDepth', '()I')
def java_lang_throwable_getStackTraceDepth(thread, args):
    return len(getattr(args[0], 'backtrace', []))


@native_method(
    'java/lang/Throwable', 'getStackTraceElement',
    '(I)Ljava/lang/StackTraceElement;')
def java_lang_throwable_getStackTraceElement(thread, args):
    class_name, method_name, file_name, line = args[0].backtrace[args[1]]
    klass = run_time_data.method_area['java/lang/StackTraceElement']
    element = run_time_data.new_object(klass)
    thread.invoke(klass, klass.get_method(
        '<init>',
        '(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;I)V'
    ), [
        element,
        _jstr(class_name),
        _jstr(method_name),
        _jstr(file_name) if file_name else None,
        line,
    ])
    return element


'''java/lang/String, Float, Double, Math'''


@native_method('java/lang/String', 'intern', '()Ljava/lang/String;')
def java_lang_string_intern(thread, args):
    return run_time_data.intern_string(args[0])


@native_method('java/lang/Float', 'floatToRawIntBits', '(F)I')
def java_lang_float_floatToRawIntBits(thread, args):
    return struct.unpack('>i', struct.pack('>f', args[0]))[0]


@native_method('java/lang/Float', 'intBitsToFloat', '(I)F')
def java_lang_float_intBitsToFloat(thread, args):
    return struct.unpack('>f', struct.pack('>i', args[0]))[0]


@native_method('java/lang/Double', 'doubleToRawLongBits', '(D)J')
def java_lang_double_doubleToRawLongBits(thread, args):
    return struct.unpack('>q', struct.pack('>d', args[0]))[0]


@native_method('java/lang/Double', 'longBitsToDouble', '(J)D')
def java_lang_double_longBitsToDouble(thread, args):
    return struct.unpack('>d', struct.pack('>q', args[0]))[0]


for _name, _function in (
    ('sin', math.sin), ('cos', math.cos), ('tan', math.tan),
    ('asin', math.asin), ('acos', math.acos), ('atan', math.atan),
    ('exp', math.exp), ('log', math.log), ('log10', math.log10),
    ('sqrt', math.sqrt), ('cbrt', lambda x: math.copysign(
        abs(x) ** (1 / 3), x)),
    ('sinh', math.sinh), ('cosh', math.cosh), ('tanh', math.tanh),
    ('expm1', math.expm1), ('log1p', math.log1p),
):
    def _math(thread, args, function=_function):
        try:
            return function(args[0])
        except (ValueError, OverflowError):
            return math.nan
    native_method('java/lang/StrictMath', _name, '(D)D')(_math)

native_method('java/lang/StrictMath', 'pow', '(DD)D')(
    lambda thread, args: math.pow(args[0], args[1]))
native_method('java/lang/StrictMath', 'atan2', '(DD)D')(
    lambda thread, args: math.atan2(args[0], args[1]))
native_method('java/lang/StrictMath', 'hypot', '(DD)D')(
    lambda thread, args: math.hypot(args[0], args[1]))
native_method('java/lang/StrictMath', 'IEEEremainder', '(DD)D')(
    lambda thread, args: math.remainder(args[0], args[1]))


'''java/lang/Runtime'''


native_method('java/lang/Runtime', 'availableProcessors', '()I')(
    lambda thread, args: 1)
native_method('java/lang/Runtime', 'freeMemory', '()J')(
    lambda thread, args: 64 * 1024 * 1024)
native_method('java/lang/Runtime', 'totalMemory', '()J')(
    lambda thread, args: 128 * 1024 * 1024)
native_method('java/lang/Runtime', 'maxMemory', '()J')(
    lambda thread, args: 256 * 1024 * 1024)
native_method('java/lang/Runtime', 'gc', '()V')(_no_op)


'''java/security/AccessController'''


def _do_privileged(exception_action):
    def do_privileged(thread, args):
        from lib.thread import JavaException
        action = args[0]
        if action is None:
            thread.throw_new('java/lang/NullPointerException')
        try:
            return thread.invoke_virtual(
                action, 'run', '()Ljava/lang/Object;', [])
        except JavaException as e:
            if not exception_action or \
                    e.throwable.klass.is_subclass_of(
                        'java/lang/RuntimeException'):
                raise
            klass = run_time_data.method_area[
                'java/security/PrivilegedActionException']
            wrapper = run_time_data.new_object(klass)
            thread.invoke(klass, klass.get_method(
                '<init>', '(Ljava/lang/Exception;)V'
            ), [wrapper, e.throwable])
            raise JavaException(wrapper)
    return do_privileged


for _action, _is_exception_action in (
    ('Ljava/security/PrivilegedAction;', False),
    ('Ljava/security/PrivilegedExceptionAction;', True),
):
    native_method(
        'java/security/AccessController', 'doPrivileged',
        f'({_action})Ljava/lang/Object;'
    )(_do_privileged(_is_exception_action))
    native_method(
        'java/security/AccessController', 'doPrivileged',
        f'({_action}Ljava/security/AccessControlContext;)Ljava/lang/Object;'
    )(_do_privileged(_is_exception_action))

native_method(
    'java/security/AccessController', 'getStackAccessControlContext',
    '()Ljava/security/AccessControlContext;')(_no_op)
native_method(
    'java/security/AccessController', 'getInheritedAccessControlContext',
    '()Ljava/security/AccessControlContext;')(_no_op)


'''sun/misc/VM, sun/reflect/Reflection'''


native_method('sun/misc/VM', 'initialize', '()V')(_no_op)
native_method(
    'sun/misc/VM', 'latestUserDefinedLoader0',
    '()Ljava/lang/ClassLoader;')(_no_op)


def _caller_class(thread, depth):
    '''Class of the method `depth` frames below the top frame, skip
    frames of reflection.
    '''
    frames = [
        f for f in reversed(thread.stack)
        if f.method.name != 'java/lang/reflect/Method.invoke'
    ]
    if depth >= len(frames):
        return None
    return run_time_data.class_mirror(frames[depth].klass.name())


@native_method(
    'sun/reflect/Reflection', 'getCallerClass', '()Ljava/lang/Class;')
def sun_reflect_reflection_getCallerClass(thread, args):
    # Top frame is the caller sensitive method which calls getCallerClass,
    # its caller is the frame below.
    return _caller_class(thread, 1)


@native_method(
    'sun/reflect/Reflection', 'getCallerClass', '(I)Ljava/lang/Class;')
def sun_reflect_reflection_getCallerClass_depth(thread, args):
    # Depth 0 is Reflection itself, which has no frame here
    return _caller_class(thread, args[0] - 1)


@native_method(
    'sun/reflect/Reflection', 'getClassAccessFlags', '(Ljava/lang/Class;)I')
def sun_reflect_reflection_getClassAccessFlags(thread, args):
    klass = _mirror_class(args[0])
    return klass.access_flags._flags if klass else 0x0411


'''java/io'''


def _file_descriptor(stream, class_name):
    fd = _field(stream, class_name, 'fd')
    return _field(fd, 'java/io/FileDescriptor', 'fd')


def _write(fd, data):
    if fd == 1:
        sys.stdout.flush()
    elif fd == 2:
        sys.stderr.flush()
    os.write(fd, data)


@native_method('java/io/FileOutputStream', 'writeBytes', '([BIIZ)V')
def java_io_fileoutputstream_writeBytes(thread, args):
    stream, data, offset, length, _ = args
    if data is None:
        thread.throw_new('java/lang/NullPointerException')
    if offset < 0 or length < 0 or offset + length > len(data.values):
        thread.throw_new('java/lang/IndexOutOfBoundsException')
    _write(
        _file_descriptor(stream, 'java/io/FileOutputStream'),
        bytes(b & 0xFF for b in data.values[offset:offset + length]))


@native_method('java/io/FileOutputStream', 'write', '(IZ)V')
def java_io_fileoutputstream_write(thread, args):
    stream, b, _ = args
    _write(
        _file_descriptor(stream, 'java/io/FileOutputStream'),
        bytes([b & 0xFF]))


@native_method('java/io/FileInputStream', 'readBytes', '([BII)I')
def java_io_fileinputstream_readBytes(thread, args):
    stream, data, offset, length = args
    if length == 0:
        return 0
    content = os.read(
        _file_descriptor(stream, 'java/io/FileInputStream'), length)
    if not content:
        return -1
    data.values[offset:offset + len(content)] = [
        ((b + 0x80) & 0xFF) - 0x80 for b in content]
    return len(content)


@native_method('java/io/FileInputStream', 'available0', '()I')
def java_io_fileinputstream_available0(thread, args):
    fd = _file_descriptor(args[0], 'java/io/FileInputStream')
    try:
        current = os.lseek(fd, 0, os.SEEK_CUR)
        return os.fstat(fd).st_size - current
    except OSError:
        return 0


'''sun/misc/Unsafe

Field offset of object field is the index in `_field_offsets`, field offset
of array element is the index of element.
'''

_field_offsets = []


def _field_offset(class_name, field_name):
    key = (class_name, field_name)
    if key not in _field_offsets:
        _field_offsets.append(key)
    return _field_offsets.index(key)


def _unsafe_get(obj, offset):
    if isinstance(obj, FRAME.ArrayObject):
        return obj.values[offset]
    class_name, field_name = _field_offsets[offset]
    if hasattr(obj, 'mirror_name') and \
            (class_name, field_name) not in obj.fields:
        # Static field, obj is the class mirror
        for key, value in run_time_data.class_static_fields[
                class_name].items():
            if key[0] == field_name:
                return value
    return obj.fields[(class_name, field_name)]


def _unsafe_put(obj, offset, value):
    if isinstance(obj, FRAME.ArrayObject):
        obj.values[offset] = value
        return
    class_name, field_name = _field_offsets[offset]
    if hasattr(obj, 'mirror_name') and \
            (class_name, field_name) not in obj.fields:
        static_fields = run_time_data.class_static_fields[class_name]
        for key in static_fields:
            if key[0] == field_name:
                static_fields[key] = value
                return
    obj.fields[(class_name, field_name)] = value


def _reflect_field_key(field):
    clazz = _field(field, 'java/lang/reflect/Field', 'clazz')
    name = _pystr(_field(field, 'java/lang/reflect/Field', 'name'))
    return _mirror_name(clazz), name


@native_method(
    'sun/misc/Unsafe', 'objectFieldOffset', '(Ljava/lang/reflect/Field;)J')
def sun_misc_unsafe_objectFieldOffset(thread, args):
    return _field_offset(*_reflect_field_key(args[1]))


native_method(
    'sun/misc/Unsafe', 'staticFieldOffset', '(Ljava/lang/reflect/Field;)J'
)(sun_misc_unsafe_objectFieldOffset)


@native_method(
    'sun/misc/Unsafe', 'staticFieldBase',
    '(Ljava/lang/reflect/Field;)Ljava/lang/Object;')
def sun_misc_unsafe_staticFieldBase(thread, args):
    return _field(args[1], 'java/lang/reflect/Field', 'clazz')


native_method('sun/misc/Unsafe', 'arrayBaseOffset', '(Ljava/lang/Class;)I')(
    lambda thread, args: 0)
native_method('sun/misc/Unsafe', 'arrayIndexScale', '(Ljava/lang/Class;)I')(
    lambda thread, args: 1)
native_method('sun/misc/Unsafe', 'addressSize', '()I')(
    lambda thread, args: 8)
native_method('sun/misc/Unsafe', 'pageSize', '()I')(
    lambda thread, args: 4096)
native_method('sun/misc/Unsafe', 'storeFence', '()V')(_no_op)
native_method('sun/misc/Unsafe', 'loadFence', '()V')(_no_op)
native_method('sun/misc/Unsafe', 'fullFence', '()V')(_no_op)


@native_method('sun/misc/Unsafe', 'ensureClassInitialized',
               '(Ljava/lang/Class;)V')
def sun_misc_unsafe_ensureClassInitialized(thread, args):
    from lib import class_loader
    klass = _mirror_class(args[1])
    if klass:
        class_loader.initialize_class(klass, thread)


@native_method('sun/misc/Unsafe', 'shouldBeInitialized',
               '(Ljava/lang/Class;)Z')
def sun_misc_unsafe_shouldBeInitialized(thread, args):
    klass = _mirror_class(args[1])
    return 1 if klass and klass.init_state is None else 0


def _compare_and_swap(thread, args):
    _, obj, offset, expected, value = args
    current = _unsafe_get(obj, offset)
    if current is expected or (
            not isinstance(current, FRAME.Object) and current == expected):
        _unsafe_put(obj, offset, value)
        return 1
    return 0


for _type in ('Int', 'Long', 'Object'):
    _descriptor = {'Int': 'I', 'Long': 'J', 'Object': 'Ljava/lang/Object;'}[
        _type]
    native_method(
        'sun/misc/Unsafe', f'compareAndSwap{_type}',
        f'(Ljava/lang/Object;J{_descriptor}{_descriptor})Z'
    )(_compare_and_swap)
    for _suffix in ('', 'Volatile'):
        native_method(
            'sun/misc/Unsafe', f'get{_type}{_suffix}',
            f'(Ljava/lang/Object;J){_descriptor}'
        )(lambda thread, args: _unsafe_get(args[1], args[2]))
        native_method(
            'sun/misc/Unsafe', f'put{_type}{_suffix}',
            f'(Ljava/lang/Object;J{_descriptor})V'
        )(lambda thread, args: _unsafe_put(args[1], args[2], args[3]))
    native_method(
        'sun/misc/Unsafe', f'putOrdered{_type}',
        f'(Ljava/lang/Object;J{_descriptor})V'
    )(lambda thread, args: _unsafe_put(args[1], args[2], args[3]))
for _type, _descriptor in (
    ('Boolean', 'Z'), ('Byte', 'B'), ('Short', 'S'), ('Char', 'C'),
    ('Float', 'F'), ('Double', 'D')
):
    for _suffix in ('', 'Volatile'):
        native_method(
            'sun/misc/Unsafe', f'get{_type}{_suffix}',
            f'(Ljava/lang/Object;J){_descriptor}'
        )(lambda thread, args: _unsafe_get(args[1], args[2]))
        native_method(
            'sun/misc/Unsafe', f'put{_type}{_suffix}',
            f'(Ljava/lang/Object;J{_descriptor})V'
        )(lambda thread, args: _unsafe_put(args[1], args[2], args[3]))


'''Off-heap memory of Unsafe, address -> bytearray'''
_memory = {}
_next_address = [0x10000]


def _find_memory(address):
    for start, block in _memory.items():
        if start <= address < start + len(block):
            return block, address - start
    raise RuntimeError(f'Invalid memory address {address}')


@native_method('sun/misc/Unsafe', 'allocateMemory', '(J)J')
def sun_misc_unsafe_allocateMemory(thread, args):
    address = _next_address[0]
    _memory[address] = bytearray(max(args[1], 1))
    _next_address[0] += max(args[1], 1) + 16
    return address


@native_method('sun/misc/Unsafe', 'freeMemory', '(J)V')
def sun_misc_unsafe_freeMemory(thread, args):
    _memory.pop(args[1], None)


def _memory_access(fmt):
    size = struct.calcsize(fmt)

    def get(thread, args):
        block, offset = _find_memory(args[1])
        return struct.unpack('<' + fmt, block[offset:offset + size])[0]

    def put(thread, args):
        block, offset = _find_memory(args[1])
        block[offset:offset + size] = struct.pack('<' + fmt, args[2])
    return get, put


for _type, _descriptor, _fmt in (
    ('Byte', 'B', 'b'), ('Short', 'S', 'h'), ('Char', 'C', 'H'),
    ('Int', 'I', 'i'), ('Long', 'J', 'q'), ('Float', 'F', 'f'),
    ('Double', 'D', 'd'),
):
    _get, _put = _memory_access(_fmt)
    native_method('sun/misc/Unsafe', f'get{_type}', f'(J){_descriptor}')(_get)
    native_method(
        'sun/misc/Unsafe', f'put{_type}', f'(J{_descriptor})V')(_put)


'''sun/reflect'''


_BOX_CLASSES = {
    'Z': 'java/lang/Boolean', 'B': 'java/lang/Byte', 'C': 'java/lang/Character',
    'S': 'java/lang/Short', 'I': 'java/lang/Integer', 'J': 'java/lang/Long',
    'F': 'java/lang/Float', 'D': 'java/lang/Double',
}


def _unbox(value, value_type):
    if value_type in _BOX_CLASSES:
        return _field(value, _BOX_CLASSES[value_type], 'value')
    return value


@native_method(
    'sun/reflect/NativeConstructorAccessorImpl', 'newInstance0',
    '(Ljava/lang/reflect/Constructor;[Ljava/lang/Object;)Ljava/lang/Object;')
def sun_reflect_nativeconstructoraccessorimpl_newInstance0(thread, args):
    from lib import class_loader
    constructor, arguments = args
    mirror = _field(constructor, 'java/lang/reflect/Constructor', 'clazz')
    slot = _field(constructor, 'java/lang/reflect/Constructor', 'slot')
    klass = _mirror_class(mirror)
    class_loader.initialize_class(klass, thread)
    method = klass.methods[slot]
    values = arguments.values if arguments else []
    obj = run_time_data.new_object(klass)
    thread.invoke(klass, method, [obj] + [
        _unbox(v, t) for v, t in zip(values, method.parameter_types)])
    return obj


native_method('java/util/concurrent/atomic/AtomicLong', 'VMSupportsCS8', '()Z')(
    lambda thread, args: 1)


'''java/io/UnixFileSystem'''


def _file_path(file_obj):
    return _pystr(_field(file_obj, 'java/io/File', 'path'))


@native_method(
    'java/io/UnixFileSystem', 'getBooleanAttributes0', '(Ljava/io/File;)I')
def java_io_unixfilesystem_getBooleanAttributes0(thread, args):
    path = _file_path(args[1])
    if not os.path.exists(path):
        return 0
    attributes = 0x01
    if os.path.isfile(path):
        attributes |= 0x02
    if os.path.isdir(path):
        attributes |= 0x04
    if os.path.basename(path).startswith('.'):
        attributes |= 0x08
    return attributes


@native_method(
    'java/io/UnixFileSystem', 'canonicalize0',
    '(Ljava/lang/String;)Ljava/lang/String;')
def java_io_unixfilesystem_canonicalize0(thread, args):
    return _jstr(os.path.realpath(_pystr(args[1])))


@native_method('java/io/UnixFileSystem', 'getLength', '(Ljava/io/File;)J')
def java_io_unixfilesystem_getLength(thread, args):
    try:
        return os.path.getsize(_file_path(args[1]))
    except OSError:
        return 0


@native_method(
    'java/io/UnixFileSystem', 'getLastModifiedTime', '(Ljava/io/File;)J')
def java_io_unixfilesystem_getLastModifiedTime(thread, args):
    try:
        return int(os.path.getmtime(_file_path(args[1])) * 1000)
    except OSError:
        return 0


@native_method(
    'java/io/UnixFileSystem', 'checkAccess', '(Ljava/io/File;I)Z')
def java_io_unixfilesystem_checkAccess(thread, args):
    mode = {4: os.R_OK, 2: os.W_OK, 1: os.X_OK}.get(args[2], os.F_OK)
    return 1 if os.access(_file_path(args[1]), mode) else 0


@native_method(
    'java/io/UnixFileSystem', 'list', '(Ljava/io/File;)[Ljava/lang/String;')
def java_io_unixfilesystem_list(thread, args):
    try:
        names = os.listdir(_file_path(args[1]))
    except OSError:
        return None
    return run_time_data.new_array_from_values(
        '[Ljava/lang/String;', [_jstr(name) for name in names])


native_method(
    'sun/misc/URLClassPath', 'getLookupCacheURLs',
    '(Ljava/lang/ClassLoader;)[Ljava/net/URL;')(_no_op)


'''java/lang/ClassLoader

There is only one class loader in JEDY, which loads classes from both class
path and JRE, so all classes are loaded as bootstrap classes.
'''


def _find_class(name):
    from lib import class_loader
    name = name.replace('.', '/')
    if name in run_time_data.method_area or \
            class_loader.find_class_file(name):
        run_time_data.method_area[name]
        return run_time_data.class_mirror(name)
    return None


@native_method(
    'java/lang/ClassLoader', 'findLoadedClass0',
    '(Ljava/lang/String;)Ljava/lang/Class;')
def java_lang_classloader_findLoadedClass0(thread, args):
    name = _pystr(args[1]).replace('.', '/')
    if name in run_time_data.method_area:
        return run_time_data.class_mirror(name)
    return None


@native_method(
    'java/lang/ClassLoader', 'findBootstrapClass',
    '(Ljava/lang/String;)Ljava/lang/Class;')
def java_lang_classloader_findBootstrapClass(thread, args):
    return _find_class(_pystr(args[1]))


def _open_file(class_name, flags):
    def open0(thread, args):
        stream, path = args[0], _pystr(args[1])
        try:
            fd = os.open(path, flags, 0o666)
        except OSError as e:
            thread.throw_new(
                'java/io/FileNotFoundException', f'{path} ({e.strerror})')
        logging.debug(f'Open file {path} as fd {fd}')
        _set_field(
            _field(stream, class_name, 'fd'), 'java/io/FileDescriptor',
            'fd', fd)
    return open0


native_method(
    'java/io/FileInputStream', 'open0', '(Ljava/lang/String;)V'
)(_open_file('java/io/FileInputStream', os.O_RDONLY))


@native_method(
    'java/io/FileOutputStream', 'open0', '(Ljava/lang/String;Z)V')
def java_io_fileoutputstream_open0(thread, args):
    flags = os.O_WRONLY | os.O_CREAT | \
        (os.O_APPEND if args[2] else os.O_TRUNC)
    _open_file('java/io/FileOutputStream', flags)(thread, args[:2])


def _close_file(class_name):
    def close0(thread, args):
        fd_obj = _field(args[0], class_name, 'fd')
        fd = _field(fd_obj, 'java/io/FileDescriptor', 'fd')
        if fd > 2:
            os.close(fd)
        _set_field(fd_obj, 'java/io/FileDescriptor', 'fd', -1)
    return close0


native_method('java/io/FileInputStream', 'close0', '()V')(
    _close_file('java/io/FileInputStream'))
native_method('java/io/FileOutputStream', 'close0', '()V')(
    _close_file('java/io/FileOutputStream'))


@native_method('java/io/FileInputStream', 'read0', '()I')
def java_io_fileinputstream_read0(thread, args):
    content = os.read(
        _file_descriptor(args[0], 'java/io/FileInputStream'), 1)
    return content[0] if content else -1


@native_method('java/io/FileInputStream', 'skip', '(J)J')
def java_io_fileinputstream_skip(thread, args):
    fd = _file_descriptor(args[0], 'java/io/FileInputStream')
    current = os.lseek(fd, 0, os.SEEK_CUR)
    end = os.lseek(fd, 0, os.SEEK_END)
    target = min(current + args[1], end)
    os.lseek(fd, target, os.SEEK_SET)
    return target - current
