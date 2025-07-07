"""Module to work with Azure DevOps."""
import time

from datetime import datetime, timedelta, date
from typing import Optional

import requests
import pandas as pd

from ..ado.azure_base import AzureBase
from ..ado.utils import repeat_request
from ..utils.transform import waiting_time_for_jobs_in_pipeline
from ..utils.convert_to_datetime import string_to_datetime
from ..utils.constants import OUTPUT_FOLDER
from ..utils.transform_jira import statuses_order_jira


PIPELINES_COLUMN_MAPPING = {
    'state': 'run_state',
    'result': 'run_result',
    'createdDate': 'run_created_date',
    'finishedDate': 'run_finished_date',
    'url': 'run_url',
    'id': 'run_id',
    'name': 'run_name',
    '_links.self.href': '_links_self_href',
    '_links.web.href': '_links_web_href',
    '_links.pipeline.web.href': '_links_pipeline_web_href',
    '_links.pipeline.href': '_links_pipeline_href',
    'pipeline.url': 'pipeline_url',
    'pipeline.id': 'pipeline_id',
    'pipeline.revision': 'pipeline_revision',
    'pipeline.name': 'pipeline_name',
    'pipeline.folder': 'pipeline_folder'
}


BUILDS_COLUMN_MAPPING = {
    'id': 'job_id',
    'type': 'job_type',
    'name': 'job_name',
    'startTime': 'job_start_time',
    'finishTime': 'job_finish_time',
    'currentOperation': 'job_current_operation',
    'percentComplete': 'job_percent_complete',
    'state': 'job_state',
    'result': 'job_result',
    'workerName': 'job_worker_name',
    'details': 'job_details',
    'errorCount': 'job_error_count',
    'warningCount': 'job_warning_count',
    'attempt': 'job_attempt',
}


