import sys
from json import dumps
from optparse import OptionParser
from time import sleep

from git import Repo
from gitlab import GitlabMRClosedError, GitlabMRRebaseError

from mkmr.api import API
from mkmr.config import Config

from . import __version__


def main():
    parser = OptionParser(version=__version__)
    parser.add_option(
        "--token",
        dest="token",
        action="store",
        type="string",
        help="GitLab Personal Access Token, if there is no "
        "private_token in your configuration file, this one "
        "will be writen there, if there isn't one it will "
        "merely override it",
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
        help="don't make the merge request, just show how it "
        "would look like. Note that using this disables "
        "rebasing on top of the target branch, so some "
        "results, like how many commits there are between "
        "your branch and upstream, may be innacurate",
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
        "-q",
        "--quiet",
        dest="quiet",
        action="store_true",
        default=False,
        help="Print only the json with the results or in case of an unrecoverable error",
    )

    (options, args) = parser.parse_args(sys.argv)

    if len(args) < 2:
        print("no merge requests given")
        sys.exit(1)

    if options.token is None and options.overwrite is True:
        print("--overwrite was passed, but no --token was passed along with it")
        sys.exit(1)

    quiet = options.quiet

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

    """
    Create a dictionary that is our queue of merge requests to work on, they have the following
    scheme of {'MRNUM': 'STATE'}, the state can be one of the 3:
    - pending (this means the merge request needs to be processed)
    - merged (this means the merge request was merged, the best outcome)
    - _ (any value other than the 2 above is an error and needs to be inspected by the user)

    errors can happen for many reasons, not enough permissions to merge or to rebase, rebase failed
    because of conflicts, etc.

    also create a list of the keys we have, those are the ones we will iterate over in our workloop,
    and get the length of the list so we know when we have processed all the merge requests.
    """
    queue = dict()
    n = 0
    for arg in args[1:]:
        queue[arg] = "pending"

    keys = list(queue.keys())
    keys_len = len(keys)

    if options.dry_run is True:
        print("MRs to be merged:", keys)
        sys.exit(0)

    """
    This is a loop that iterates over all members of our queue dictionary using a neddle that
    starts at 0 and will break the loop once the neddle value gets higher than the length of
    our dictionary

    This is the logic of our loop:
    1. Get the merge request
    2. Check a few attributes of the merge request
       a. if the value of the 'state' key is 'merged', then set the merge request as
          'already merged' in the dictionary, increment the neddle and restart the loop
       b. if the value of the 'state' key is 'closed', then set the merge request as 'closed' in
          the dictionary, increment the neddle and restart the loop
       c. if the key 'work_in_progress' is True, then set the merge request as 'work in progress'
          in the dictionary, increment the neddle and restart the loop
       d. if the key 'rebase_in_progress' is True, sleep for 2 seconds and restart the loop
       e. if the key 'rebase_in_progress' is False and 'merge_error' attribute is not null, then
          set the merge request in the dictionary as the value of the 'merge_error' key, increment
          the neddle and restart the loop
    2. Try merging it
       a. if merging fails with error code 406, try starting a rebase request
          i. if asking for a rebase fails with error code 403, then set the merge request as
             'Rebase failed:' with the error message, increment the neddle and restart the loop
          ii. if asking for a rebase returns 202, restart the loop
       b. if it fails with error code 401, then set the merge request as 'Merge failed:' with the
          error message, increment the neddle and restart the loop
       c. if it works, then set the merge request as 'merged', increment the neddle and restart the
          loop
    """
    while True:

        # This will be reached once we have worked on all members
        if n + 1 > keys_len:
            break

        # Set our neddle in the list
        k = keys[n]

        """
        Get the merge request, include_rebase_in_progress is required so
        we get information on whether we are rebasing
        """
        mr = project.mergerequests.get(k, include_rebase_in_progress=True)

        attrs = mr.attributes
        if attrs["state"] == "merged":
            print(k, "is already merged") if not quiet else 0
            queue[k] = "Merge: already merged"
            n += 1
            continue
        elif attrs["state"] == "closed":
            print(k, "is closed") if not quiet else 0
            queue[k] = "Merge: closed"
            n += 1
            continue
        elif attrs["work_in_progress"] is True:
            print(k, "is a work in progress, can't merge") if not quiet else 0
            queue[k] = "Merge: work in progress"
            n += 1
            continue
        elif attrs["rebase_in_progress"] is True:
            print(
                k, "is currently rebasing, polling until it is no longer rebasing"
            ) if not quiet else 0
            # This is the median value we found for it to take when rebasing on
            # gitlab.alpinelinux.org/alpine/aports which is a big repo that holds lots
            # of recipes for building software
            sleep(3)
            continue
        elif attrs["rebase_in_progress"] is False and attrs["merge_error"] is not None:
            print(k, attrs["merge_error"]) if not quiet else 0
            queue[k] = "Rebase: " + attrs["merge_error"]
            n += 1
            continue

        try:
            mr.merge()
        except GitlabMRClosedError as e:
            if e.response_code == 406:
                print(k, "cannot be merged, trying to rebase") if not quiet else 0
                try:
                    mr.rebase(skip_ci=True)
                except GitlabMRRebaseError as e:
                    if e.response_code == 403:
                        print("Rebase failed:", e.error_message) if not quiet else 0
                        queue[k] = "Rebase: " + e.error_message
                        n += 1
                        continue
                else:
                    continue
            elif e.response_code == 401:
                print("Merge failed:", e.error_message) if not quiet else 0
                queue[k] = "Merge: " + e.error_message
                n += 1
                continue
            else:
                print(e.error_message, "aborting completely")
                sys.exit(1)
        else:
            print("Merged", k) if not quiet else 0
            queue[k] = "merged"
            n += 1

    print(dumps(queue, indent=4))


if __name__ == "__main__":
    main()