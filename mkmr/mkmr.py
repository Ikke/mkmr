from optparse import OptionParser
from mkmr.api import API
from mkmr.utils import find_config
from git import Repo
from configparser import SafeConfigParser
import inquirer
import editor
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
    parser = OptionParser(version="0.0.4")
    parser.add_option("--token",
                      dest="token",
                      action="store",
                      type="string",
                      help="GitLab Personal Access Token, if there is no "
                      "private_token in your configuration file, this one "
                      "will be writen there, if there isn't one it will "
                      "merely override it")
    parser.add_option("-c",
                      "--config",
                      dest="config",
                      action="store",
                      type="string",
                      default=None,
                      help="Full path to configuration file")
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
    parser.add_option("-e",
                      "--edit",
                      dest="edit",
                      action="store_true",
                      default=False,
                      help="Edit title and description in $VISUAL or $EDITOR")
    parser.add_option("--description",
                      dest="description",
                      action="store",
                      type="string",
                      help="Description of the merge request")
    parser.add_option("--labels",
                      dest="labels",
                      action="store",
                      type="string",
                      help="comma separated list of labels for the merge "
                           "request")
    parser.add_option("-y",
                      "--yes",
                      dest="yes",
                      action="store_true",
                      default=False,
                      help="Don't prompt for user confirmation before making "
                           "merge request")
    parser.add_option("--timeout",
                      dest="timeout",
                      action="store",
                      default=None,
                      type="int",
                      help="Set timeout for making calls to the gitlab API")
    parser.add_option("-n",
                      "--dry-run",
                      dest="dry_run",
                      action="store_true",
                      default=False,
                      help="don't make the merge request, just show how it "
                           "would look like. Note that using this disables "
                           "rebasing on top of the target branch, so some "
                           "results, like how many commits there are between "
                           "your branch and upstream, may be innacurate")

    (options, args) = parser.parse_args(sys.argv)

    # Initialize our repo object based on the local repo we have
    repo = Repo()

    # Call the API using our local repo and have one for remote
    # origin and remote upstream
    origin = API(repo, options.origin)
    upstream = API(repo, options.upstream)

    # Get the host from upstream and remove the https://
    # the case for alpine linux, https://gitlab.alpinelinux.org
    # will be reduced to gitlab.alpinelinux.org
    #
    # Do note that it does not matter if we use upstream.host
    # or origin.host since gitlab is not federated, so both will
    # call the same server
    section = upstream.host.replace("https://", "")

    # Try to find the config, it checks XDG_CONFIG_HOME/mkmr/config
    # then HOME/.mkmr, and will quit otherwise
    config = find_config(options.config)

    parser = SafeConfigParser()
    parser.read(config)

    if parser.has_section(section) is False:
        parser.add_section(section)
        with open(config, 'w') as c:
            parser.write(c)

    # In case the 'url' options is not set in the section we are looking for
    # then just write it out.
    if parser.has_option(section, "url") is False:
        parser[section]['url'] = upstream.host
        with open(config, 'w') as c:
            parser.write(c)

    if parser.has_option(section, "private_token") is False:
        # If --token is not passed to us then drop out with a long useful
        # message, if it is passed to us write it out in the configuration
        # file
        if options.token is None:
            s = (
                "Option private_token inside section " + section + " has not "
                "been found. Please fill with with your personal access "
                "token.\n If you don't have an personal access token, go to: "
                "https://<GITLAB_HOST>/profile/personal_access_tokens\n"
                "And make one for yourself, this is ABSOLUTELY required"
                )
            print(s)
            sys.exit(1)
        else:
            parser[section]['private_token'] = options.token
            with open(config, 'w') as c:
                parser.write(c)

    gl = gitlab.Gitlab.from_config(section, [config])

    # If the user passed --token to us then override the token acquired
    # from private_token
    if options.token is not None:
        gl.private_token = options.token

    # If the user passed --timeout to us then override the token acquired
    # from timeout or the default value
    if options.timeout is not None:
        gl.timeout = options.timeout

    if options.source is not None:
        source_branch = options.source
    else:
        source_branch = repo.active_branch.name

    # Enable alpine-specific features
    if "gitlab.alpinelinux.org" in gl.url:
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
    commit_titles = dict()
    for c in commits:
        cstr = c.message.partition('\n')
        commit_titles.update([(cstr[0], c)])

    labels = []

    if options.labels is not None:
        for l in options.labels.split(','):
            labels.append(l)

    # Automatically add nice labels to help Alpine Linux
    # reviewers and developers sort out what is important
    if alpine is True:
        for s in commit_titles:
            if ": new aport" in s and "A-add" not in labels:
                labels.append("A-add")
                continue
            if ": move from " in s and "A-move" not in labels:
                labels.append("A-move")
                continue
            if ": upgrade to " in s and "A-upgrade" not in labels:
                labels.append("A-upgrade")
                continue
            if ": security upgrade to " in s and "T-security" not in labels:
                labels.append("T-Security")
                continue
        if alpine_prefix is not None:
            labels.append("A-backport")
            labels.append('v' + alpine_prefix)

    if commit_count < 2:
        commit = repo.head.commit
    else:
        questions = [
            inquirer.List('commit',
                          message="Please pick a commit",
                          choices=commit_titles,
                          carousel=True
                          ),
        ]
        answers = inquirer.prompt(questions)
        commit = commit_titles[answers['commit']]

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

    if options.edit is True:
        title = editor.edit(contents=title).decode('utf-8')
        description = editor.edit(contents=description).decode('utf-8')

    if options.yes is False or options.dry_run is True:
        print("GitLab Instance:", gl.url)
        print("Source Project:", (origin.user + '/' + origin.project))
        print("Target Project:", (upstream.user + '/' + upstream.project))
        print("Source Branch:", source_branch)
        print("Target Branch:", target_branch, '\n')

        print("title:", title)
        for l in description.splitlines():
            print("description:", l)
        for l in commit_titles:
            print("commit:", l)
        for l in labels:
            print("label:", l)

        # This is equivalent to git rev-list
        print("commit count:", commit_count)

    if options.dry_run is True:
        sys.exit(0)

    if options.yes is True:
        choice = True
    else:
        choice = inquirer.confirm("Create Merge Request with the values "
                                  "shown above?", default=True)

    if choice is False:
        sys.exit(0)

    origin_project = gl.projects.get(origin.projectid(token=gl.private_token),
                                     retry_transient_errors=True)

    upj = upstream.projectid(token=gl.private_token)

    mr = origin_project.mergerequests.create({
                                             'source_branch': source_branch,
                                             'target_branch': target_branch,
                                             'title': title,
                                             'description': description,
                                             'target_project_id': upj,
                                             'labels': labels
                                             },
                                             retry_transient_errors=True)

    print("id:", mr.attributes['iid'])
    print("title:", mr.attributes['title'])
    print("state:", mr.attributes['state'])
    print("url:", mr.attributes['web_url'])


if __name__ == "__main__":
    main()
