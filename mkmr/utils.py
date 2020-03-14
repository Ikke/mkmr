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
        else:
            raise ValueError("couldn't find configuration in {}".format(
                             xdgpath))

    homepath = getenv("HOME")
    if homepath is None:
        raise ValueError("Neither XDG_CONFIG_HOME or HOME are set, please "
                         "set XDG_CONFIG_HOME and place the file in mkmr/"
                         "config relative to it")

    if xdgpath is None:
        xdgpath = path.join(homepath, '.config/mkmr/config')
        if path.isfile(xdgpath):
            return xdgpath
        else:
            raise ValueError("couldn't find configuration file in {}".format(
                             xdgpath))
