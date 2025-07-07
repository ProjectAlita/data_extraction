#!/usr/bin/python3
# coding=utf-8

""" AdoDataExtractor Tool Operations """

from typing import Any, Dict, Optional

from ..extractors.github.github_org import GitHubGetOrgLvl
from ..extractors.github.main_github import (
   extract_commits_from_multiple_repos,
   extract_pull_requests_from_multiple_repos,
   extract_repositories_list,
   extract_repositories_extended_data,
)


from pylon.core.tools import log, web


class Method:
    """ Tool operation methods """

    @web.method()
    def get_commits_from_repos(
        self, git: GitHubGetOrgLvl, since_after: str, repos: str
    ):
        """
        Extracts commit data from multiple GitHub repositories since the specified date. Saves the result to a CSV file.

        repos : str
            The string containing repositories names to extract data from, separated by commas.
        since_date : str
            The date to start extracting commits from, in 'YYYY-MM-DD' format.
        """
        df_commits = extract_commits_from_multiple_repos(repos, since_after, git=git)

        csv_data = ""
        if df_commits is None or df_commits.empty:
            message = f"No commits found for repositories: {repos} since {since_after}"
        else:
            csv_data = df_commits.to_csv(index=False)
            message = f"GitHub commits data for {repos} extracted successfully since {since_after}"

        return csv_data, message
    
    @web.method()
    def get_pull_requests_from_repos(
        self, git: GitHubGetOrgLvl, since_after: str, repos: str
    ):
        """
        Extracts pull request data from multiple GitHub repositories since the specified date. 
        Saves the result to a CSV file.

        repos: str
            The string containing repositories names to extract data from, separated by commas.
        since_date: str
            The date to start extracting pull requests from, in 'YYYY-MM-DD' format.
        """
        df_pull_requests = extract_pull_requests_from_multiple_repos(repos, since_after, git=git)

        csv_data = ""
        if df_pull_requests is None or df_pull_requests.empty:
            message = f"No pull requests found for repositories: {repos} since {since_after}"
        else:
            csv_data = df_pull_requests.to_csv(index=False)
            message = f"GitHub pull requests data for {repos} extracted successfully since {since_after}"

        return csv_data, message

    @web.method()
    def get_repositories(self, git: GitHubGetOrgLvl, pushed_after: str):
        """
        Extracts a list of GitHub repositories that were pushed after the specified date. 
        Saves the result to a CSV file.

        pushed_after : str
            The date to filter repositories by, in 'YYYY-MM-DD' format.
        """
        df_repos = extract_repositories_list(pushed_after, git=git)

        csv_data = ""
        if df_repos is None or df_repos.empty:
            message = f"No repositories found pushed after {pushed_after}"
        else:
            csv_data = df_repos.to_csv(index=False)
            message = f"GitHub repositories list extracted successfully since {pushed_after}"

        return csv_data, message

    @web.method()
    def get_repositories_extended_data(self, git: GitHubGetOrgLvl, pushed_after: str):
        """
        Extracts extended data for GitHub repositories that were pushed after the specified date. 
        Saves the result to a CSV file.

        pushed_after : str
            The date to filter repositories by, in 'YYYY-MM-DD' format.
        """
        df_repos_extended = extract_repositories_extended_data(pushed_after, git=git)

        csv_data = ""
        if df_repos_extended is None or df_repos_extended.empty:
            message = f"No extended data found for repositories pushed after {pushed_after}"
        else:
            csv_data = df_repos_extended.to_csv(index=False)
            message = f"GitHub repositories extended data extracted successfully since {pushed_after}"

        return csv_data, message
