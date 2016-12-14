import struct
import functools


def _read_ux_int(fd, x):
    return int.from_bytes(fd.read(x), byteorder='big')


read_u1_int = functools.partial(_read_ux_int, x=1)
read_u2_int = functools.partial(_read_ux_int, x=2)
read_u4_int = functools.partial(_read_ux_int, x=4)
read_u8_int = functools.partial(_read_ux_int, x=8)


def read_u4_float(fd):
    return struct.unpack('>f', fd.read(4))


def read_u8_float(fd):
    return struct.unpack('>f', fd.read(8))


def read_string(fd, length):
    return fd.read(length).decode()
