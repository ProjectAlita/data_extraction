"""This module extracts data from GitHub."""

import logging

import pandas as pd

from ..github.github_base import GitHubBase


class GitHubGetOrgLvl(GitHubBase):  # pylint: disable=too-few-public-methods
    """
    A class used to interact with the GitHub API on the organization level and extract repositories data.

    Attributes
    ----------
    owner : str
        The owner of the repository.
    token : str
        The token used to authenticate with the GitHub API.
    base_url : str
        The base URL for the GitHub API for the specified repository.

    Methods
    -------
    extract_repos_list()
        Extracts repositories list (their ids and names) that can be accessed.
    """

    def __init__(self, owner, token):
        """
        Constructs all the necessary attributes for the GitHubGet object.
        """
        super().__init__(owner, token)
        self.base_url = self.base_url + f'/orgs/{self.owner}'

    def extract_repos_list(self) -> pd.DataFrame:
        """
        Extracts repositories list from the GitHub API. Details on the page:
        https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-organization-repositories
        """
        logging.info("Starting repos list extraction...")
        data_raw = self._load_data('repos')
        data = []
        for repo in data_raw:
            repo_data = self._extract_repos_attr(repo)
            data.append(repo_data)
        df_repos = pd.DataFrame(data)
        logging.info('Repos list extraction completed.')
        return df_repos

    @staticmethod
    def _extract_repos_attr(repository: dict) -> dict:
        """Extracts relevant attributes from a repository object."""
        return {
            'repository_id': repository.get('id'),
            'repository_name': repository.get('name'),
            'description': repository.get('description'),
            'http_url_to_repo': repository.get('html_url'),
            'web_url': repository.get('homepage'),
            'default_branch': repository.get('default_branch'),
            'pushed_at': repository.get('pushed_at'),
        }
