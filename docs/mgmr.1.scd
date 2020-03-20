mgmr(1)

# NAME

mgmr - Merge merge requests in a GitLab instance

# SYNOPSIS

*mgmr* [options] <MRNUM...>

# OPTIONS

*--version*
	Show version number and quit

*-h, --help*
	Show help message and quit

*--token* <TOKEN>
	Specify a GitLab personal access token

*-c, --config* <CONFIG>
	Specify a configuration file

*-n, --dry-run*
	Don't create the merge request, just show how it would look like

*--timeout* <TIMEOUT>
	Specify, in seconds, how long to wait for completion of API requests, defaults to 4

*--overwrite*
	If *--token* is used, rewrite configuration file to use the it

*--remote* <REMOTE>
	Which remote to operate from

*-q, --quiet*
	Don't print any information about what mgmr is doing, only final results
	and falta errors

*-y, --yes*
	Answer yes to all questions

# DESCRIPTION

mgmr is a python3 script that allows an user to merge merge requests in any
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

## Merging lots of merge requests

mgmr 1 2 3

## Use another configuration file

mgmr --config=/path/to/temporary/configuration

## Permanently switching to a new token

mgmr --token=NewTokenSoNice --overwrite

; TODO: write about	the loop we use to merge multiple MRs
