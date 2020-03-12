# mkmr

Small python3 utility to create Merge Requests on GitLab, with special support for Alpine Linux's self-hosted instance.

## Dependencies

The packages for Alpine Linux, please check the equivalents for your distribution:

* py3-gitpython
* py3-urllib
* py3-gitlab

The following is optional and won't affect anything at the current moment, but will in the future allow users to pick which commit they want to derive the title and description of the merge request from:

* py3-inquirer

## License

mkmr is licensed under 'GPL-3.0-or-later', see COPYING
