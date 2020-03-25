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
	Specify a configuration file, will create one in that path if it doesn't exist

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

# CACHE

The cache directory holds various informations that is important to speed up
operation of mkmr, if they are not present then calls to the gitlab instance
are made instead which are much slower.

These are the cache directories:

. $XDG_CACHE_HOME/mkmr (if XDG_CACHE_HOME is set)
. $HOME/.cache/mkmr (if XDG_CACHE_HOME is not set)

## Project IDs

Every time one of the utilities needs to interact with a project in GitLab it
needs to know the project id assigned to that project. So instead of making an
API call every time it just stores that in a value in a file within the
following path, with the following name:

```
$domain/$user/$project/project-id
```

As an example if one contributes to alpine/aports from gitlab.alpinelinux.org
the file would be:

```
gitlab.alpinelinux.org/alpine/aports/project-id
```

The content present within the file is the project id

## branch - merge request relation

Every time that a merge request is created with mkmr, a file will be created
in the following location under the mkmr cache directory.

```
$XDG_CACHE_HOME/mkmr/$domain/$user/$project/branches/$source_branch
```

domain is the domain of the hosted GitLab instance, user and project correspond
to the user that owns the project and the name of the project, and branch is
the name of the source branch

the content within the file is the internal id (the one that appears in the
web interface) of the merge request that was made from the source branch.

This is done so programs can directly relate a branch and and a merge request
without having to resort to network calls.

# EXAMPLES

The following show examples of how to use the different options that mkmr
provides, note that almost all options can be mixed and match as you please:

## Targetting other branches

```
mkmr --source=FOO --target=BAR
```

## Use another configuration file

```
mkmr --config=/path/to/temporary/configuration
```

## Permanently switching to a new token

```
mkmr --token=NewTokenSoNice --overwrite
```

## Title and description

```
mkmr --title="This is an amazing merge request"

mkmr --title="Not Amazing Merge Request" --description="Sike!"
```

## Labels

```
mkmr --labels=help-wanted,good-first-issue
```

# ALPINE LINUX

mkmr is written by Alpine Linux developers, while it desires to work with all
GitLab instances, as  noted by avoiding to hardcode Alpine Linux stuff, mkmr
does offer special support for Alpine Linux handling of GitLab

The following is a write-up of things mkmr does to better integrate with Alpine
Linux:

We automatically add Alpine Linux specific labels like A-add, A-move,
A-upgrade, A-backport and others as appropriate.

We automatically guess the target branch in case your source branch name
matches a specific pattern, namely that it starts with a version number
that matches Alpine Linux's one. As an example, 3.11-dns as a source
branch will lead to mkmr guessing that the user wants to make the merge
request against 3.11-stable.

It will also prefix the title with a version number if one is making
merge requests against one of the branches, merge requests targetting
3.x-stable will have [3.x] prefixed to their title.
