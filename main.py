from optparse import OptionParser
from mkmr import mkmr
import gitlab
import git

parser = OptionParser()
parser.add_option("--token",
                  dest="token",
                  action="store",
                  type="string")

args = ["--token", "HARDCODE YOUR OWN HERE"]

(options, args) = parser.parse_args(args)

origin = mkmr()
upstream = mkmr("upstream")

gl = gitlab.Gitlab(upstream.api.host, private_token=options.token)

branch = origin.remote.branch()
commit = origin.remote.commit()
title = commit.message.partition('\n')[0]

upstream_project = gl.projects.get(upstream.api.projectid())
origin_project = gl.projects.get(upstream.api.projectid())

mr = origin_project.mergerequests.create({'source_branch': branch,
                                          'target_branch': 'master',
                                          'title': title,
                                          'target_project_id': upstream.api.projectid})
