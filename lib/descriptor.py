import re


def parse_field_descriptor(field, void=False):
    field_type = [
        ('B', 'byte'),
        ('C', 'char'),
        ('D', 'double'),
        ('F', 'float'),
        ('I', 'int'),
        ('J', 'long'),
        ('S', 'short'),
        ('Z', 'boolean'),
        ('L[^.;[(]+;', 'reference'),
        ('\[.+\]', 'array reference')
    ]
    if void:
        field_type.append(('V', 'void'))
    field_type_regex = '|'.join(t for t, v in field_type)
    pattern = re.compile(field_type_regex)
    fields = pattern.findall(field)
    return fields


def parse_method_descriptor(method_d):
    pattern = re.compile('\([^\)]+\)|.+')
    parts = pattern.findall(method_d)
    assert len(parts) == 2, 'Invalid method descriptor {d}'.format(d=method_d)
    assert parts[0][0] == '(', 'Invalid method descriptor {d}'.format(d=method_d)
    parameters = parse_field_descriptor(parts[0][1:-1])
    rt = parse_field_descriptor(parts[1], True)
    return parameters, rt
