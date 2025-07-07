"""This module extracts data from GitHub."""

import logging

from typing import Optional
from datetime import datetime

import pandas as pd
import requests

from ..github.github_base import GitHubBase
from ..utils.convert_to_datetime import string_to_datetime
from ..utils.check_input import check_input_date


class GitHubGetReposLvl(GitHubBase):
    """
    A class used to interact with the GitHub API and extract data inside repositories (commits, pull requests etc.).

    Attributes
    ----------
    owner : str
        The owner of the repository.
    repo : str
        The name of the repository.
    token : str
        The token used to authenticate with the GitHub API.
    base_url : str
        The base URL for the GitHub API for the specified repository.

    Methods
    -------
    extract_commit_data(since_date)
        Extracts commit data from the GitHub API since the specified date.
    extract_pull_requests_data(since_date)
        Extracts pull requests data (open and closed) from the GitHub API since the specified date.
    """

    def __init__(self, owner, token, repo):
        """
        Constructs all the necessary attributes for the GitHubGet object.
        """
        if not owner or not token or not repo:
            raise ValueError("Owner, token and repo must all be provided")
        
        super().__init__(owner, token)
        self.repo = repo
        self.base_url = f'https://api.github.com/repos/{self.owner}/{self.repo}'

        # Validate credentials
        try:
            test_response = requests.get(
                self.base_url,
                headers={'Authorization': f'Bearer {self.token}'},
                timeout=30
            )
            test_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to authenticate: {str(e)}")
            raise ValueError("Invalid credentials or repository access") from e

    def extract_commit_data(self, since_date: str) -> pd.DataFrame:
        """
        Extracts commit data from the GitHub API since the specified date.
        More details on the page: https://docs.github.com/en/rest/commits/commits?apiVersion=2022-11-28
        """
        check_input_date(since_date)
        logging.info("Starting commits data extraction...")
        data_raw = self._load_data('commits', params={'since': since_date})
        data = []
        for commit in data_raw:
            commit_data = self._extract_commit_attr(commit)
            commit_data['commit_size'] = self._get_commit_size(commit_data['id'])
            data.append(commit_data)
        df_commits = pd.DataFrame(data)
        logging.info('Commits data extraction completed.')
        return df_commits

    def extract_pull_requests_data(self, since_date: str) -> pd.DataFrame:
        """
        Extracts pull requests data (open and closed) from the GitHub API since the specified date.
        More details on the page: https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests
        """
        check_input_date(since_date)
        # logging.info('Starting pull requests data extraction for the repository "%s"...', self.repo)
        data_raw = self._load_data('pulls', params={'state': 'all'})

        if not data_raw:
            logging.info('No pull requests found for the repository %s.', self.repo)
            return pd.DataFrame()

        data = [
            self._extract_pull_request_attr(pull)
            for pull in data_raw
            if pull is not None
        ]
        if len(data) == 0:
            return pd.DataFrame()
        df_pull_requests = pd.DataFrame(data)
        df_pull_requests['created_at_datetime'] = df_pull_requests.apply(
            lambda x: string_to_datetime(x['created_at'][:10]), axis=1)
        df_pull_requests = df_pull_requests[df_pull_requests['created_at_datetime'] >= string_to_datetime(since_date)]
        df_pull_requests = df_pull_requests.drop(columns=['created_at_datetime'])
        logging.info('Pull requests data extraction for the repository %s completed.', self.repo)
        return df_pull_requests

    def extract_branches_data(self) -> pd.DataFrame:
        """
        Extracts branches data from the GitHub API.
        More details on the page: https://docs.github.com/en/rest/branches/branches?apiVersion=2022-11-28#list-branches
        """
        # logging.info("Starting branches data extraction...")
        data_raw = self._load_data('branches')
        # Return empty DataFrame if no data
        if not data_raw:
            logging.info('No branches found.')
            return pd.DataFrame()
        df_branches = pd.DataFrame(data_raw)
        branches_details = []
        for branch in df_branches['name'].tolist():
            branch_data = self.extract_one_branch_data(branch)
            branches_details += [branch_data]
        df_branches = df_branches.merge(pd.DataFrame(branches_details), on='name', how='left')
        if df_branches.empty:
            return df_branches
        df_branches['last_commit_date'] = df_branches['commit_y'].apply(
            lambda x: x.get('commit', {}).get('committer', {}).get('date'))
        df_branches['branch_status'] = df_branches['last_commit_date'].apply(self._define_active_or_stale_branch)
        # logging.info('Branches data extraction completed.')
        return df_branches

    def extract_one_branch_data(self, branch_name: str) -> dict:
        """
        Extracts one branch data from the GitHub API.
        More details on the page: https://docs.github.com/en/rest/branches/branches?apiVersion=2022-11-28#get-a-branch
        """
        # logging.info('Starting %s branch data extraction...', branch_name)
        data = self._load_data(f'branches/{branch_name}')
        # logging.info('%s branch data extraction completed.', branch_name)
        return data

    @staticmethod
    def _extract_pull_request_attr(pull_req: dict) -> dict:
        """
        Extracts relevant attributes from a pull request object.
        
        Args:
            pull_req: Dictionary containing pull request data
            
        Returns:
            dict: Extracted pull request attributes with safe fallbacks
        """
        if not pull_req:
            logging.warning("Received empty pull request data")
            return {
                "project_id": None,
                "created_at": None,
                "merged_at": None,
                "closed_at": None,
                "merge_commit_sha": None,
                "source_branch": None
            }

        head = pull_req.get("head") or {}
        repo = head.get("repo") or {}

        return {
            "project_id": repo.get("id"),
            "created_at": pull_req.get("created_at"),
            "merged_at": pull_req.get("merged_at"),
            "closed_at": pull_req.get("closed_at"),
            "merge_commit_sha": pull_req.get("merge_commit_sha"),
            "source_branch": head.get("ref")
        }

    def _extract_commit_attr(self, commit: dict) -> dict:
        """Extracts relevant attributes from a commit object."""
        commit_info = commit.get("commit", {})
        return {
            "repos_name": self.repo,
            "id": commit.get("sha"),
            "authored_date": commit_info.get("author", {}).get("date"),
            "committed_date": commit_info.get("committer", {}).get("date"),
            "created_at": commit_info.get("author", {}).get("date"),
            "message": commit_info.get("message").encode('utf8'),
        }

    def _get_commit_size(self, commit_sha: str) -> Optional[int]:
        """Fetches the size of a commit from the GitHub API."""
        data = self._load_data(f'commits/{commit_sha}')
        return data.get('stats', {}).get('total')

    @staticmethod
    def _extract_branch_attr(branch: dict) -> dict:
        """Extracts relevant attributes from a pull request object."""
        return {
            "name": branch.get("name", {}),
            "last_commit_date": branch.get("commit", {}).get("date", {}),
        }

    @staticmethod
    def _define_active_or_stale_branch(commit_date: str):
        """Defines if a branch is active or stale."""
        commit_date = datetime.strptime(commit_date, '%Y-%m-%dT%H:%M:%SZ')
        if (datetime.utcnow() - commit_date).days <= 30:
            return 'active'
        return 'stale'
