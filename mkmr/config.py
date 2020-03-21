from configparser import SafeConfigParser
from typing import Optional

import inquirer
from gitlab import Gitlab

from mkmr.utils import find_config


class Config:
    options: dict
    config: Optional[str]
    section: str

    def __init__(self, options, gitlab_host):
        self.options = options
        self.config = find_config(self.options.config)
        # Get the host from upstream and remove the https://
        # the case for alpine linux, https://gitlab.alpinelinux.org
        # will be reduced to gitlab.alpinelinux.org
        #
        # Do note that it does not matter if we the origin or upstream
        # remote is used here since gitlab is not federated, so both will
        # call the same server
        self.section = gitlab_host.replace("https://", "")

        """
            Write the configuration passed to us via the CLI to the config
            file if it's not there already or the user wants to overwrite it
        """
        parser = SafeConfigParser()
        parser.read(self.config)

        if parser.has_section(self.section) is False:
            parser.add_section(self.section)
            with open(self.config, "w") as c:
                parser.write(c)

        # In case the 'url' options is not set in the section we are looking for
        # then just write it out.
        if parser.has_option(self.section, "url") is False:
            parser[self.section]["url"] = "https://" + self.section
            with open(self.config, "w") as c:
                parser.write(c)

        if parser.has_option(self.section, "private_token") is False or (
            self.options.overwrite is True
        ):
            # If --token is not passed to us then drop out with a long useful
            # message, if it is passed to us write it out in the configuration
            # file
            if self.options.token is None:
                token_answer = dict()
                token_answer["token"] = ""
                print(
                    "Please visit https://"
                    + self.section
                    + "/profile/personal_access_tokens to generate your token"
                )
                while token_answer is not None and token_answer["token"] == "":
                    questions = [inquirer.Text("token", message="personal access token")]
                    token_answer = inquirer.prompt(questions)
                if token_answer is None:
                    raise ValueError("personal access token not provided")
                else:
                    parser[self.section]["private_token"] = token_answer["token"]
                    with open(self.config, "w") as c:
                        parser.write(c)
            else:
                parser[self.section]["private_token"] = self.options.token
                with open(self.config, "w") as c:
                    parser.write(c)

    def get_gitlab(self) -> Gitlab:
        """
            Get the Gitlab object that is generated from this configuration file
        """
        gl = Gitlab.from_config(self.section, [self.config])
        # If the user passed --token to us then override the token acquired
        # from private_token
        if self.options.token is not None:
            gl.private_token = self.options.token

        # If the user passed --timeout to us then override the token acquired
        # from timeout or the default value
        if hasattr(self.options, "timeout") and self.options.timeout is not None:
            gl.timeout = self.options.timeout
        return gl
