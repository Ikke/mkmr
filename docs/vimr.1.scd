vimr(1)

# NAME

vimr - Interactively edit attributes of merge requests

# SYNOPSIS

*vimr* [options] <MRNUM...>

# OPTIONS

*--version*
	Show version number and quit

*-h, --help*
	Show help message and quit

*--token* <TOKEN>
	Specify a GitLab personal access token

*-c, --config* <CONFIG>
	Specify a configuration file, will create one in that path if it doesn't exist

*-n, --dry-run*
	Don't create the merge request, just show how it would look like

*--timeout* <TIMEOUT>
	Specify, in seconds, how long to wait for completion of API requests, defaults to 4

*--overwrite*
	If *--token* is used, rewrite configuration file to use the it

*--remote* <REMOTE>
	Which remote to operate from

*-y, --yes*
	Answer yes to all questions

# DESCRIPTION

vimr is a python3 script that allows an user to edit attributes of the merge
requests that are allowed by the gitlab v4 API.

it makes uses of an ini-format configuration file to store the url of the
instance and the personal access token used to interact with the GitLab API of
the hosted instance. And it uses information stored in the git repository in
the form of remotes to guess which GitLab instance it should interact with.

# CONFIGURATION

vimr will aggresively try to create a configuration file in the following path
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

# CACHE

vimr will read the files written in cache, as described in mkmr-cache(7), to
stablish a connection between a branch and what merge request has that branch
as its source.
