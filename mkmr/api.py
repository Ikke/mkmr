from git import Repo

from mkmr.utils import create_dir


class API:
    host: str
    uri: str
    endpoint: str
    projectid: int
    user: str
    project: str

    def __init__(self, repo: Repo, remote: str):
        """
        Check that we were given a valid remote
        """
        if remote in repo.remotes:
            self.uri = repo.remotes[remote].url
        else:
            raise ValueError("Remote passed does not exist in repository")

        """
        if we have https:// then just apply it, if we have ssh then
        try to convert it to https://, if we have any other then raise
        a ValueError
        """
        if self.uri.startswith("git@"):
            self.uri = self.uri.replace(":", "/").replace("git@", "https://")
        elif self.uri.startswith("ssh://git@"):
            self.uri = self.uri.replace(":", "/").replace("ssh://git@", "https://")
        if self.uri.endswith(".git"):
            self.uri = self.uri.replace(".git", "")

        uri = self.uri.split("/")
        if len(uri) < 5:
            raise ValueError("uri passed must contain owner and repository")

        self.endpoint = "https://" + uri[2] + "/api/v4/projects/"
        self.endpoint = self.endpoint + uri[3] + "%2F" + uri[4]

        self.user = uri[3]
        self.project = uri[4]

        self.host = "https://" + uri[2]

    def projectid(self, token=None) -> int:
        """
        Try to get cached project id
        """
        from pathlib import Path
        from os import getenv

        cachefile = Path(self.uri.replace("https://", "").replace("/", "."))

        cachedir = getenv("XDG_CACHE_HOME")
        if cachedir is not None:
            cachedir = create_dir(Path(cachedir, "mkmr"))
        else:
            homepath = getenv("HOME")
            if homepath is None:
                raise ValueError(
                    "Neither XDG_CONFIG_HOME or HOME are set, "
                    "please set XDG_CACHE_HOME"
                )
            else:
                cachedir = create_dir(Path(homepath, ".cache"))

        cachepath = Path(cachedir / cachefile)

        if cachepath.is_file():
            self.projectid = int(cachepath.read_text())
            return self.projectid

        """
        Call into the gitlab API to get the project id
        """
        from urllib.request import Request, urlopen
        import json

        req = Request(self.endpoint)
        if token is not None:
            req.add_header("Private-Token", token)
        f = urlopen(req).read()
        j = json.loads(f.decode("utf-8"))
        cachepath.write_text(str(j["id"]))
        self.projectid = j["id"]
        return self.projectid
