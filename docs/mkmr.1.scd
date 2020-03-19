mkmr(1)

# NAME

mkmr - Make merge requests to a GitLab instance

# SYNOPSIS

*mkmr* [options]

# OPTIONS

*--version*
	Show version number and quit

*-h, --help*
	Show help message and quit

*--token* <TOKEN>
	Specify a GitLab personal access token

*-c, --config* <CONFIG>
	Specify a configuration file

*--target* <TARGET>
	Specify a branch where the changes will be merged into, defaults to master

*--source* <SOURCE>
	Specify a branch where the changes will come from, defaults to active branch

*--origin* <ORIGIN>
	Specify a git remote from where the merge request will come from defaults to origin

*--upstream* <UPSTREAM>
	Specify a git remote from where the merge request will target, defaults to upstream

*--title* <TITLE>
	Specify a title for the merge request, defaults to title of head commit

*-e, --edit*
	Open the title and description of the merge request in an editor

*--description* <DESCRIPTION>
	Specify a description for the merge request, defaults to body of head commit

*--labels* <LABELS>
	Specify a comma-delimited list of labels for the merge request

*-y, --yes*
	Don't prompt for confirmation

*--timeout* <TIMEOUT>
	Specify, in seconds, how long to wait for completion of API requests, defaults to 4

*-n, --dry-run*
	Don't create the merge request, just show how it would look like

*--overwrite*
	If *--token* is used, rewrite configuration file to use the it

# DESCRIPTION

mkmr is a python3 script that allows a user to create merge requests to any
GitLab instance.

it makes uses of an ini-format configuration file to store the url of the
instance and the personal access token used to interact with the GitLab API of
the hosted instance. And it uses information stored in the git repository in
the form of remotes to guess which GitLab instance it should interact with.

# CONFIGURATION

mkmr will aggresively try to create a configuration file in the following path
under certain conditions:

. $XDG_CONFIG_HOME/mkmr/config (if XDG_CONFIG_HOME is set)
. $HOME/.config/mkmr/config (if XDG_CONFIG_HOME is not set)

The configuration is an ini-format with the same sections, keys and values as
used by python-gitlab.

Example configuration:

```
[gitlab.alpinelinux.org]
url = https://gitlab.alpinelinux.org
private_token = 123456789abcdefg
```

# EXAMPLES

The following show examples of how to use the different options that mkmr
provides, note that almost all options can be mixed and match as you please:

## Targetting other branches

mkmr --source=FOO --target=BAR

## Use another configuration file

mkmr --config=/path/to/temporary/configuration

## Permanently switching to a new token

mkmr --token=NewTokenSoNice --overwrite

## Title and description

mkmr --title="This is an amazing merge request"

mkmr --title="Not Amazing Merge Request" --description="Sike!"

## Labels

mkmr --labels=help-wanted,good-first-issue
