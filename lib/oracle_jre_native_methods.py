'''We can't use the Oracle JVM native implementation, it's
integrated with it's JVM progress. So we provide own fake
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