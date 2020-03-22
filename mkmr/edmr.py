import sys
from optparse import OptionParser
from typing import Optional

from git import Repo
from gitlab import GitlabAuthenticationError, GitlabUpdateError

from mkmr.api import API
from mkmr.config import Config

from . import __version__


def strtobool(s) -> Optional[bool]:
    """
    Convert a string into a boolean value or None

    True is returned when yes, true or 1 is called
    False is returned when no, false or 0 is called
    None is returned on any other value, we do this because we want to know if we are passing an
    invalid value
    """
    if s.lower() in ("yes", "true", "1"):
        return True
    elif s.lower() in ("no", "false", "0"):
        return False
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
        "--quiet",
        dest="quiet",
        action="store_true",
        default=False,
        help="Don't print warnings of invalid values",
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

    if len(args) < 3:
        print("no attributes to edit given")
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

    # Store all valid values in a set we can check for validity
    valid_values = {
        "assignee_id",
        "assignee_ids",
        "description",
        "labels",
        "milestone_id",
        "remove_source_branch",
        "state_event",
        "target_branch",
        "title",
        "discussion_locked",
        "squash",
        "allow_collaboration",
        "allow_maintainer_to_push",
    }
    for arg in args[2:]:
        should_skip = False

        k = arg.split("=")[0]
        if k not in valid_values:
            continue
        try:
            v = arg.split("=")[1]
        except IndexError:
            continue

        # Check if we are passing a valid type
        if (
            k == "remove_source_branch"
            or k == "squash"
            or k == "discussion_locked"
            or k == "allow_collaboration"
            or k == "allow_maintainer_to_push"
        ):
            if strtobool(v) is None:
                print(
                    "value of {} ({}), is invalid, should be True or False".format(k, v)
                ) if not options.quiet else 0
                continue
        elif k == "state_event":
            if v != "close" and v != "reopen":
                print(
                    "value of {} ({}), is invalid, should be either close or reopen".format(k, v)
                ) if not options.quiet else 0
                continue
        elif k == "assignee_id" or k == "milestone_id":
            # "" and 0 are the same thing for the GitLab API, it justs allows us to try a conversion
            # to int
            if v == "":
                v = 0
            try:
                v = int(v)
            except ValueError:
                print(
                    "value of {} ({}), is invalid, should be an integer".format(k, v)
                ) if not options.quiet else 0
                continue
        elif k == "title":
            if v == "":
                print("value of title should not be empty") if not options.quiet else 0
                continue
        elif k == "description":
            if len(v) > 1048576:
                print(
                    "description has more characters than limit of 1.048.576"
                ) if not options.quiet else 0
                continue
        elif k == "labels":
            v = v.split(",")
        elif k == "assignee_ids":
            # "" and 0 are the same thing for the GitLab API, it justs allows us to try a conversion
            # to int
            if v == "":
                v = 0
            v = v.split()
            for value in v:
                try:
                    value = int(value)
                except ValueError:
                    print(
                        "key {} has invalid sub-value {} in value {}".format(k, value, v)
                    ) if not options.quiet else 0
                    should_skip = True

            if should_skip is True:
                continue

        print("{} -> {}".format(k, v)) if not options.quiet else 0
        setattr(mr, k, v)

    try:
        mr.save()
    except GitlabAuthenticationError as e:
        print("Failed to update, authentication error\n\n{}".format(e))
    except GitlabUpdateError as e:
        print("Failed to update, update error\n\n{}".format(e))


if __name__ == "__main__":
    main()