'''Start up of the JVM, create the initial thread and initialize the
system classes, as HotSpot does before invoking the main method.
'''
import logging
from lib import (
    class_loader,
    run_time_data,
)

booted = False


def _new_instance(thread, class_name, descriptor, args):
    klass = run_time_data.method_area[class_name]
    class_loader.initialize_class(klass, thread)
    obj = run_time_data.new_object(klass)
    thread.invoke(klass, klass.get_method('<init>', descriptor), [obj] + args)
    return obj


def create_initial_thread(thread):
    '''Create the java/lang/Thread object for the main thread'''
    system_group = _new_instance(thread, 'java/lang/ThreadGroup', '()V', [])
    main_group = _new_instance(
        thread, 'java/lang/ThreadGroup',
        '(Ljava/lang/ThreadGroup;Ljava/lang/String;)V',
        [system_group, run_time_data.java_string('main')])
    thread_class = run_time_data.method_area['java/lang/Thread']
    class_loader.initialize_class(thread_class, thread)
    java_thread = run_time_data.new_object(thread_class)
    # Thread constructor reads priority and group of current thread
    java_thread.set_field('java/lang/Thread', 'priority', 5)
    java_thread.set_field('java/lang/Thread', 'group', main_group)
    thread.java_thread = java_thread
    thread.invoke(thread_class, thread_class.get_method(
        '<init>', '(Ljava/lang/ThreadGroup;Ljava/lang/String;)V'
    ), [java_thread, main_group, run_time_data.java_string('main')])


def boot(thread):
    '''Initialize the system classes, after that System.out is ready'''
    global booted
    if booted:
        return
    logging.debug('Booting JVM')
    for class_name in (
        'java/lang/Object',
        'java/lang/String',
        'java/lang/System',
        'java/lang/Class',
    ):
        class_loader.initialize_class(
            run_time_data.method_area[class_name], thread)
    create_initial_thread(thread)
    thread.invoke_static(
        'java/lang/System', 'initializeSystemClass', '()V', [])
    booted = True
    logging.debug('JVM booted')
