import os
import subprocess
import sys
from unittest import TestCase

JEDY_HOME = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..')


def run_jedy(program_dir, class_name):
    return subprocess.run(
        [
            sys.executable,
            os.path.join(JEDY_HOME, 'jedy.py'),
            '--classpath',
            os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         program_dir),
            class_name,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=600,
    )


class TestJVM(TestCase):
    '''Run program with the JVM booted, System.out is initialized by
    System.initializeSystemClass() of the JRE.
    '''

    def test_hello_world(self):
        result = run_jedy('hello_world', 'Main')
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(result.stdout.decode(), 'Hello World!\n')

    def test_jdk_features(self):
        result = run_jedy('jdk_features', 'Main')
        self.assertEqual(result.returncode, 1, result.stderr.decode())
        self.assertEqual(result.stdout.decode(), '\n'.join([
            'fib(20) = 6765',
            'overflow: -9223372036854775808 -2147483648',
            'div: -3 -1 3 15',
            'double: 0.3333333333333333 float: 0.33333334 '
            '0.10000000149011612',
            'chars: b 122',
            'sorted: [1, 3, 5, 7, 9]',
            '[item4, item3, item2, item1, item0]',
            'the=3 size=9',
            'shape 7.069',
            'square 9.0',
            'MonTueHundredOther',
            'caught CCE',
            'caught 5',
            'finally',
            'caught java.lang.ArithmeticException: / by zero',
            ',2,1,0',
            '3.14159 ff -123456789012',
            '中文 unicode ✓ 96354 HÉLLO',
            '3x4 7',
            '',
        ]))
        self.assertEqual(result.stderr.decode(), '\n'.join([
            'to stderr',
            'Exception in thread "main" java.lang.IllegalStateException: boom',
            '\tat Main.main(Main.java:75)',
            '',
        ]))
