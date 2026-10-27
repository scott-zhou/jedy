# JEDY
JVM (Java SE 8 Edition) implementation in Python3

## WHY
It's seems ridiculous a JVM run on Python, well, maybe it is.
But for me, it's for learn more about Python, and got more understand about Java, what is Java, why Java, and why not Java.
On the other hand, I don't think programing language is a problem. If I can implement JVM in Python, then I can implement JVM in any other program language.
The most important thing is, ridiculous always means fun ;)

## Usage
```
python3 jedy.py --classpath test/hello_world Main
Hello World!
```
`--debug` prints debug logs, `--trace` also prints every executed instruction.

JEDY boots like a real JVM: it creates the main thread, runs
`System.initializeSystemClass()` from the JRE classes in `openjdk_jre/lib`,
then invokes `main`. So `System.out.println` runs the real `PrintStream`,
`StreamEncoder` and charset encoder bytecode of the JRE. Native methods
(`FileOutputStream.writeBytes`, `System.arraycopy`, `sun.misc.Unsafe`, ...)
are implemented in Python, see `lib/hijack_jre_methods.py`.

Not supported yet: `invokedynamic` (lambdas), multiple threads, reflective
method invocation, and features which need JRE data files not in this
repository (such as `String.format`, which reads `currency.data`).

## Test
Test programs are compiled with `javac --release 8`. Run tests in the
`test` directory (the directory name conflicts with python's `test`
package):
```
cd test
PYTHONPATH=.. python3 -m unittest test_class_loader test_whole_program test_jvm
```

## Author
Created by [Scott Zhou](http://www.scottzhou.me)

## License
This project is licensed under the [MIT license](http://opensource.org/licenses/MIT).

##MISC
JDK version in test: jdk1.8.0_60
