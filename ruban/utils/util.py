import os


def first_or_none(list_, default=None):
    return list_[0] if list_ else default


def get_program_name():
    import __main__

    filename = getattr(__main__, '__file__', None)
    if filename is not None:
        filename = os.path.basename(filename)
        for suffix in ('.py', '.pyc'):
            if filename.endswith(suffix):
                filename = filename[:-len(suffix)]
    return filename


def ensure_dir(path, quite=False):
    if quite:
        try:
            return ensure_dir(path, quite=False)
        except:
            return

    # 非安静模式，会抛异常
    items = [item for item in os.path.abspath(path).split('/') if item]
    path = '/'
    already_ensure = True
    for item in items:
        path = os.path.join(path, item)
        if os.path.exists(path):
            assert(os.path.isdir(path))
        else:
            os.mkdir(path)
            already_ensure = False

    return already_ensure


def pop_key_default(data, key, default=None, ctype=None):
    try:
        value = data.pop(key, default)
        if ctype == int:
            value = ctype(value)
        else:
            value = ctype and ctype(value) or value
    except:
        value = default
    return value
