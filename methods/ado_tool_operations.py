#!/usr/bin/python3
# coding=utf-8

""" AdoDataExtractor Tool Operations """

from typing import Any, Dict, Optional
from ..extractors.utils.constants import OUTPUT_WORK_ITEMS_FILE
from ..extractors.ado.azure_search import AzureSearch
from ..extractors.ado.main import (
    OUTPUT_WORK_ITEMS,
    get_work_items_several_projects,
    get_commits_several_projects,
    get_merge_requests_several_projects,
    get_pipelines_runs_several_projects,
)


from pylon.core.tools import log, web


class Method:
    """ Tool operation methods """

    @web.method()
    def get_project_list(self, ado_search: AzureSearch):
        """
        Get all projects in the organization that the authenticated user has access to.
        Details on a page: https://docs.microsoft.com/en-us/rest/api/azure/devops/core/projects/list
        """
        df_fpojects = ado_search.get_projects_list()

        csv_data = df_fpojects.to_csv(index=False)

        if df_fpojects.empty:
            log.warning("No projects found for the authenticated user.")
            message = "No projects found for the authenticated user."
        else:
            log.info(f"Extracted projects DataFrame:\n{df_fpojects.head()}")
            message = f"Found {len(df_fpojects)} projects."

        return  csv_data, message

    @web.method()
    def get_work_items(
        self,
        ado_search: AzureSearch,
        resolved_after: str,
        updated_after: str,
        created_after: str,
        project_keys: str,
        area: str = "",
    ) :
        """
        Get work items from multiple Azure DevOps projects.

            project_keys: str
                Comma-separated project names.
            resolved_after: str
                Date filter for resolved items 'YYYY-MM-DD'.
            updated_after: str
                Date filter for updated items 'YYYY-MM-DD'.
            created_after: str
                Date filter for created items 'YYYY-MM-DD'.
            project_keys: str
                Comma-separated project names.
            area: str
                Area path filter (optional).
        """
        df_work_items = get_work_items_several_projects(
            project_keys,
            resolved_after,
            updated_after,
            created_after,
            area=area,
            ado_search=ado_search,
        )

        csv_data = df_work_items.to_csv(index_label="id", index=False)

        if df_work_items.empty:
            log.warning("No work items found for the specified criteria.")
            message = "No work items found for the specified criteria."
        else:
            log.info(f"Extracted work items DataFrame:\n{df_work_items.head()}")
            message = f"Found {len(df_work_items)} work items."

        return csv_data, message

    @web.method()
    async def get_commits(
        self,
        ado_search: AzureSearch,
        since_date: str,
        project_keys: str,
        new_version: bool = True,
        with_commit_size: bool = True,
    ):
        """
        Get commits from multiple Azure DevOps projects.

        since_date: str
            Get commits after this date 'YYYY-MM-DD'.
        project_keys: str
            Comma-separated project names.
        new_version: bool
            If True, returns commits with new versioning.
        with_commit_size: bool
            If True, includes commit size in the results.
        """
        # await
        df_commits = await get_commits_several_projects(
            project_keys,
            since_date,
            new_version=new_version,
            with_commit_size=with_commit_size,
            ado_search=ado_search,
        )

        csv_data = df_commits.to_csv(index_label="id", index=False)

        if df_commits.empty:
            log.warning("No commits found for the specified criteria.")
            message = "No commits found for the specified criteria."
        else:
            log.info(f"Extracted commits DataFrame:\n{df_commits.head()}")
            message = f"Found {len(df_commits)} commits."

        return csv_data, message

    @web.method()
    def get_merge_requests(self, ado_search: AzureSearch, since_date: str, project_keys: str,):
        """
        Get merge requests from multiple Azure DevOps projects.

        ado_search: AzureSearch
            Initialized AzureSearch client instance.
        since_date: str
            Get merge requests after this date 'YYYY-MM-DD'.
        project_keys: str
            Comma-separated project names.
        """
        df_prs = get_merge_requests_several_projects(
            project_keys, since_date, ado_search
        )

        csv_data = df_prs.to_csv(index=False)

        if df_prs.empty:
            log.warning("No pull requests found for the specified criteria.")
            message = "No merge requests found for the specified criteria."
        else:
            log.info(f"Extracted merge requests DataFrame:\n{df_prs.head()}")
            message = f"Found {len(df_prs)} merge requests."

        return csv_data, message
    
    @web.method()
    def get_pipelines_runs(self, ado_search: AzureSearch, project_keys: str):
        """
        Get pipeline runs from multiple Azure DevOps projects.

        ado_search: AzureSearch
            Initialized AzureSearch client instance.
        project_keys: str
            Comma-separated project names.
        """
        pipelines_df = get_pipelines_runs_several_projects(project_keys, ado_search=ado_search)

        csv_data = pipelines_df.to_csv(index=False)

        if pipelines_df.empty:
            log.warning("No pipeline runs found for the specified criteria.")
            message = "No pipeline runs found for the specified criteria."
        else:
            log.info(f"Extracted pipeline runs DataFrame:\n{pipelines_df.head()}")
            message = f"Found {len(pipelines_df)} pipeline runs."

        return csv_data, message