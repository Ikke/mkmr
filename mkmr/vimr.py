import sys
from optparse import OptionParser
from os import system

import editor
import inquirer
from git import Repo
from gitlab import GitlabAuthenticationError, GitlabUpdateError

from mkmr.api import API
from mkmr.config import Config
from mkmr.utils import find_cache, prompt, init_repo

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
        default=False,
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
    if (repo := init_repo()) is None:
        sys.exit(1)

    remote = API(repo, options.remote)

    try:
        config = Config(options, remote.host)
    except ValueError as e:
        print(e)
        sys.exit(1)

    gl = config.get_gitlab()

    name = mrnum
    if not mrnum.isdigit():
        try:
            cachepath = find_cache()
            # This path should be, taking alpine/aports from gitlab.alpinelinux.org as example:
            # $XDG_CACHE_HOME/mkmr/gitlab.alpinelinux.org/alpine/aports/branches/$source_branch
            cachepath = (
                cachepath
                / remote.host.replace("https://", "").replace("/", ".")
                / remote.user
                / remote.project
                / "branches"
                / name
            )
            mrnum = cachepath.read_text()
        except FileNotFoundError:
            print("branch name given, {}, has no corresponding cache file".format(name))
            sys.exit(1)
        else:
            # This is executed in a try-catch if there are no exceptions raised
            if mrnum == "":
                print("cache file for {} is empty".format(name))
                cachepath.unlink()  # Delete the file as it is empty
                sys.exit(1)

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
        "quit",
    ]

    while True:
        should_skip = False
        system("clear")

        question = [
            inquirer.List(
                "attr",
                message="Pick an attribute to edit (or quit)",
                choices=valid_values,
                carousel=True,
            )
        ]
        answer = inquirer.prompt(question)

        # We reach this in case the user calls for ctrl+c, or takes the exit option
        if answer is None or answer["attr"] == "quit":
            break

        # Split by the whitespace and get the first argument which should, most of the time, be the
        # name of the object we are dealing with, stuff after the space usually concern showing nice
        # information to the user like a preview of what value will be set on a boolean attribute
        k = answer["attr"].split()[0]

        # Check if we are passing a valid type
        if k == "squash" or k == "allow_collaboration" or k == "allow_maintainer_to_push":
            setattr(mr, k, not mr.attributes[k])
            prompt("Set {} to {}".format(k, not mr.attributes[k])) if options.yes is False else 0
            continue
        elif k == "state":
            setattr(mr, "state_event", state)
            prompt("Set state to {}".format(state)) if options.yes is False else 0
            continue
        elif k == "discussion_locked":
            setattr(mr, "discussion_locked", discussion)
            prompt("Set discussion_locked to {}".format(discussion)) if options.yes is False else 0
            continue
        elif k == "remove_source_branch":
            setattr(
                mr, "force_remove_source_branch", not mr.attributes["force_remove_source_branch"]
            )
            prompt(
                "Set remove_source_branch to {}".format(
                    not mr.attributes["force_remove_source_branch"]
                )
            ) if options.yes is False else 0
            continue
        else:
            if hasattr(mr, k):
                oldval = getattr(mr, k)
                if type(oldval) == list:
                    oldval = bytes(" ".join(oldval), "utf-8")
                else:
                    oldval = bytes(str(oldval), "utf-8")
            else:
                oldval = bytes("", "utf-8")
            v = editor.edit(contents=oldval).decode("utf-8")

        oldval = oldval.decode("utf-8")

        if k == "assignee_id" or k == "milestone_id":
            # "" and 0 are the same thing for the GitLab API, it justs allows us to try a
            # conversion to int
            if v == "":
                v = 0
            try:
                v = int(v)
            except ValueError:
                prompt(
                    "value of {} ({}), is invalid, should be an integer".format(k, v)
                ) if options.yes is False else 0
                continue
        elif k == "title" or k == "target_branch":
            if v == oldval:
                prompt("value of {} did not change".format(k)) if options.yes is False else 0
                continue
            elif v == "":
                prompt("value of {} should not be empty".format(k)) if options.yes is False else 0
                continue
        elif k == "description":
            if len(v) > 1048576:
                prompt(
                    "description has more characters than limit of 1.048.576"
                ) if options.yes is False else 0
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
                    print(
                        "key {} has invalid sub-value {} in value {}".format(k, value, v)
                    ) if options.yes is False else 0
                    should_skip = True

        if should_skip is True:
            prompt() if options.yes is False else 0
            continue

        prompt(
            "Set value of {} to {}".format(k, v if k != "description" else ("\n\n" + v))
        ) if options.yes is False else 0
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
