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
    parser.add_option("--labels",
                      dest="labels",
                      action="store",
                      type="string",
                      help="comma separated list of labels for the merge request")
    parser.add_option("--dry-run",
                      dest="dry_run",
                      action="store_true",
                      default=False,
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

    # Call the API using our local repo and have one for remote
    # origin and remote upstream
    origin = API(repo, options.origin)
    upstream = API(repo, options.upstream)

    if options.source is not None:
        source_branch = options.source
    else:
        source_branch = repo.active_branch.name

    # Enable alpine-specific features
    if "gitlab.alpinelinux.org" in upstream.host:
        alpine = True
        alpine_prefix = alpine_stable_prefix(source_branch)
    else:
        alpine = False
        alpine_prefix = None

    if options.target is not None:
        target_branch = options.target
    else:
        if alpine_prefix is not None:
            target_branch = alpine_prefix + '-stable'
        else:
            target_branch = "master"

    # git pull --rebase the source branch on top of the target branch
    if options.dry_run is False:
        repo.git.pull(
                      "--quiet",
                      options.upstream,
                      "--rebase",
                      target_branch
                      )

    str = options.upstream + '/' + target_branch
    str = str + '..' + source_branch
    commits = list(repo.iter_commits(str))
    commit_count = len(commits)
    commit_titles = []
    for c in commits:
        commit_titles.append(c.message.partition('\n')[0])

    labels = []

    if options.labels is not None:
        for l in options.labels.split(','):
            labels.append(l)

    # Automatically add nice labels to help Alpine Linux
    # reviewers and developers sort out what is important
    if alpine is True:
        for s in commit_titles:
            if ": new aport" in s:
                labels.append("A-add")
                continue
            if ": move from " in s:
                labels.append("A-move")
                continue
            if ": upgrade to " in s:
                labels.append("A-upgrade")
                continue
            if ": security upgrade to " in s:
                labels.append("T-Security")
                continue
        if alpine_prefix is not None:
            labels.append("A-backport")
            labels.append('v' + alpine_prefix)

    if commit_count < 2:
        commit = repo.head.commit
    else:
        try:
            import inquirer
        except ImportError:
            commit = repo.head.commit
        else:
            # TODO: make it so we can select an actual commit
            # object, but show the titles to the user
            # this currently allows the user to pick a title
            # but it will fail to provide a description
            questions = [
                inquirer.List('commit',
                              message="Please pick a commit",
                              choices=commit_titles,
                              carousel=True
                              ),
            ]
            answers = inquirer.prompt(questions)

            # Remove this once the TODO above is fixed
            commit = repo.head.commit

    message = commit.message.partition('\n')

    if options.title is not None:
        title = options.title
    else:
        title = message[0]

    if alpine_prefix is not None:
        title = '[' + alpine_prefix + '] ' + title

    if options.description is not None:
        description = options.description
    else:
        # Don't do [1:] because git descriptions have one blank line separating
        # between the title and the description
        description = '\n'.join(message[2:])

    # git pull --rebase the source branch on top of the target branch
    if options.dry_run is False:
        repo.git.pull(
                      "--quiet",
                      options.upstream,
                      "--rebase",
                      target_branch
                      )

        # git push --quiet upstream source_branch:source_branch
        repo.git.push(
                      "--quiet",
                      options.origin,
                      (source_branch + ":" + source_branch)
                      )

    if options.dry_run is True:
        print("source_branch:", source_branch)
        print("target_branch:", target_branch)
        for l in commit_titles:
            print("commit:", l)
        print("title:", title)
        for l in description.split('\n'):
            print("description:", l)
        print("target_project_id:", upstream.projectid)
        for l in labels:
            print("labels:", l)

        # This is equivalent to git rev-list
        print("commit count:", commit_count)
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
                                             'target_project_id': upstream.projectid,
                                             'labels': labels
                                             },
                                             retry_transient_errors=True)

    print("id:", mr.attributes['id'])
    print("title:", mr.attributes['title'])
    print("state:", mr.attributes['state'])
    print("target_branch:", mr.attributes['target_branch'])
    print("source_branch:", mr.attributes['source_branch'])
    print("url:", mr.attributes['web_url'])


if __name__ == "__main__":
    main()
