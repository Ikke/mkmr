from git import Repo


class Remote():
    remote: str
    repo: Repo

    def __init__(self, remote_name="origin"):
        self.repo = Repo('.')
        if remote_name in self.repo.remotes:
            self.remote = self.repo.remotes[remote_name]
        else:
            raise ValueError("Remote passed does not exist in repository")

    def url(self) -> str:
        return self.remote.url

    def branch(self) -> str:
        return self.repo.active_branch.name

    def commit(self) -> str:
        return self.repo.head.commit
