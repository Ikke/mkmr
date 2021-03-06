# mkmr

Small python3 utility to create Merge Requests on GitLab, with special support for Alpine Linux's self-hosted instance.

## Installation

Unless you need the absolutely newest version immediately please use a system package.

This package is available in the testing repo of Alpine Linux

```
apk add mkmr
```

## Set-up

The following are required to be set up in the repository you're working on:

1. A remote called `origin` (or use `--origin=ORIGIN`), the URL **must** point to your fork of the project you want to contribute to.
2. A remote called `upstream` (or use `--upstream=UPSTREAM`), the URL **must** point to the canonical repository of the project you want to contribute to.

Example:
<code>git remote -v</code>
<pre>
origin	https://gitlab.alpinelinux.org/Leo/aports.git (fetch)
origin	git@gitlab.alpinelinux.org:Leo/aports.git (push)
upstream	https://gitlab.alpinelinux.org/alpine/aports.git (fetch)
upstream	git@gitlab.alpinelinux.org:alpine/aports.git (push)
</pre>

Note that the fetch URL will be used for all interactions, and in fact only https:// are supported, with other ssh URL types like ssh:// and git:// being silently converted to https://.

3. (first-time users) call the script with `--token=TOKEN`, it will be written automatically to the configuration and won't be necessary in any further usage.

## Simple usage and common examples

After doing set-up one can run mkmr easily with:

<code>mkmr</code>

It will automatically create a merge request from the active branch to the master branch.

### Different source and target branches

Sometimes you want to create a merge request that targets another branch, sometimes you want another branch to be the source of changes in the merge request, sometimes you want both.

For those use `--source=SOURCE` and `--target=TARGET` switches like so:

<code>mkmr --target=dev</code>  
<code>mkmr --source=foo</code>  
<code>mkmr --source=foo --target=bar</code>  

### Dealing with titles, descriptions and labels

mkmr will automatically derive the title and description from the commit of the merge request, if there are multiple commits then you will be prompted with a list to pick one.

If you are using Alpine Linux's GitLab instance then it will also derive relevant labels for your merge request.

If you wish to pass your own title and description then use `--title=TITLE` and `--description=DESCRIPTION` like so:

<code>mkmr --title="This is an amazing merge request"</code>  
<code>mkmr --title="Not amazing merge request" --description="sike!"</code>  

The `--edit` or `-e` switch, when used, will open the title and description in your text editor (as decided by $VISUAL, then $EDITOR, then vim, emacs, nano).

If you want to add labels to your merge request then use `--labels=LABELS`, the labels should be separated by a comma, like so:

<code>mkmr --labels=help-wanted,good-first-issue</code>

### Switching to a new personal access token

Eventually you want to rotate your personal access tokens, in that case you can
combine the `--token=TOKEN` and `--overwrite` options. Usage of the latter means
the configuration file will have its `private_token` overwritten.

<code>cat $XDG_CONFIG_HOME/mkmr/config</code>  
```ini
[gitlab.alpinelinux.org]
url = https://gitlab.alpinelinux.org
private_token = BAR
```

<code>mkmr --token=FOO --overwrite</code>  

<code>cat $XDG_CONFIG_HOME/mkmr/config</code>  
```ini
[gitlab.alpinelinux.org]
url = https://gitlab.alpinelinux.org
private_token = FOO
```

## Configuration

mkmr uses INI-formatted files in the same way as python-gitlab, in fact mkmr will just write a section (like `[gitlab.alpinelinux.org]`) and in it, will write the `private_token` and `url` keys with the relevant values.

After writing it, the configuration file will be passed to python-gitlab, which is used for interacting with the GitLab API.

The following locations are searched (if none of them exists them the first one will be created automatically):

- $XDG_CONFIG_HOME/mkmr/config (only if XDG_CONFIG_HOME is set)
- $HOME/.config/mkmr/config (if XDG_CONFIG_HOME is not set but HOME is)

The --config switch can be used to pass a full path to a configuration file like so:

<code>mkmr --config=/tmp/config</code>
