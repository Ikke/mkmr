mkmr-cache(7)

# NAME

*mkmr-cache* - Information about caching operations

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
$CACHE_DIR/mkmr/$domain/$user/$project/branches/$source_branch
```

domain is the domain of the hosted GitLab instance, user and project correspond
to the user that owns the project and the name of the project, and branch is
the name of the source branch

The content within the file is the internal id (the one that appears in the
web interface) of the merge request that was made from the source branch.

This is done so programs can directly relate a branch and a merge request
without having to resort to network calls.
