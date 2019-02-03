'''We can't use the JVM native implementation, it's
integrated with it's JVM progress. So we provide hijacked
implementation in this file.
'''

from collections import defaultdict
from lib import (
    frame,
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
    print(f' ---- try to get jdk method: {klass} {method} {descriptor}')
    if has_jdk_method(klass, method, descriptor):
        return _JDK_M_IMPLS[klass][(method, descriptor)]
    return None


def native_method(klass, method, descriptor):
    def native_method_decorator(m):
        _NATIVE_IMPS[klass][(method, descriptor)] = m
    return native_method_decorator


@native_method('java/lang/Object', 'registerNatives', '()V')
def java_lang_object_registerNatives(stack):
    pass


@native_method('java/lang/Object', 'getClass', '()Ljava/lang/Class;')
def java_lang_object_getClass(stack):
    stack.append(None)


@native_method('java/lang/System', 'registerNatives', '()V')
def java_lang_system_registerNatives(stack):
    pass


@native_method('java/io/FileDescriptor', 'initIDs', '()V')
def java_io_filedescriptor_initIds(stack):
    pass


@native_method('java/io/FileOutputStream', 'initIDs', '()V')
def java_io_fileoutputstream_initIds(stack):
    pass


@native_method('sun/misc/Unsafe', 'registerNatives', '()V')
def sun_misc_unsafe_registerNatives(stack):
    pass


def jdk_method(klass, method, descriptor):
    def jdk_method_decorator(m):
        _JDK_M_IMPLS[klass][(method, descriptor)] = m
    return jdk_method_decorator


@jdk_method('java/io/FileDescriptor', '<clinit>', '()V')
def java_io_filedescriptor_clinit(stack):
    fd_class = run_time_data.class_static_fields['java/io/FileDescriptor']
    klass = run_time_data.method_area['java/io/FileDescriptor']
    fd_class[('in', 'Ljava/io/FileDescriptor;')] = frame.Object(klass)
    fd_class[('out', 'Ljava/io/FileDescriptor;')] = frame.Object(klass)
    fd_class[('err', 'Ljava/io/FileDescriptor;')] = frame.Object(klass)
    fd_class[('in', 'Ljava/io/FileDescriptor;')].set_field(
        'java/io/FileDescriptor', 'I', 'fd', 0)
    fd_class[('out', 'Ljava/io/FileDescriptor;')].set_field(
        'java/io/FileDescriptor', 'I', 'fd', 1)
    fd_class[('err', 'Ljava/io/FileDescriptor;')].set_field(
        'java/io/FileDescriptor', 'I', 'fd', 2)
