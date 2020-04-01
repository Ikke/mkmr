from git import Repo
from giturlparse import parse

from mkmr.utils import create_dir, find_cache


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

        try:
            self.host = "https://" + p.domain
        except AttributeError:
            raise AttributeError(
                "url from remote '{}' has no valid URL: {}".format(remote, self.uri)
            )
        try:
            # Some people have a remote that is
            # git@gitlab.alpinelinux.org:/User/Project.git
            # The / in /User causes problems when using pathlib, so strip it here to avoid any
            # future problems
            if p.owner[0] == "/":
                p.owner = p.owner[1:]
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
        # The path should be, as an example taking alpine/aports from gitlab.alpinelinux.org
        # $XDG_CACHE_HOME/mkmr/gitlab.alpinelinux.org/alpine/aports/project-id
        cachedir = create_dir(
            find_cache()
            / self.host.replace("https://", "").replace("/", ".")
            / self.user
            / self.project
        )
        cachepath = cachedir / "project-id"

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
