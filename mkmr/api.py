from git import Repo
from giturlparse import parse

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
            raise ValueError(
                "We were passed the remote '{}' which does not exist in the repository".format(
                    remote
                )
            )

        """
        Parse the url with giturlparse and check what values we got from it
        """
        p = parse(self.uri)

        self.host = "https://" + p.domain
        try:
            self.user = p.owner
        except AttributeError:
            raise AttributeError(
                "url from remote '{}' has no component owner in its url: '{}'".format(
                    remote, self.uri
                )
            )
        try:
            self.project = p.repo
        except AttributeError:
            raise AttributeError(
                "url from remote '{}' has no repo component in its url: '{}'".format(
                    remote, self.uri
                )
            )

        self.uri = p.url2https.replace(".git", "")

        self.endpoint = self.host + "/api/v4/projects/"
        self.endpoint = self.endpoint + self.user + "%2F" + self.project

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
                    "Neither XDG_CONFIG_HOME or HOME are set, please set XDG_CACHE_HOME"
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
