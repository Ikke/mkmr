import sys
from optparse import OptionParser

import editor
import inquirer
from git import Repo
from gitlab import GitlabAuthenticationError, GitlabUpdateError

from mkmr.api import API
from mkmr.config import Config

from . import __version__


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
        "-n",
        "--dry-run",
        dest="dry_run",
        action="store_true",
        default=False,
        help="show which merge requests mgmr would try to merge",
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
        "--overwrite",
        dest="overwrite",
        action="store_true",
        default=False,
        help="if --token is passed, overwrite private_token in configuration file",
    )
    parser.add_option(
        "--remote",
        dest="remote",
        action="store",
        type="string",
        default="upstream",
        help="which remote from which to operate on",
    )
    parser.add_option(
        "-y",
        "--yes",
        dest="yes",
        action="store_true",
        default=True,
        help="Assume yes to all prompts",
    )

    (options, args) = parser.parse_args(sys.argv)

    if len(args) < 2:
        print("no merge request given")
        sys.exit(1)

    if options.token is None and options.overwrite is True:
        print("--overwrite was passed, but no --token was passed along with it")
        sys.exit(1)

    mrnum = args[1]

    # Initialize our repo object based on the local repo we have
    repo = Repo()

    remote = API(repo, options.remote)

    try:
        config = Config(options, remote.host)
    except ValueError as e:
        print(e)
        sys.exit(1)

    gl = config.get_gitlab()

    project = gl.projects.get(
        remote.projectid(token=gl.private_token), retry_transient_errors=True, lazy=True
    )
    mr = project.mergerequests.get(mrnum, include_rebase_in_progress=True)

    # If discussion isn't locked then the value returned is a None instead of a false like it is
    # normally expected
    discussion = not mr.attributes["discussion_locked"]
    if discussion is None:
        discussion = True
    else:
        discussion = False

    state = mr.attributes["state"]
    if state == "opened" or state == "merged" or state == "repoened":
        state = "close"
    else:
        state = "reopen"

    # Store all valid values in a set we can check for validity
    valid_values = [
        "assignee_id",
        "assignee_ids",
        "description",
        "labels",
        "milestone_id",
        "remove_source_branch (Set to: {})".format(not mr.attributes["force_remove_source_branch"]),
        "state (Set to: {})".format(state),
        "target_branch",
        "title",
        "discussion_locked (Set to: {})".format(discussion),
        "squash (Set to: {})".format(not mr.attributes["squash"]),
        "allow_collaboration (Set to: {})".format(not mr.attributes["allow_collaboration"]),
        "allow_maintainer_to_push (Set to: {})".format(
            not mr.attributes["allow_maintainer_to_push"]
        ),
    ]

    while True:
        question = [
            inquirer.List(
                "attr", message="Pick an attribute to edit", choices=valid_values, carousel=True
            )
        ]
        answer = inquirer.prompt(question)

        if answer is None:
            break

        k = answer["attr"].split()[0]

        # Check if we are passing a valid type
        if k == "squash" or k == "allow_collaboration" or k == "allow_maintainer_to_push":
            setattr(mr, k, not mr.attributes[k])
            continue
        elif k == "state":
            setattr(mr, "state_event", state)
            continue
        elif k == "discussion_locked":
            setattr(mr, "discussion_locked", discussion)
            continue
        elif k == "remove_source_branch":
            setattr(
                mr, "force_remove_source_branch", not mr.attributes["force_remove_source_branch"]
            )
            continue
        else:
            oldval = getattr(mr, k)
            if type(oldval) == str:
                oldval = bytes(oldval, "utf-8")
            elif type(oldval) == list:
                oldval = bytes(" ".join(oldval), "utf-8")
            else:
                oldval = bytes(oldval)
            v = editor.edit(contents=oldval)

        if k == "assignee_id" or k == "milestone_id":
            # "" and 0 are the same thing for the GitLab API, it justs allows us to try a
            # conversion to int
            if v == "":
                v = 0
            try:
                v = int(v)
            except ValueError:
                print("value of {} ({}), is invalid, should be an integer".format(k, v))
                continue
        elif k == "title":
            if v == "":
                print("value of title should not be empty")
                continue
        elif k == "description":
            if len(v) > 1048576:
                print("description has more characters than limit of 1.048.576")
                continue
        elif k == "labels":
            v = v.split()
        elif k == "assignee_ids":
            # "" and 0 are the same thing for the GitLab API, it justs allows us to try a
            # conversion to int
            if v == "":
                v = 0
            for value in v.split():
                try:
                    value = int(value)
                except ValueError:
                    print("key {} has invalid sub-value {} in value {}".format(k, value, v))
                    should_skip = True

        if should_skip is not None and should_skip is True:
            continue

        print("{}: {} -> {}".format(k, getattr(mr, k), v))
        setattr(mr, k, v)

    if options.dry_run is True:
        sys.exit(0)

    try:
        mr.save()
    except GitlabAuthenticationError as e:
        print("Failed to update, authentication error\n\n{}".format(e))
    except GitlabUpdateError as e:
        print("Failed to update, update error\n\n{}".format(e))


if __name__ == "__main__":
    main()
