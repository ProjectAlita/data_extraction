"""This module gets all the statuses list in a Jira instance."""
from typing import Optional
from jira import JIRA

from ..jira.jira_connect import connect_to_jira


def get_all_statuses_list(credentials: Optional[dict] = None, jira: Optional[JIRA] = None) -> list:
    """Get all statuses names."""
    if jira is None:
        jira = connect_to_jira(credentials=credentials)
    if not jira:
        raise ConnectionError('Failed to connect to Jira')

    statuses = jira.statuses()
    return [status.name for status in statuses]
