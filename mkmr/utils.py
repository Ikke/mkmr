from os import getenv
from pathlib import Path
from typing import Optional

from git import Repo, exc


def strtobool(s) -> Optional[bool]:
    """
    Convert a string into a boolean value or None

    True is returned when yes, true or 1 is called
    False is returned when no, false or 0 is called
    None is returned on any other value, we do this because we want to know if we are passing an
    invalid value
    """
    if s.lower() in ("yes", "true", "1"):
        return True
    elif s.lower() in ("no", "false", "0"):
        return False
    else:
        return None


def prompt(s=None) -> None:
    print(s) if s is not None else 0
    input("Press Enter to continue...")


def create_dir(path: Path) -> Path:
    if path.exists() and not path.is_dir():
        path.unlink()

    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    return path


def create_file(path: Path) -> Path:
    # Get the parent
    create_dir(path.parent)

    # If the file exists but is not a file then remove
    # it is as well
    if path.exists() and not path.is_file():
        path.unlink()

    # Create it with nice permissions for a file that
    # hold secrets
    path.touch(mode=0o600)
    return path


def find_config(p: Optional[str]) -> Path:
    if p is not None:
        p = Path(p)
        return create_file(p)

    xdgpath = getenv("XDG_CONFIG_HOME")
    if xdgpath is not None:
        xdgpath = Path(xdgpath)
        return create_file(xdgpath / "mkmr" / "config")

    homepath = getenv("HOME")
    if homepath is None:
        raise ValueError("Neither XDG_CONFIG_HOME or HOME are set, please set XDG_CONFIG_HOME")

    if xdgpath is None:
        xdgpath = Path(homepath)
        return create_file(xdgpath / ".config" / "mkmr" / "config")


def find_cache() -> Path:
    xdgpath = getenv("XDG_CACHE_HOME")
    if xdgpath is not None:
        xdgpath = Path(xdgpath)
        return create_dir(xdgpath / "mkmr")

    homepath = getenv("HOME")
    if homepath is None:
        raise ValueError("Neither XDG_CACHE_HOME or HOME are set, please set XDG_CACHE_HOME")

    if homepath is not None:
        homepath = Path(homepath)
        return create_dir(homepath / ".cache" / "mkmr")


def init_repo(path=None) -> Optional[Repo]:
    if path is None:
        path = Path(getenv("PWD"))

    def _init_repo(path) -> Repo:
        try:
            repo = Repo(path)
        except exc.InvalidGitRepositoryError:
            if path == Path("/"):
                raise
            return _init_repo(path=path.parent)
        else:
            return repo

    try:
        return _init_repo(path)
    except exc.InvalidGitRepositoryError:
        print("Failed to start repo at {} or any of its parent directories".format(path))
        return None
