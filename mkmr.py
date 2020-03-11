from remote import Remote
from api import Api

class mkmr():
    remote: Remote
    api: Api

    def __init__(self, remote):
        self.remote = Remote(remote)
        self.api = Api(self.remote.url())
