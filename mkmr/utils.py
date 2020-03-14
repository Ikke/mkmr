def find_config(p):
    from os import path, getenv

    if p is not None:
        if path.isfile(p):
            return p
        else:
            raise ValueError("couldn't find configuration file in {}".format(
                             p))

    xdgpath = getenv("XDG_CONFIG_HOME")
    if xdgpath is not None:
        xdgpath = path.join(xdgpath, 'mkmr/config')
        if path.isfile(xdgpath):
            return xdgpath

    homepath = getenv("HOME")
    if homepath is not None:
        homepath = path.join(homepath, '.mkmr')
        if path.isfile(homepath):
            return homepath

    raise ValueError("couldn't find configuration file in {} or {}".format(
                     xdgpath, homepath))
