import re


def parse_field_descriptor(field, void=False):
    base_type = [
        ('B', 'byte'),
        ('C', 'char'),
        ('D', 'double'),
        ('F', 'float'),
        ('I', 'int'),
        ('J', 'long'),
        ('S', 'short'),
        ('Z', 'boolean'),
    ]
    if void:
        base_type.append(('V', 'void'))
    base_pattern = '[' + ''.join(t for t, _ in base_type) + ']'
    object_type = [
        ('L.+?;', 'reference'),
    ]
    object_pattern = object_type[0][0]
    array_type = [
        ('\[+' + base_pattern, 'base type array reference'),
        ('\[+' + object_pattern, 'object type array reference'),
    ]
    array_pattern = '|'.join(t for t, _ in array_type)
    field_pattern = '|'.join([base_pattern, object_pattern, array_pattern])
    pattern = re.compile(field_pattern)
    fields = pattern.findall(field)
    return fields


def parse_method_descriptor(method_d):
    pattern = re.compile('\(.*?\)|.+')
    parts = pattern.findall(method_d)
    assert len(parts) == 2, 'Invalid method descriptor {d}'.format(d=method_d)
    assert parts[0][0] == '(', 'Invalid method descriptor {d}'.format(d=method_d)
    parameters = parse_field_descriptor(parts[0][1:-1])
    rt = parse_field_descriptor(parts[1], True)
    return parameters, rt
