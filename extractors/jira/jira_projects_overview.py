"""This module connects to a Jira instance, gets the list of projects a user has access with number of issues,
  and saves the result to a CSV file."""

import logging
from typing import Optional
import pandas as pd

from jira import JIRA, JIRAError

from ..jira.jira_connect import connect_to_jira_and_print_projects

pd.set_option('display.max_rows', None)
pd.set_option('max_colwidth', 40)


def jira_projects_overview(
    after_date: str, project_keys: Optional[str] = None, credentials: Optional[dict] = None, jira: Optional[JIRA] = None
) -> pd.DataFrame:
    """Get projects a user has access to and merge them with issues count."""
    jira, df_prj = connect_to_jira_and_print_projects(credentials=credentials, jira=jira)

    list_to_analyze = _get_list_to_analyze(df_prj, project_keys)
    if list_to_analyze is not None:
        df_prj = df_prj[df_prj['key'].isin(list_to_analyze)]

    df_count = jira_get_issues_count_for_projects(jira, df_prj, after_date, projects_lst=list_to_analyze)
    if df_count.empty:
        logging.info("There are no issues in the requested projects")
        return df_prj

    df_result = pd.merge(df_prj, df_count, on='key', how='left')
    df_result = df_result.sort_values(by='issues_count', ascending=False, ignore_index=True).reset_index(drop=True)
    return df_result


def _get_list_to_analyze(df_prj: pd.DataFrame, project_keys: Optional[str] = None) -> list | None:
    """Get list of projects to analyze."""
    if project_keys is None or project_keys.strip() == "":
        logging.info("No project keys were provided. All projects will be analyzed.")
        return None

    list_to_analyze = []

    projects_list = project_keys.strip().replace(" ", "").split(",")

    available_projects = df_prj["key"].tolist()
    for project in projects_list:
        if project not in available_projects:
            logging.warning(
                f"Project {project} is not available in the list of accessible projects."
            )
        else:
            list_to_analyze.append(project)
    return list_to_analyze


def jira_get_issues_count_for_projects(
    jira: JIRA, df_prj: pd.DataFrame, after_date: str, projects_lst: Optional[list] = None
) -> pd.DataFrame:
    """Loop through every project and get issues count via JQL request."""
    if projects_lst is None:
        projects_lst = df_prj['key'].tolist()

    projects_and_issues_num = {}

    for prj in projects_lst:
        jql = f'project = "{prj}" AND updated >= {after_date}'
        projects_and_issues_num[prj] = jira_get_issues_count(jira, jql)

    df_count = pd.DataFrame.from_dict(projects_and_issues_num, orient='index', columns=['issues_count'])
    df_count = df_count.reset_index()
    df_count = df_count.rename(columns={'index': 'key'})
    return df_count


def jira_get_issues_count(jira: JIRA, jql: str, block_size: int = 100, block_num: int = 0, fields: str = "key") -> int:
    """Request issues for one project which were updated after set date and return their number."""
    issues_num = 0
    try:
        jira_search = jira.search_issues(jql, startAt=block_num * block_size, maxResults=block_size, fields=fields)
        while jira_search:
            issues_num_one_block = len(jira_search)
            issues_num += issues_num_one_block
            block_num += 1
            jira_search = jira.search_issues(jql, startAt=block_num * block_size, maxResults=block_size, fields=fields)
        return issues_num
    except JIRAError as err:
        logging.error(f"Jira connection has been failed. Error: {err.status_code}, {err.text}")
        return issues_num
