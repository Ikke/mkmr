# mkmr

Small python3 utility to create Merge Requests on GitLab, with special support for Alpine Linux's self-hosted instance.

## Dependencies

The packages for Alpine Linux, please check the equivalents for your distribution:

* py3-gitpython
* py3-urllib
* py3-gitlab

The follow is optional but highly recommended, it allows mkmr to prompt the user to select which commit from which the title and description of the merge request will be derived.

* py3-inquirer

## License

mkmr is licensed under 'GPL-3.0-or-later', see COPYING
