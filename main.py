from optparse import OptionParser
from api import API
from git import Repo
import gitlab
import sys


def alpine_stable_prefix(str: str) -> str:
    if str.startswith('3.8-'):
        return "3.8"
    elif str.startswith('3.9-'):
        return "3.9"
    elif str.startswith('3.10-'):
        return "3.10"
    elif str.startswith('3.11-'):
        return "3.11"
    else:
        return None


def main():
    parser = OptionParser()
    parser.add_option("--token",
                      dest="token",
                      action="store",
                      type="string",
                      help="GitLab Personal Access Token")
    parser.add_option("--target",
                      dest="target",
                      action="store",
                      type="string",
                      help="branch to make the merge request against")
    parser.add_option("--source",
                      dest="source",
                      action="store",
                      type="string",
                      help="branch from which to make the merge request")
    parser.add_option("--origin",
                      dest="origin",
                      action="store",
                      type="string",
                      default="origin",
                      help="git remote that points to your fork of the repo")
    parser.add_option("--upstream",
                      dest="upstream",
                      action="store",
                      type="string",
                      default="upstream",
                      help="git remote that points to upstream repo")
    parser.add_option("--title",
                      dest="title",
                      action="store",
                      type="string",
                      help="title of the merge request")
    parser.add_option("--description",
                      dest="description",
                      action="store",
                      type="string",
                      help="Description of the merge request")
    parser.add_option("--dry-run",
                      dest="dry_run",
                      action="store_true",
                      help="don't make the merge request, just show how it would look like")

    (options, args) = parser.parse_args(sys.argv)

    if options.token is None:
        s = (
            "Please pass your GitLab Personal Access Token with --token\n"
            "If you don't have one, go to: "
            "https://<GITLAB_HOST>/profile/personal_access_tokens\n"
            "And make one for yourself, this is ABSOLUTELY required"
            )
        print(s)
        sys.exit(1)

    # Initialize our repo object based on the local repo we have
    repo = Repo()

    if options.source is not None:
        source_branch = options.source
    else:
        source_branch = repo.active_branch.name

    if options.target is not None:
        target_branch = options.target
    else:
        target_branch = alpine_stable_prefix(source_branch)
        if target_branch is not None:
            target_branch = target_branch + '-stable'
        else:
            target_branch = "master"

    str = options.upstream + '/' + target_branch
    str = str + '..' + source_branch
    commit_count = len(list(repo.iter_commits(str)))

    if commit_count == 1:
        commit = repo.head.commit
    else:
        # TODO: make it prompt the user to pick the correct
        # commit, preferably with a python equivalent to fzf
        commit = repo.head.commit

    message = commit.message.partition('\n')

    if options.title is not None:
        title = options.title
    else:
        title = message[0]

    if options.description is not None:
        description = options.description
    else:
        # Don't do [1:] because git descriptions have one blank line separating
        # between the title and the description
        description = '\n'.join(message[2:])

    # Call the API using our local repo and have one for remote
    # origin and remote upstream
    origin = API(repo, options.origin)
    upstream = API(repo, options.upstream)

    # git pull --rebase the source branch on top of the target branch
    str = repo.git.pull(
                       options.upstream,
                       "--rebase",
                       target_branch
                       )
    if str != '':
        print(str)

    if options.dry_run is False:
        # git push --quiet upstream source_branch:source_branch
        str = repo.git.push(
                           options.origin,
                           (source_branch + ":" + source_branch)
                           )
        if str != '':
            print(str)

    if options.dry_run is True:
        print("source_branch:", source_branch)
        print("target_branch:", target_branch)
        print("title:", title)
        for l in description.split('\n'):
            print("description:", l)
        print("target_project_id:", upstream.projectid)

        # This is equivalent to git rev-list
        str = options.upstream + '/' + target_branch
        str = str + '..' + source_branch
        commit_count = len(list(repo.iter_commits(str)))
        print("commits:", commit_count)
        sys.exit(0)

    # Using upstream.host or origin.host here is irrelevant since we don't have
    # a federated GitLab, hosts only talk to themselves
    gl = gitlab.Gitlab(upstream.host, private_token=options.token)

    origin_project = gl.projects.get(origin.projectid,
                                     retry_transient_errors=True)

    mr = origin_project.mergerequests.create({
                                             'source_branch': source_branch,
                                             'target_branch': target_branch,
                                             'title': title,
                                             'description': description,
                                             'target_project_id': upstream.projectid
                                             },
                                             retry_transient_errors=True)

    print(mr.attributes)


if __name__ == "__main__":
    main()
