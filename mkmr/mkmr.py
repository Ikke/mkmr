import sys
from optparse import OptionParser
from typing import Optional

import editor
import inquirer
from git import Repo, exc

from mkmr.api import API
from mkmr.config import Config
from mkmr.utils import create_dir, find_cache, create_file

from . import __version__


def alpine_stable_prefix(str: str) -> Optional[str]:
    if str.startswith("3.8-"):
        return "3.8"
    elif str.startswith("3.9-"):
        return "3.9"
    elif str.startswith("3.10-"):
        return "3.10"
    elif str.startswith("3.11-"):
        return "3.11"
    else:
        return None


def main():
    parser = OptionParser(version=__version__)
    parser.add_option(
        "--token", dest="token", action="store", type="string", help="GitLab Personal Access Token"
    )
    parser.add_option(
        "-c",
        "--config",
        dest="config",
        action="store",
        type="string",
        default=None,
        help="Full path to configuration file",
    )
    parser.add_option(
        "--target",
        dest="target",
        action="store",
        type="string",
        help="branch to make the merge request against",
    )
    parser.add_option(
        "--source",
        dest="source",
        action="store",
        type="string",
        help="branch from which to make the merge request",
    )
    parser.add_option(
        "--origin",
        dest="origin",
        action="store",
        type="string",
        default="origin",
        help="git remote that points to your fork of the repo",
    )
    parser.add_option(
        "--upstream",
        dest="upstream",
        action="store",
        type="string",
        default="upstream",
        help="git remote that points to upstream repo",
    )
    parser.add_option(
        "--title", dest="title", action="store", type="string", help="title of the merge request",
    )
    parser.add_option(
        "-e",
        "--edit",
        dest="edit",
        action="store_true",
        default=False,
        help="Edit title and description in $VISUAL or $EDITOR",
    )
    parser.add_option(
        "--description",
        dest="description",
        action="store",
        type="string",
        help="Description of the merge request",
    )
    parser.add_option(
        "--labels",
        dest="labels",
        action="store",
        type="string",
        help="comma separated list of labels for the merge " "request",
    )
    parser.add_option(
        "-y",
        "--yes",
        dest="yes",
        action="store_true",
        default=False,
        help="Don't prompt for user confirmation before making merge request",
    )
    parser.add_option(
        "--timeout",
        dest="timeout",
        action="store",
        default=None,
        type="int",
        help="Set timeout for making calls to the gitlab API",
    )
    parser.add_option(
        "-n",
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=False,
        help="don't make the merge request, just show how it would look like",
    )
    parser.add_option(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        default=False,
        help="if --token is passed, overwrite private_token in configuration file",
    )

    (options, _) = parser.parse_args(sys.argv)

    if options.token is None and options.overwrite is True:
        print("--overwrite was passed, but no --token was passed along with it")
        sys.exit(1)

    # Initialize our repo object based on the local repo we have
    repo = Repo()

    # Call the API using our local repo and have one for remote
    # origin and remote upstream
    origin = API(repo, options.origin)
    upstream = API(repo, options.upstream)

    try:
        config = Config(options, upstream.host)
    except ValueError as e:
        print(e)
        sys.exit(1)
    except PermissionError as e:
        print("Not enough permissions to create config on '{}'".format(e.filename))
        sys.exit(1)

    gl = config.get_gitlab()

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
            target_branch = alpine_prefix + "-stable"
        else:
            target_branch = "master"

    # git pull --rebase the source branch on top of the target branch
    if options.dry_run is False:
        try:
            repo.git.pull("--quiet", options.upstream, "--rebase", target_branch)
        except exc.GitCommandError as e:
            # There are multiple reasons that GitCommandError can be raised, try to guess based on
            # the string that is given to us, it would be better if it raised GitCommandError with a
            # specific subtype that would tell us what it is but we can not rely on that
            if "You have unstaged changes" in e.stderr:
                print(
                    "Rebasing {} on top of {} failed!\n There are unstaged changes, please commit "
                    "or stash them".format(source_branch, target_branch)
                )
            if "Failed to merge in the changes" in e.stderr:
                print(
                    "Rebasing {} on top of {} failed!\n Please check the output below:\n\n"
                    "{}".format(source_branch, target_branch, e.stdout)
                )
            sys.exit(1)

    str = options.upstream + "/" + target_branch
    str = str + ".." + source_branch
    commits = list(repo.iter_commits(str))
    commit_count = len(commits)

    # Fail early if we are creating a merge request without commits in difference
    # to the target branch
    if commit_count < 1:
        print("no commits in difference between {}".format(str.replace("..", " and ")))
        sys.exit(1)

    commit_titles = dict()
    for c in commits:
        cstr = c.message.partition("\n")
        commit_titles.update([(cstr[0], c)])

    labels = []

    if options.labels is not None:
        for l in options.labels.split(","):
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
            if (": security upgrade to " or ": fix CVE-") in s and "T-security" not in labels:
                labels.append("T-Security")
                continue
        if alpine_prefix is not None:
            labels.append("A-backport")
            labels.append("v" + alpine_prefix)

    if commit_count == 1:
        commit = list(commit_titles.values())[0]
    else:
        questions = [
            inquirer.List(
                "commit", message="Please pick a commit", choices=commit_titles, carousel=True,
            ),
        ]
        answers = inquirer.prompt(questions)
        commit = commit_titles[answers["commit"]]

    message = commit.message.partition("\n")

    if options.title is not None:
        title = options.title
    else:
        title = message[0]

    if alpine_prefix is not None:
        title = "[" + alpine_prefix + "] " + title

    if options.description is not None:
        description = options.description
    else:
        # Don't do [1:] because git descriptions have one blank line separating
        # between the title and the description
        description = "\n".join(message[2:])

    if options.edit is True:
        title = editor.edit(contents=title).decode("utf-8")
        description = editor.edit(contents=description).decode("utf-8")

    if options.yes is False or options.dry_run is True:
        print("GitLab Instance:", gl.url)
        print("Source Project:", (origin.user + "/" + origin.project))
        print("Target Project:", (upstream.user + "/" + upstream.project))
        print("Source Branch:", source_branch)
        print("Target Branch:", target_branch, "\n")

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
        choice = inquirer.confirm("Create Merge Request with the values shown above?", default=True)

    if choice is False:
        sys.exit(0)

    origin_project = gl.projects.get(
        origin.projectid(token=gl.private_token), retry_transient_errors=True, lazy=True
    )

    mr = origin_project.mergerequests.create(
        {
            "source_branch": source_branch,
            "target_branch": target_branch,
            "title": title,
            "description": description,
            "target_project_id": upstream.projectid(token=gl.private_token),
            "labels": labels,
            "allow_maintainer_to_push": True,
            "remove_source_branch": True,
        },
        retry_transient_errors=True,
    )

    print("id:", mr.attributes["iid"])
    print("title:", mr.attributes["title"])
    print("state:", mr.attributes["state"])
    print("url:", mr.attributes["web_url"])

    try:
        cachepath = create_file(find_cache() / "branch" / source_branch)
        cachepath.write_text(mr.attributes["iid"])
    except ValueError:
        print("Failed to write to cache, merging via branch won't be available")
        print("Error: {}".format(sys.exc_info()[0]))


if __name__ == "__main__":
    main()
