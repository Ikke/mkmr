def find_config(p):
    from pathlib import Path
    from os import getenv

    if p is not None:
        if p.is_file():
            return p
        else:
            raise ValueError("couldn't find configuration file in {}".format(
                             p))

    xdgpath = getenv("XDG_CONFIG_HOME")
    if xdgpath is not None:
        xdgpath = Path(xdgpath)
        xdgpath = xdgpath / 'mkmr' / 'config'

        # Get the parent
        p = xdgpath.parent

        # If the parent exists and is not a directory
        # remove it, we need it to be a directory
        if p.exists() and not p.is_dir():
            p.unlink()

        # Create parent directions of the parent directory
        p.mkdir(parents=True, exist_ok=True)

        # If the file exists but is not a file then remove
        # it is as well
        if xdgpath.exists() and not xdgpath.is_file():
            xdgpath.unlink()

        # Create it with nice permissions for a file that
        # hold secrets
        xdgpath.touch(mode=0o600)
        return xdgpath

    homepath = getenv("HOME")
    if homepath is None:
        raise ValueError("Neither XDG_CONFIG_HOME or HOME are set, please "
                         "set XDG_CONFIG_HOME and place the file in mkmr/"
                         "config relative to it")

    if xdgpath is None:
        xdgpath = Path(homepath)
        xdgpath = xdgpath / '.config' / 'mkmr' / 'config'

        # Get the parent
        p = xdgpath.parent

        # If the parent exists and is not a directory
        # remove it, we need it to be a directory
        if p.exists() and not p.is_dir():
            p.unlink()

        # Create parent directions of the parent directory
        p.mkdir(parents=True, exist_ok=True)

        # If the file exists but is not a file then remove
        # it is as well
        if xdgpath.exists() and not xdgpath.is_file():
            xdgpath.unlink()

        # Create it with nice permissions for a file that
        # hold secrets
        xdgpath.touch(mode=0o600)
        return xdgpath
