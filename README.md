# mkmr

Small python3 utility to create Merge Requests on GitLab, with special support for Alpine Linux's self-hosted instance.

## Installation

Unless you need the absolutely newest version immediately please use a system package.

This package is available in the testing repo of Alpine Linux

```
apk add mkmr
```

## Configuration

mkmr uses INI-formatted files and re-uses the same ones from python-gitlab, in fact it only does some validation to provide useful messages to the user and then passes the configuration file directly for python-gitlab, which is used to do all the API calls required to create the merge request.

The locations searched are:

- $XDG_CONFIG_HOME/mkmr/config
- $HOME/.mkmr

The --config switch can be used to pass a full path to a configuration file like so:

```sh
$ mkmr --config=/tmp/config
```
