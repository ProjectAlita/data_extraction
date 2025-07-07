#!/usr/bin/python3
# coding=utf-8

""" JiraDataExtractor Tool Operations """

from typing import Any, Dict, Optional

from ..extractors.jira.jira_projects_overview import jira_projects_overview
from ..extractors.jira.jira_statuses import get_all_statuses_list
from ..extractors.jira.jira_issues import JiraIssues

from pylon.core.tools import log, web
from jira import JIRA


class Method:
    """ Tool operation methods """

    @web.method()
    def get_number_of_all_issues(self, jira: JIRA, after_date: str, project_keys: str):
        """
        Get projects a user has access to and merge them with issues count.
        after_date: str
            date after which issues are considered
        project_keys: str
            one or more projects keys separated with comma
        """
        log.info(f"get_number_of_all_issues called with after_date={after_date}, project_keys={project_keys}")

        project_df = jira_projects_overview(
            after_date, project_keys=project_keys, jira=jira
        )

        # Convert DataFrame to CSV string for artifact storage
        csv_data = project_df.to_csv(index=False)

        log.info(f"result project_df {project_df}")

        # some meaningful message for the user
        if project_df.empty:
            log.warning(f"No projects found for after_date: {after_date} and project_keys: {project_keys}")
            message = "No projects found for the specified criteria."
        else:
            log.info(f"Extracted projects DataFrame:\n{project_df.head()}")
            message = f"Found {len(project_df)} projects after date: {after_date} with keys: {project_keys}."

        # Return CSV data - provider_worker will handle artifact creation
        return csv_data, message

    @web.method()
    def get_jira_issues(self, 
        jira: JIRA, 
        project_keys: str,                        
        closed_issues_based_on: int,
        closed_status: str,
        defects_name: str,
        resolved_after:str, 
        updated_after: str,
        created_after: str,
        custom_fields: Dict[str, str] = {},
        add_filter: str = ""
    ):
        """
        Extract Jira issues for the specified projects.
        jira: JIRA
            initialized JIRA client instance
        project_keys: str
            one or more projects keys separated with comma
        closed_issues_based_on: int
            define whether issues can be thought as 
            closed based on their status (1) or not empty resolved date (2)
        resolved_after: str
            resolved after date (i.e. 2023-01-01)
        updated_after: str
            updated after date (i.e. 2023-01-01)
        created_after: str
            created after date (i.e. 2023-01-01)
        custom_fields: Dict[str, str]
            custom fields to include in the issues data.
            Format: {"field_name": "field_value"}.
            Example: {"customfield_10001": "value1", "customfield_10002": "value2"}
        add_filter: str
            additional filter for Jira issues in JQL format 
            like "customfield_10000 = 'value' AND customfield_10001 = 'value'"
        """
        if not (
            (
                closed_issues_based_on == 1
                and closed_status in get_all_statuses_list(jira=jira)
            )
            or closed_issues_based_on == 2
        ):
            error_message = (
                f"ERROR: Check input parameters closed_issues_based_on ({closed_issues_based_on}) "
                f"and closed_status ({closed_status}) not in Jira statuses list."
            )
            return "", error_message

        jira_issues = JiraIssues(
            jira=jira,
            projects=project_keys,
            closed_params=(closed_issues_based_on, closed_status),
            defects_name=defects_name,
            add_filter=add_filter
        )

        df_issues, df_map = jira_issues.extract_issues_from_jira_and_transform(
            custom_fields=custom_fields,
            dates=(resolved_after, updated_after, created_after)
        )
        log.info(f"Extracted {len(df_issues)} issues from Jira for projects: {project_keys}")

        # Convert DataFrame to CSV string for artifact storage
        csv_data = df_issues.to_csv(index_label="id")

        # some meaningful message for the user
        if len(df_issues) == 0:
            log.warning(f"No issues found for projects: {project_keys}")
            message = "No issues found for the specified projects." 
        else:
            log.info(f"Extracted issues DataFrame:\n{df_issues.head()}")
            message = f"Found {len(df_issues)} issues for projects: {project_keys}."

        return csv_data, message
