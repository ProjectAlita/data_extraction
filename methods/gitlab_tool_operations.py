#!/usr/bin/python3
# coding=utf-8

""" AdoDataExtractor Tool Operations """

from ..extractors.git.main import (
    get_git_projects_list,
    get_git_projects_that_in_jira,
    get_git_commits,
    get_git_merge_requests,
)
from ..extractors.git.git_search import GitLabV4Search

from pylon.core.tools import log, web


class Method:
    """ Tool operation methods """

    @web.method()
    def get_gitlab_project_list(self, gitlab_search: GitLabV4Search, date: str) :
        """
        Get projects list that user has access to in GitLab.

        gitlab_search: GitLabV4Search
            GitLab search client.
        date: str
            Filter projects by last activity date.
            Date in 'YYYY-MM-DD' format.
        """
        df_project_list = get_git_projects_list(date, git=gitlab_search)

        csv_data = df_project_list.to_csv(index=False)

        if df_project_list.empty:
            log.warning("No projects found for the authenticated user.")
            message = "No projects found for the authenticated user."
        else:
            log.info(f"Extracted projects DataFrame:\n{df_project_list.head()}")
            message = f"Found {len(df_project_list)} projects."

        return csv_data, message

    @web.method()
    def get_gitlab_projects_that_in_jira(self, gitlab_search: GitLabV4Search, jira_project_keys: str):
        """
        Find GitLab projects that correspond to Jira projects by matching names.

        gitlab_search: GitLabV4Search
            GitLab search client.
        jira_project_keys: str
            Comma-separated Jira project keys.
        """
        df_projects = get_git_projects_that_in_jira(
            jira_project_keys, git=gitlab_search)

        csv_data = ""
        if df_projects is None or df_projects.empty:
            message = "No GitLab projects found that match the provided Jira project keys."
        else:
            csv_data = df_projects.to_csv(index=False)

            message = f"Found {len(df_projects)} GitLab projects that match Jira project names. "

        return csv_data, message

    @web.method()
    def get_gitlab_commits(self, gitlab_search: GitLabV4Search, since_date: str, project_ids: str):
        """
        Get commit data for specified GitLab project.

        gitlab_search: GitLabV4Search
            GitLab search client.
        project_ids: str
            Comma-separated GitLab project IDs.
        since_date: str
            Date filter in 'YYYY-MM-DD' format.
        """
        
        df_commits = get_git_commits(
            project_ids, since_date, git_search=gitlab_search)
        
        csv_data = ""
        if df_commits is None or df_commits.empty:
            log.warning(f"No commits found for project IDs: {project_ids} since {since_date}.")
            message = f"No commits found for project IDs: {project_ids} since {since_date}."
        else:
            csv_data = df_commits.to_csv(index=False)
            log.info(f"Extracted commits DataFrame:\n{df_commits.head()}")
            message = f"Found {len(df_commits)} commits for project IDs: {project_ids} since {since_date}."

        return csv_data, message

    @web.method()
    def get_gitlab_merge_requests(self, gitlab_search: GitLabV4Search, since_date: str, project_ids: str):
        """
        Get merge requests for specified GitLab project.

        gitlab_search: GitLabV4Search
            GitLab search client.
        project_ids: str
            Comma-separated GitLab project IDs.
        since_date: str
            Date filter in 'YYYY-MM-DD' format.
        """
        
        df_prs = get_git_merge_requests(
            project_ids, since_date, git_search=gitlab_search)

        csv_data = ""
        if df_prs is None or df_prs.empty:
            log.warning(f"No merge requests found for project IDs: {project_ids} since {since_date}.")
            message = f"No merge requests found for project IDs: {project_ids} since {since_date}."
        else:
            log.info(f"Extracted merge requests DataFrame:\n{df_prs.head()}")
            message = f"Found {len(df_prs)} merge requests for project IDs: {project_ids} since {since_date}."
            csv_data = df_prs.to_csv(index=False)

        return csv_data, message