class AzureDevOps(AzureBase):  # pylint: disable=too-many-public-methods
    '''
    Class to work with Azure DevOps.
    '''
    def __init__(self, organization, project_id,  # pylint: disable=too-many-arguments
                 default_branch_name, user, token=None):
        super().__init__(organization, project_id, user, token)
        self.default_branch_name = default_branch_name

    def get_single_work_item(self, work_item_id: str) -> None:
        """Get a single work item.
        Details on a page:
        https://docs.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/get-work-item?view=azure-devops-rest-6.0
        """
        request_url = (f'https://dev.azure.com/{self.organization}/{self.project_id}/_apis/wit/workitems/{work_item_id}'
                       f'?$expand=All&api-version=6.0')
        response = self.make_get_request(request_url)
        item = response.json()
        self._crate_list_of_relations(item)

    def _crate_list_of_relations(self, item: dict) -> None:
        relations_lst = []
        try:
            relations = item['relations']
            for relation in relations:
                attributes = relation['attributes']
                related_name = attributes['name']
                if related_name == 'Integrated in build':
                    relations_lst.append(
                        self._generate_relation_list(item['id'], attributes, relation.get('url')))
        except KeyError as err:
            print('There is not such attribute as', err)
            print('Please review the work item:', item)
        print(relations_lst)

    @staticmethod
    def _generate_relation_list(id_: str, attributes: dict, url: str) -> list:
        return [
            id_, attributes.get('id'),
            attributes.get('authorizedDate'),
            attributes.get('resourceCreatedDate'),
            attributes.get('resourceModifiedDate'),
            url,
        ]

    def wiql_work_items_limit(self, team: str, dates: tuple[str, str, str], area: str) -> dict[str, str]:
        """
        Get a list of all work items (open, closed and bugs separately).
        The number is limited to 10000 items for every query.

        Details on a page:
        https://docs.microsoft.com/en-us/rest/api/azure/devops/wit/wiql/query-by-wiql?view=azure-devops-rest-6.0
        """
        request_url = (f'https://dev.azure.com/{self.organization}/{self.project_id}/{team}/'
                       f'_apis/wit/wiql?$top=10000&api-version=6.0')
        query_area = self._process_query_area(area) if area else ''
        resolved_after, updated_after, created_after = dates
        # Three different queries for open, closed work items and bugs
        where_statements_list = [
            f'[Microsoft.VSTS.Common.ClosedDate] >= {resolved_after}',
            f'[Microsoft.VSTS.Common.ClosedDate] = "" AND [System.ChangedDate] >= {updated_after}',
            f'[System.WorkItemType] = "Bug" AND [System.CreatedDate] >= {created_after}',
        ]
        queries_lst = self._create_queries_list(where_statements_list, query_area)
        result = {}
        for index, query in enumerate(queries_lst):
            self._run_item_work_limit_query(index, query, request_url, result)

        return result

    @staticmethod
    def _process_query_area(area: str) -> str:
        """Make area suitable for SQL query."""
        area = [f'"{i}"' for i in area.replace(',', ' ').split()]
        area = ', '.join(area)
        return f'AND [System.AreaPath] IN ({area})'

    def _create_queries_list(self, where_statements_list: list[str], query_area: str) -> list[dict]:
        """Create a list of SQL queries based on 'WHERE' conditions."""
        return [self._generate_query(where_statement, query_area) for where_statement in where_statements_list]

    def _generate_query(self, where_statement: str, query_area: str) -> dict:
        """Generate a dictionary with a SQL query."""
        return {'query': f'Select [System.Id], [System.Title], [System.State] From WorkItems Where {where_statement} '
                         f'AND [System.TeamProject] = "{self.project_id}" {query_area}'}

    def _run_item_work_limit_query(self, index: int, query: dict[str, str], request_url: str, result: dict) -> None:
        """Run and process query."""
        response = self.make_post_request(request_url, query)
        response.raise_for_status()
        result[f'result_{str(index + 1)}'] = response.json()['workItems']

    @repeat_request(repeat_num=10)
    def make_post_request(self, request_url: str, query: dict[str, str]) -> requests.Response:
        """Make POST request based on authentication."""
        kwargs = {'json': query}
        if self.token is not None:
            kwargs['auth'] = (self.user, self.token)
        try:
            response = requests.post(request_url, **kwargs)  # pylint: disable=missing-timeout
        except requests.exceptions.RequestException as err:
            print('Oops: something went wrong while sending POST request:', err)
            raise
        response.raise_for_status()
        return response

    def wiql_work_items(self, dates: tuple[str, str, str], area: str) -> Optional[dict[str, list]]:
        """
        Get list of all work items (ope, closed and bugs separately). There is no limit on the number of work items.
        Details on a page:
        https://docs.microsoft.com/en-us/rest/api/azure/devops/wit/wiql/query-by-wiql?view=azure-devops-rest-6.0
        """
        request_url = f'https://dev.azure.com/{self.organization}/{self.project_id}/_apis/wit/wiql?api-version=6.0'
        result = {}
        query_area = self._process_query_area(area) if area else ''

        # Three different queries for open, closed work items and bugs
        for idx, date_str in enumerate(dates):
            result[f'result_{str(idx + 1)}'] = self._get_list_of_closed_work_items(
                idx, date_str, query_area, request_url)

        print("Closed items", len(result['result_1']))
        print("Open items", len(result['result_2']))
        print("Bugs", len(result['result_3']))

        return result

    def _get_list_of_closed_work_items(self, idx: int, date_str: str, query_area: str, request_url: str) -> list:
        """Get a list of closed work items."""
        date_ = date.fromisoformat(date_str)
        count = 0
        date_after = date_
        date_before = datetime.today()
        result = []
        while True:
            where_statement = self._get_where_statement(idx, date_after, date_before)
            query = self._generate_query(where_statement, query_area)
            count += 1
            try:
                response = self.make_post_request(request_url, query)
                result += response.json()['workItems']
                # Exit loop when get to the resolved_after/updated_after/created_after
                if date_after <= date_:
                    break
                date_before, date_after = self._get_before_after_dates(count)
                date_after = max(date_after, date_)
            except requests.exceptions.HTTPError as err:
                print(err)
                if date_after <= date_ or "The following project does not exist" in str(err):
                    break
                date_before, date_after = self._get_before_after_dates(count)
        return result

    @staticmethod
    def _get_where_statement(idx, date_after, date_before) -> str:
        match idx:
            case 0:
                return f'[Microsoft.VSTS.Common.ClosedDate] >= "{str(date_after)[:10]}" AND ' \
                       f'[Microsoft.VSTS.Common.ClosedDate] < "{str(date_before)[:10]}"'
            case 1:
                return f'[Microsoft.VSTS.Common.ClosedDate] = "" AND ([System.ChangedDate] >= ' \
                       f'"{str(date_after)[:10]}" AND [System.ChangedDate] < "{str(date_before)[:10]}")'
            case 2:
                return f'[System.WorkItemType] = "Bug" AND ([System.CreatedDate] >= "{str(date_after)[:10]}" AND ' \
                       f'[System.CreatedDate] < "{str(date_before)[:10]}")'

    @staticmethod
    def _get_before_after_dates(count: int) -> tuple[date, date]:
        days_delta = 7  # Number of days to consequently subtract from current date in while loops
        date_before = (datetime.today() - timedelta(days_delta * (count - 1))).date()
        date_after = (datetime.today() - timedelta(days_delta * count)).date()
        return date_before, date_after

    def get_work_items_batch(self, ids: dict) -> pd.DataFrame:
        """
        Get info on a list of work items.
        Details on a page:
        https://docs.microsoft.com/en-us/rest/api/azure/devops/wit/work-items/get-work-items-batch
        """
        df_batch = pd.DataFrame()
        for key, value in ids.items():
            ids_list = [v['id'] for v in value] if isinstance(value, list) else value
            if len(ids_list) == 0:
                continue
            ids_blocks = [ids_list[i:i+200] for i in range(0, len(ids_list), 200)]
            data = []
            for block in ids_blocks:
                data += self._get_data_block(block)
            result = []
            for item in data:
                result.append(self._get_block_attributes(item, key))
            df_block = pd.DataFrame(result,
                                    columns=['issue_key', 'issue_id', 'issue_type', 'priority', 'resolution', 'summary',
                                             'status', 'total_time_spent', 'labels', 'fix_versions', 'linked_issues',
                                             'components', 'subtasks', 'created_date', 'start_date', 'resolved_date',
                                             'last_updated_date', 'reporter_name', 'assignee_name', 'project_name',
                                             'project_key', 'request_type', 'team', 'defects_environment']
                                    )
            df_batch = pd.concat([df_batch, df_block], ignore_index=True)
        return df_batch

    def _get_data_block(self, ids_item: list) -> Optional[dict]:
        """Get work items batch based on list of ids."""
        request_url = (f'https://dev.azure.com/{self.organization}/{self.project_id}/_apis/wit/workitemsbatch'
                       f'?api-version=6.0')
        body = {"$expand": "all", "ids": ids_item}
        for _ in range(100):
            try:
                response = self.make_post_request(request_url, body)
                data_block = response.json()['value']
                return data_block
            except requests.exceptions.ConnectionError:
                time.sleep(60)
        return None

    @staticmethod
    def _get_block_attributes(item, key) -> list:
        """Get a list of block attributes."""
        request_type_dict = {'result_1': 'closed', 'result_2': 'open', 'result_3': 'defect'}
        fields = item.get('fields', {})
        return [None, item['id'], fields.get('System.WorkItemType'), fields.get('Microsoft.VSTS.Common.Priority'),
                fields.get('System.Reason'), None, fields.get('System.State'), None, None, None, None, None, None,
                fields.get('System.CreatedDate'), None, fields.get('Microsoft.VSTS.Common.ClosedDate'),
                fields.get('System.ChangedDate'), None, fields.get('System.AssignedTo', {}).get('displayName'),
                fields.get('System.TeamProject'), None, request_type_dict.get(key), fields.get('System.AreaPath'), None]

    def work_items_and_info(self, resolved_after, updated_after, created_after, area) -> pd.DataFrame:
        '''Get work items list and information on them.'''
        ids = self.wiql_work_items((resolved_after, updated_after, created_after), area)
        if ids:
            df = self.get_work_items_batch(ids)
            return df
        return pd.DataFrame()

    def concat_work_items_and_history(self, resolved_after: str, updated_after: str, created_after: str, area: str) -> \
            tuple[pd.DataFrame, pd.DataFrame]:
        """Concatenate work items with history."""
        df_wi_info = self.work_items_and_info(resolved_after, updated_after, created_after, area)
        if df_wi_info.empty:
            return df_wi_info, df_wi_info
        ids = df_wi_info[df_wi_info['request_type'] != 'defect'][['issue_id', 'request_type']].values.tolist()

        if not ids:
            df_history = df_wi_info
            df_history[['status_history', 'from_time', 'to_time', 'time_in_status']] = None
            return df_history, pd.DataFrame()

        df_history = self.process_history(ids)
        df_wi_history = df_wi_info.merge(df_history, on='issue_id', how='left')
        df_statuses = statuses_order_jira(df_wi_history)
        df_wi_history = df_wi_history.drop(['cum_count'], axis=1)

        return df_wi_history, df_statuses

    def process_history(self, ids: list) -> pd.DataFrame:
        """Process histories."""
        history = []
        for item in ids:
            one_transition = self.get_work_items_update(item)
            history.extend(one_transition)

        df_history = pd.DataFrame(
            history, columns=['issue_id', 'status_history', 'from_date', 'to_date', 'time_in_status'])
        df_history['cum_count'] = df_history.sort_values(by=['issue_id', 'from_date']).groupby(['issue_id']).cumcount()
        return df_history

    def get_work_items_update(self, work_item_id: list) -> list[list]:
        """
        Get history of statuses transitions for a single work item.
        Details on a page: https://docs.microsoft.com/en-us/rest/api/azure/devops/wit/updates/list?
        view=azure-devops-rest-6.0#list-of-work-item-updates-(project-scoped)
        """
        request_url = (f'https://dev.azure.com/{self.organization}/_apis/wit/workitems/{work_item_id[0]}/'
                       f'updates?api-version=6.0')
        response = self.make_get_request(request_url)
        updates = response.json().get('value', [])
        if not updates:
            return []

        count_state_trans = sum(1 for update in updates if 'System.State' in update.get('fields', {}))
        if count_state_trans <= 1:
            return self._get_work_items_update_for_single_state_transition(work_item_id, updates)

        return self._get_work_items_update_for_multiple_state_transitions(work_item_id, updates)

    @staticmethod
    def _get_work_items_update_for_single_state_transition(work_item_id: list, updates: dict) -> list[list]:
        """Get work items update for single state transition."""
        if work_item_id[1] == 'open':
            for update in updates:
                try:
                    status_history = update['fields']['System.State']
                    date_new = update['fields']['Microsoft.VSTS.Common.StateChangeDate']['newValue']
                    date_new = string_to_datetime(date_new)
                    to_date = datetime.utcnow().replace(microsecond=0)
                    time_in_status = round(((to_date - date_new).total_seconds() / (24 * 60 * 60)), 2)
                    return [[work_item_id[0], status_history['newValue'], date_new, to_date, time_in_status]]
                except KeyError:
                    pass
        return []

    @staticmethod
    def _get_work_items_update_for_multiple_state_transitions(work_item_id: list, updates: dict) -> list[list]:
        """Get work items update for multiple state transitions."""
        history = []
        last_trans = []
        for update in updates:
            try:
                status_history = update['fields']['System.State']
                date_old = update['fields']['Microsoft.VSTS.Common.StateChangeDate']['oldValue']
                to_date = update['fields']['Microsoft.VSTS.Common.StateChangeDate']['newValue']
                date_old = string_to_datetime(date_old)
                to_date = string_to_datetime(to_date)
                time_in_status = round(((to_date - date_old).total_seconds() / (24 * 60 * 60)), 2)
                last_trans = [status_history['newValue'], to_date]
                history.append([work_item_id[0], status_history['oldValue'], date_old, to_date, time_in_status])
            except KeyError:
                pass
        if work_item_id[1] == 'closed' and last_trans:
            history.append(([work_item_id[0], last_trans[0], last_trans[1], None, None]))
        if work_item_id[1] == 'open':
            try:
                to_date = datetime.utcnow().replace(microsecond=0)
                time_in_status = round((datetime.utcnow() - last_trans[1]).total_seconds() / (24 * 60 * 60), 2)
                history.append([work_item_id[0], last_trans[0], last_trans[1], to_date, time_in_status])
            except IndexError:
                pass
        return history

    def get_diff(self, repository_id: str, base_commit_id: str, target_commit_id: str) -> dict:
        """Get the diff between the base and target commits."""
        request_url = (f'https://dev.azure.com/{self.organization}/{self.project_id}/_apis/git/repositories/'
                       f'{repository_id}/diffs/commits?baseVersion={base_commit_id}&baseVersionType=commit'
                       f'&targetVersion={target_commit_id}&targetVersionType=commit&api-version=7.0')
        response = self.make_get_request(request_url)
        return response.json()

    def get_associated_commits_to_pr(self, repos_id, pull_request_id) -> Optional[pd.DataFrame]:
        """
        Get associated pull request commits.
        Doesn't return system commits/
        Details on the page:
        https://docs.microsoft.com/en-us/rest/api/azure/devops/git/pull-request-commits/get-pull-request-commits
        """
        request_url = (f'https://dev.azure.com/{self.organization}/{self.project_id}/_apis/git/repositories/{repos_id}/'
                       f'pullRequests/{pull_request_id}/commits?api-version=6.0')
        response = self.make_get_request(request_url)
        try:
            data = response.json()['value']
            df_commits = pd.json_normalize(data)
            return df_commits.loc[:, ['author.date', 'comment', 'commitId']]
        except KeyError:
            return None

    def get_all_pull_requests_details(self, since_date: str, skip: int = 0) -> Optional[pd.DataFrame]:
        """
        Get and process.
        Details on a page:
        https://docs.microsoft.com/en-us/rest/api/azure/devops/git/pull-requests/get-pull-requests-by-project
        """
        df_pr_data = self._get_pull_requests_data(skip)
        if df_pr_data.empty:
            return None
        df_pr_data['creationDate_formatted'] = df_pr_data['creationDate'].str.split('T', expand=True)[0]
        df_pr_data = df_pr_data[df_pr_data['creationDate_formatted'] >= since_date]
        df_pull_requests = self._adapt_df_to_github(df_pr_data)
        repos_ids = self.get_repos()
        df_pull_requests = self._add_commit_dates(repos_ids, df_pr_data, df_pull_requests)
        df_pull_requests = df_pull_requests.reset_index(level=0)
        df_pull_requests.rename(columns={'creationDate': 'created_at',
                                         'closedDate': 'closed_at',
                                         'sourceRefName': 'source_branch',
                                         'repository.project.name': 'project_id',
                                         'pullRequestId': 'merge_commit_sha',
                                         'repository.id': 'repository_id',
                                         'repository.name': 'repository_name'},
                                inplace=True)
        df_pull_requests = df_pull_requests[
            ['project_id', 'repository_id', 'repository_name', 'created_at', 'merged_at', 'closed_at',
             'merge_commit_sha', 'source_branch', 'first_commit_date', 'last_commit_date']]
        print("Pull requests data has been downloaded to the folder 'raw_data'")
        return df_pull_requests

    def _get_pull_requests_data(self, skip: int) -> pd.DataFrame:
        """Gather data of all pull requests."""
        data = []
        count = True
        while count:
            request_url = (f'https://dev.azure.com/{self.organization}/{self.project_id}/'
                           f'_apis/git/pullrequests?searchCriteria.status=all&$skip={skip}&$top=200'
                           f'&api-version=6.0')
            response = self.make_get_request(request_url)
            data_unit = response.json().get('value')
            if data_unit:
                data += data_unit
            count = response.json().get('count')
            skip += 200
        return pd.json_normalize(data)

    @staticmethod
    def _adapt_df_to_github(df_pr_data: pd.DataFrame) -> pd.DataFrame:
        """Adapt data to suit GitHub format."""
        df_pull_requests = df_pr_data.loc[:, ['creationDate',
                                              'closedDate',
                                              'pullRequestId',
                                              'sourceRefName',
                                              'mergeStatus',
                                              'repository.project.name',
                                              'repository.id',
                                              'repository.name']]
        # Reformat the columns to match with template for GitLab
        df_pull_requests['merged_at'] = None
        df_pull_requests.loc[
            df_pull_requests['mergeStatus'] == 'succeeded', ['merged_at']] = df_pull_requests.loc[:, 'closedDate']
        df_pull_requests.loc[df_pull_requests['mergeStatus'] == 'succeeded', ['closedDate']] = None
        df_pull_requests.drop(columns=['mergeStatus'])
        df_pull_requests.set_index('pullRequestId', inplace=True)
        # Add info on first and last commit associated with merge request
        df_pull_requests['first_commit_date'] = None
        df_pull_requests['last_commit_date'] = None
        return df_pull_requests

    def _add_commit_dates(
            self, repos_ids: dict, df_pr_data: pd.DataFrame, df_pull_requests: pd.DataFrame) -> pd.DataFrame:
        """Add first and last commits dates."""
        for repos_id in repos_ids:
            merge_req_ids = df_pr_data[df_pr_data['repository.id'] == repos_id]['pullRequestId'].to_list()
            for merge_req_id in merge_req_ids:
                merge_req_commits_df = self.get_associated_commits_to_pr(repos_id, merge_req_id)
                if merge_req_commits_df is None:
                    print("empty df")
                else:
                    if len(merge_req_commits_df) == 1:
                        commit_min_date = merge_req_commits_df['author.date'].min()
                        df_pull_requests.at[merge_req_id, 'first_commit_date'] = commit_min_date
                    else:
                        commit_min_date = merge_req_commits_df['author.date'].min()
                        commit_max_date = merge_req_commits_df['author.date'].max()
                        df_pull_requests.at[merge_req_id, 'first_commit_date'] = commit_min_date
                        df_pull_requests.at[merge_req_id, 'last_commit_date'] = commit_max_date
        return df_pull_requests

    def get_pipelines(self) -> dict:
        """
        Get pipelines.
        Details on the page: https://docs.microsoft.com/en-us/rest/api/azure/devops/pipelines/pipelines/list
        """
        data = []
        request_url = (f'https://dev.azure.com/{self.organization}/{self.project_id}/'
                       f'_apis/pipelines?$top=100&&api-version=6.0-preview.1')
        while True:
            response = self.make_get_request(request_url)
            continuation_token = response.headers.get('x-ms-continuationtoken')
            request_url = (f'https://dev.azure.com/{self.organization}/{self.project_id}/'
                           f'_apis/pipelines?$top=100&continuationToken={continuation_token}'
                           f'&api-version=6.0-preview.1')
            value = response.json().get('value')
            if value:
                data += value
            if not continuation_token:
                break
        return {pipeline['id']: [pipeline['name'], self.project_id] for pipeline in data}

    def get_pipelines_runs(self, pipeline_id: str) -> Optional[pd.DataFrame]:
        """
        Retrieve pipeline runs from Azure DevOps and returns a DataFrame containing the pipeline runs data.
        Details on the page: https://docs.microsoft.com/en-us/rest/api/azure/devops/pipelines/runs/list
        """
        request_url = (f'https://dev.azure.com/{self.organization}/{self.project_id}/'
                       f'_apis/pipelines/{pipeline_id}/runs/?api-version=6.0-preview.1')
        response = self.make_get_request(request_url)
        data = response.json().get('value')
        if data is None:
            print(f"There is no runs for the pipeline id {pipeline_id}")
            return None
        df_pipelines = pd.json_normalize(data)
        df_pipelines = df_pipelines[PIPELINES_COLUMN_MAPPING.keys()]
        df_pipelines = df_pipelines.rename(columns=PIPELINES_COLUMN_MAPPING)
        return df_pipelines

    def get_pipelines_and_runs(self) -> pd.DataFrame:
        """Retrieves pipeline data and their respective run data and merges it into a single DataFrame."""
        pipelines_dict = self.get_pipelines()
        all_data = []

        for pipeline_id, (_, project_name) in pipelines_dict.items():
            run_data = self.get_pipelines_runs(pipeline_id)
            if run_data is not None:
                run_data['project_name'] = project_name
                all_data.append(run_data)

        return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

    def get_builds(self) -> tuple[list, pd.DataFrame]:
        """
        Retrieves builds data from Azure DevOps and returns the build IDs and a DataFrame containing the builds' data.
        """
        request_url = f'https://dev.azure.com/{self.organization}/{self.project_id}/_apis/build/builds?api-version=6.0'
        response = self.make_get_request(request_url)
        data = response.json().get('value')
        if not data:
            raise KeyError(
                f'There are no builds for organization "{self.organization}" with the project id "{self.project_id}"')
        builds_ids = [item['id'] for item in data]
        df_builds = pd.json_normalize(data)
        df_builds = df_builds.rename(columns={'id': 'build_id'})
        return builds_ids, df_builds

    def get_timeline(self, build_id: str) -> Optional[pd.DataFrame]:
        """Function to get the timeline details of a specific build id."""
        request_url = (f'https://dev.azure.com/{self.organization}/{self.project_id}/'
                       f'_apis/build/builds/{build_id}/timeline?api-version=6.0')
        response = self.make_get_request(request_url)
        data = response.json().get('records')
        if data is None:
            print(f'There are no records for build "{build_id}"')
            return None
        df_timeline = pd.json_normalize(data)
        # Keep only necessary columns
        df_timeline = df_timeline[BUILDS_COLUMN_MAPPING.keys()]
        df_timeline = df_timeline.rename(columns=BUILDS_COLUMN_MAPPING)
        return df_timeline

    def get_pipelines_runs_and_timeline(self, to_save) -> Optional[pd.DataFrame]:
        """Get pipelines and run timelines."""
        pipelines_runs = self.get_pipelines_and_runs()
        if pipelines_runs.empty:
            print("There are no pipelines runs")
            return None
        run_ids = pipelines_runs['run_id'].to_list()
        timeline_df = pd.DataFrame()
        for run in run_ids:
            df_timeline = self.get_timeline(run)
            if df_timeline is not None:
                df_timeline['run_id'] = run
                timeline_df = pd.concat([timeline_df, df_timeline])
        runs_details_df = pipelines_runs.merge(timeline_df, how='outer', on='run_id')
        runs_details_df = runs_details_df[runs_details_df['job_type'] == 'Job']
        runs_details_df = runs_details_df.rename(columns={'name_y': 'job name', 'state_y': 'job state',
                                                          'result_y': 'job result', 'name_x': 'name',
                                                          'state_x': 'state',
                                                          'result_x': 'result'})
        if to_save:
            runs_details_df.to_csv(f'{OUTPUT_FOLDER}pipelines_{self.project_id}.csv')
            print(f'Data has been downloaded to the folder "{OUTPUT_FOLDER}"')
        # Calculate waiting time for jobs and add it to the dataframe
        runs_details_df = waiting_time_for_jobs_in_pipeline(runs_details_df)
        return runs_details_df

    def associated_work_items_to_build(self, build_id) -> pd.DataFrame:
        '''
        Gets the work items associated with a build
        Details on page :
        https://docs.microsoft.com/en-us/rest/api/azure/devops/build/builds/get-build-work-items-refs?view=azure-devops-rest-6.0
        '''
        request_url = f"https://dev.azure.com/{self.organization}/{self.project_id}/" \
                      f"_apis/build/builds/{build_id}/workitems?api-version=6.0"
        if self.token is not None:
            req = self.session.get(request_url, auth=(self.user, self.token))
        else:
            req = self.session.get(request_url)
        try:
            data = req.json()['value']
            return data
        except KeyError:
            return pd.DataFrame()

    def get_iterations(self) -> Optional[pd.DataFrame]:
        """Get iterations (sprints).
        Details on a page: https://docs.microsoft.com/en-us/rest/api/azure/devops/work/iterations/list.
        """
        teams_lst = self.get_teams()
        if not teams_lst:
            return None

        iterations_df = pd.DataFrame()
        for team in teams_lst:
            if team:
                request_url = (f'https://dev.azure.com/{self.organization}/{self.project_id}/{team}/'
                               f'_apis/work/teamsettings/iterations?api-version=6.0')
                response = self.make_get_request(request_url)
                data = response.json().get('value')
                if data:
                    next_df = pd.json_normalize(data)
                    next_df['team'] = team
                    iterations_df = pd.concat([iterations_df, next_df], ignore_index=True)
        return iterations_df

    def get_teams(self) -> list:
        """Get teams list.
        Details on a page: https://docs.microsoft.com/en-us/rest/api/azure/devops/core/teams/get-teams.
        """
        request_url = (f'https://dev.azure.com/{self.organization}/_apis/projects/{self.project_id}/'
                       f'teams?api-version=6.0')
        response = self.make_get_request(request_url)
        data = response.json().get('value', [])
        return [team.get('id', None) for team in data]
