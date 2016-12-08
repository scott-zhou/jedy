import struct


def _read_ux_int(fd, x):
    return int.from_bytes(fd.read(x), byteorder='big')


def read_u1_int(fd):
    return _read_ux_int(fd, 1)


def read_u2_int(fd):
    return _read_ux_int(fd, 2)


def read_u4_int(fd):
    return _read_ux_int(fd, 4)


def read_u8_int(fd):
    return _read_ux_int(fd, 8)


def read_u4_float(fd):
    return struct.unpack('>f', fd.read(4))


def read_u8_float(fd):
    return struct.unpack('>f', fd.read(8))


def read_string(fd, length):
    return fd.read(length).decode()
