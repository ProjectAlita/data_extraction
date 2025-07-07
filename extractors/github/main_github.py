"""This module is an entry point for data extraction from GutHub via API."""

import logging
import os
from typing import Optional

import pandas as pd

from ..github.github_repo import GitHubGetReposLvl
from ..github.github_org import GitHubGetOrgLvl
from ..utils.constants import OUTPUT_FOLDER, OUTPUT_COMMITS_PATH, OUTPUT_PULL_REQUESTS_PATH
from ..utils.read_config import GitHubConfig
from ..utils.outliers import get_outliers_upper_bound
from ..utils.check_input import check_if_open, check_input_date
from ..utils.timer import timer
from ..utils.convert_to_datetime import string_to_datetime
from ..github.github_transform import calculate_pull_req_statistic, add_pull_req_statistic_to_repos

CONFIG_PATH = './config.yml'
OWNER, TOKEN = None, None
if os.path.exists(CONFIG_PATH):
    GITHUB_CREDS = GitHubConfig(CONFIG_PATH)
    OWNER, TOKEN = GITHUB_CREDS.owner, GITHUB_CREDS.token


@timer
def extract_commits_from_multiple_repos(repos: str, since_date: str, git: Optional[GitHubGetOrgLvl] = None,  to_save=False) -> pd.DataFrame | None:
    """
    Extracts commit data from multiple GitHub repositories since the specified date. Saves the result to a CSV
     file. Checks if the file with the same name is not open.

    Parameters
    ----------
    repos : str
        The string containing repositories names to extract data from, separated by commas.
    since_date : str
        The date to start extracting commits from, in ISO 8601 format.
    """
    repos_list = [item.strip() for item in repos.split(',')]
    df_commits = pd.DataFrame()
    for repo in repos_list:
        if git is not None:
            git_repo = GitHubGetReposLvl(git.owner, git.token, repo)
        else:
            git_repo = GitHubGetReposLvl(OWNER, TOKEN, repo)
        result = git_repo.extract_commit_data(since_date)
        df_commits = pd.concat([df_commits, result], axis=0)

    if df_commits.empty:
        logging.info('There are no commits for the selected period!')
        return
    
    df_commits['upperBound'] = get_outliers_upper_bound(df_commits['commit_size'])
    if to_save:
        outputfile = f'{OUTPUT_COMMITS_PATH}{repos}.csv'
        check_if_open(outputfile)
        df_commits.to_csv(outputfile, index=False)
        logging.info('Data has been downloaded to the folder %s', OUTPUT_FOLDER)

    return df_commits


@timer
def extract_pull_requests_from_multiple_repos(repos: str, since_date: str, git: Optional[GitHubGetOrgLvl] = None) -> pd.DataFrame:
    """
    Extracts pull request data from multiple GitHub repositories since the specified date.

    Parameters
    ----------
    repos : str
        The string containing repositories names to extract data from, separated by commas.
    since_date : str
        The date to start extracting pull requests from, in ISO 8601 format.
    """
    df_pull_requests = pd.DataFrame()
    repos_list = [item.strip() for item in repos.split(',')]

    for repo in repos_list:
        if git is not None:
            git_repos = GitHubGetReposLvl(git.owner, git.token, repo)
        else:
            git_repos = GitHubGetReposLvl(OWNER, TOKEN, repo)

        result = git_repos.extract_pull_requests_data(since_date)
        df_pull_requests = pd.concat([df_pull_requests, result], axis=0)

    if df_pull_requests.empty:
        logging.info("There are no pull requests for the selected period!")
        return df_pull_requests

    # Add empty columns that are in the GitLab data
    df_pull_requests[['first_commit_date', 'last_commit_date']] = None

    logging.info('Pull requests data has been extracted.')
    return df_pull_requests


def extract_pull_requests_from_multiple_repos_and_save_to_csv(repos: str, since_date: str) -> None:
    """
    Extracts pull request data from multiple GitHub repositories since the specified date.
    Checks if the file with the same name as output is not open. Saves the result to a CSV.
    """
    output_file = f'{OUTPUT_PULL_REQUESTS_PATH}{repos}.csv'
    check_if_open(output_file)
    extract_pull_requests_from_multiple_repos(repos, since_date).to_csv(output_file, index=False)
    logging.info('Pull requests data has been downloaded to the folder %s', OUTPUT_FOLDER)


@timer
def extract_repositories_list(pushed_after, git: Optional[GitHubGetOrgLvl] = None) -> pd.DataFrame:
    """
    Extracts repositories list from the GitHub API (id, name). Saves the result to a CSV file.
    """
    check_input_date(pushed_after)
    if git is None:
        git = GitHubGetOrgLvl(OWNER, TOKEN)
    result = git.extract_repos_list()
    if result.empty:
        return pd.DataFrame()

    result['pushed_at'] = result.apply(lambda x: string_to_datetime(x['pushed_at']), axis=1)
    result = result[result['pushed_at'] >= string_to_datetime(pushed_after)]
    logging.info('Repositories data has been extracted.')

    return result


def extract_repositories_list_and_save_to_csv(pushed_after) -> None:
    """
    Extracts repositories list from the GitHub API (id, name). Saves the result to a CSV file.
    Checks if the file with the same name is not open.
    """
    output_file = f'{OUTPUT_FOLDER}github_repos_list.csv'
    check_if_open(output_file)
    result = extract_repositories_list(pushed_after)
    result.to_csv(output_file, index=False)
    logging.info('You have access to %s repositories. Data has been downloaded to '
                 'the folder %s', len(result), OUTPUT_FOLDER)


@timer
def extract_repositories_extended_data(pushed_after, git: Optional[GitHubGetOrgLvl] = None, to_save=False) -> pd.DataFrame:
    """
    Extracts repositories list from the GitHub API (id, name). Saves the result to a CSV file.
    Checks if the file with the same name is not open.
    """
    check_input_date(pushed_after)
   
    result = extract_repositories_list(pushed_after, git=git)
    if result.empty:
        logging.info('There are no repositories for the selected period!')
        return result

    repos_names = result['repository_name'].tolist()

    branches_all_repos = []
    for repo in repos_names:
        if git is not None:
            git_repo = GitHubGetReposLvl(git.owner, git.token, repo)
        else:
            git_repo = GitHubGetReposLvl(OWNER, TOKEN, repo)
        branches = git_repo.extract_branches_data()
        if branches.empty:
            continue
        branches_count_status = branches['branch_status'].value_counts()
        branches_count_status['repository_name'] = repo
        branches_all_repos += [branches_count_status]
    branches_all_repos = pd.DataFrame(branches_all_repos)
    if not branches_all_repos.empty:
        result = result.merge(branches_all_repos, on='repository_name', how='left')

    pull_req = extract_pull_requests_from_multiple_repos(','.join(repos_names), pushed_after, git=git)
    pull_req_stats = calculate_pull_req_statistic(pull_req)
    result = add_pull_req_statistic_to_repos(result, pull_req_stats)

    if to_save:
        output_file = f'{OUTPUT_FOLDER}github_repos_extended_info.csv'
        check_if_open(output_file)
        result.to_csv(output_file, index=False)
        logging.info('Extended information on the repositories you have access to has been downloaded to '
                 'the folder %s', OUTPUT_FOLDER)

    return result
