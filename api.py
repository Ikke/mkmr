from git import Repo


class API():
    host: str
    uri: str
    endpoint: str
    projectid: int

    def __init__(self, repo: Repo, remote="origin"):
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
        if self.uri.endswith(".git"):
            self.uri = self.uri.replace(".git", "")

        uri = self.uri.split('/')
        if len(uri) < 5:
            raise ValueError("uri passed must contain owner and repository")

        self.endpoint = 'https://' + uri[2] + '/api/v4/projects/'
        self.endpoint = self.endpoint + uri[3] + '%2F' + uri[4]

        self.host = 'https://' + uri[2]

        # Initialize the value of self.projectid, it will use the cache
        # whenever possible
        self.projectid = self.projectid()

    def projectid(self) -> int:
        """
        Try to get cached project id
        """
        from pathlib import Path
        import os
        cachefile = Path(self.uri.replace("https://",  "").replace("/", "."))
        cachedir = Path(os.environ.get('XDG_CACHE_HOME') + '/mkmr')

        cachepath = cachedir / cachefile

        if cachepath.is_file():
            return int(cachepath.read_text())

        if not cachedir.exists():
            cachedir.mkdir(parents=True)
        else:
            if not cachedir.is_dir():
                cachedir.unlink()

        """
        Call into the gitlab API to get the project id
        """
        import urllib.request
        import urllib.parse
        import json

        f = urllib.request.urlopen(self.endpoint).read()
        j = json.loads(f.decode('utf-8'))
        cachepath.write_text(str(j['id']))
        return j['id']
