'''We can't use the JVM native implementation, it's
integrated with it's JVM progress. So we provide hijacked
implementation in this file.
'''

from collections import defaultdict

IMPS = defaultdict(dict)


def has_native_method(klass, method, descriptor):
    return klass in IMPS and (method, descriptor) in IMPS[klass]


def get_native_method(klass, method, descriptor):
    if has_native_method(klass, method, descriptor):
        return IMPS[klass][(method, descriptor)]
    return None


def native_method(klass, method, descriptor):
    def native_mmethod_decorator(m):
        IMPS[klass][(method, descriptor)] = m
    return native_mmethod_decorator


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


@native_method('sun/misc/Unsafe', 'registerNatives', '()V')
def sun_misc_unsafe_registerNatives(stack):
    pass
