import sys
from optparse import OptionParser

from git import Repo
from gitlab import GitlabAuthenticationError, GitlabUpdateError

from mkmr.api import API
from mkmr.config import Config
from mkmr.utils import find_cache, init_repo, strtobool

from . import __version__

# Store all valid values in a set we can check for validity
# we also print them after some processing for the user so
# they know what attributes of a merge request they can modify
# and what kind of input (boolean, string, integer, etc...) each
# attribute takes
VALID_VALUES = {
    "assignee_id",
    "assignee_ids",
    ":description",
    "description",
    "description:",
    ":labels",
    "labels",
    "labels:",
    "milestone_id",
    "remove_source_branch",
    "state_event",
    "target_branch",
    ":title",
    "title",
    "title:",
    "discussion_locked",
    "squash",
    "allow_collaboration",
    "allow_maintainer_to_push",
}


def print_values():
    for val in iter(VALID_VALUES):
        if (
            val == "remove_source_branch"
            or val == "squash"
            or val == "discussion_locked"
            or val == "allow_collaboration"
            or val == "allow_maintainer_to_push"
        ):
            print("{} -> boolean".format(val))
        elif val == "assignee_id":
            print("{} -> integer".format(val))
        elif val == "assignee_ids":
            print("{} -> multiple integers separated by whitespace".format(val))
        elif val == "labels" or val == ":labels" or val == "labels:":
            print("{} -> one or more strings separated by whitespace".format(val))
        else:
            print("{} -> a single string".format(val))


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
        "-l",
        "--list",
        dest="list",
        action="store_true",
        default=False,
        help="Show list of attributes that can be modified",
    )

    (options, args) = parser.parse_args(sys.argv)

    if options.list is True:
        print_values()
        sys.exit(0)

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

    for arg in args[2:]:
        should_skip = False

        k = arg.split("=")[0]
        if k not in VALID_VALUES:
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
            if v == mr.attributes["title"]:
                print("value of title hasn't changed") if not options.quiet else 0
                continue
            if v == "":
                print("value of title should not be empty") if not options.quiet else 0
                continue
        elif k == ":title" or k == "title:":
            if v == "":
                print("value of title should not be empty") if not options.quiet else 0
                continue
            if k == ":title":
                v = v + " " + mr.attributes["title"]
            elif k == "title:":
                v = mr.attributes["title"] + " " + v
            k = "title"
        elif k == "description":
            if len(v) > 1048576:
                print(
                    "description has more characters than limit of 1048576"
                ) if not options.quiet else 0
                continue
        elif k == ":description" or k == "description:":
            if len(v) + len(mr.attributes["description"]) > 1048576:
                print(
                    "description has more characters than limit of 1048576"
                ) if not options.quiet else 0
                continue
            if k == ":description":
                v = v + " " + mr.attributes["description"]
            elif k == "description:":
                v = mr.attributes["description"] + " " + v
            k = "description"
        elif k == "labels":
            v = v.split()
        elif k == ":labels" or k == "labels:":
            o = mr.attributes["labels"]
            for val in v.split():
                o.append(val)
            k = "labels"
            v = o
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
