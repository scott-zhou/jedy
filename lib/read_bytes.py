import struct
import functools


def _read_ux_int(fd, x):
    return int.from_bytes(fd.read(x), byteorder='big')


def _read_sx_int(fd, x):
    return int.from_bytes(fd.read(x), byteorder='big', signed=True)


read_u1_int = functools.partial(_read_ux_int, x=1)
read_u2_int = functools.partial(_read_ux_int, x=2)
read_u4_int = functools.partial(_read_ux_int, x=4)
read_u8_int = functools.partial(_read_ux_int, x=8)
read_s4_int = functools.partial(_read_sx_int, x=4)
read_s8_int = functools.partial(_read_sx_int, x=8)


def read_u4_float(fd):
    return struct.unpack('>f', fd.read(4))[0]


def read_u8_double(fd):
    return struct.unpack('>d', fd.read(8))[0]


def read_string(fd, length):
    return fd.read(length).decode()


def read_modified_utf8(fd, length):
    '''Decode the "modified UTF-8" used by class files (JVM spec 4.4.7).
    Null is encoded in two bytes and supplementary characters are encoded
    as surrogate pairs, so the result may contain lone surrogates, one
    for each UTF-16 code unit of the Java string.
    '''
    data = fd.read(length)
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        pass
    chars = []
    i = 0
    while i < len(data):
        b = data[i]
        if b < 0x80:
            chars.append(chr(b))
            i += 1
        elif b & 0xE0 == 0xC0:
            chars.append(chr(((b & 0x1F) << 6) | (data[i + 1] & 0x3F)))
            i += 2
        else:
            chars.append(chr(
                ((b & 0x0F) << 12) |
                ((data[i + 1] & 0x3F) << 6) |
                (data[i + 2] & 0x3F)
            ))
            i += 3
    return ''.join(chars)
