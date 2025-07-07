''' Module for working with GitLab API v4. '''
# first commit -> last commit -> pause time -> merger req created ->
# ->  merge req processed (merged) ready to deploy on first stage of some env
import json
from datetime import datetime
import logging
from typing import Optional
import requests
import pandas as pd

from ..utils.outliers import get_outliers_upper_bound
from ..utils import exceptions as e


pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)


class GitLabV4():
    ''' Class for working with GitLab API v4. '''
    def __init__(self, url: str, project_id: str, default_branch_name: str, token: Optional[str] = None):
        self.url = url
        self.project_id = project_id
        self.default_branch_name = default_branch_name
        self.token = token
        self.reponse_code_handler = e.ResponseCodeHandler(project_id)

    def _load_data(self, url_suffix: str) -> tuple[bool, pd.DataFrame]:
        '''
        Makes GET request to load data from GitLab API.
        '''
        request_url = f"https://{self.url}/api/v4/projects/{self.project_id}/{url_suffix}"
        headers = {"PRIVATE-TOKEN": f"{self.token}"} if self.token else {}
        req = requests.get(request_url, headers=headers)  # pylint: disable=missing-timeout
        self.reponse_code_handler.process_response_code(req.status_code)

        next_page = req.headers.get('X-Next-Page')
        is_next_page_exist = bool(next_page)
        content = json.loads(req.content)
        df = pd.json_normalize(content)
        return is_next_page_exist, df

    def get_commits_details(self, since_date: str, page: int = 1) -> pd.DataFrame:
        '''
        Get recursively list of all repository commits for a project starting from specific date
        (details on page https://docs.gitlab.com/ee/api/commits.html#list-repository-commits)
        '''
        is_next_page_exist, df = self._load_data(f"repository/commits?since={since_date}&per_page=100&page={page}")
        if df.empty:
            return pd.DataFrame()

        commits_df = df.loc[:, ['created_at', 'message', 'id',
                                'committed_date', 'authored_date', 'title']]
        if is_next_page_exist:
            next_commits_df = self.get_commits_details(since_date, page=page + 1)
            commits_df = pd.concat([commits_df, next_commits_df], ignore_index=True)
        return commits_df

    def get_commits_details_per_branch(self, ref_name: str, page: int = 1) -> pd.DataFrame:
        '''
        Get recursively information on first commit to a branch -- list of commits filtered by specific merge request
        (details on page https://docs.gitlab.com/ee/api/commits.html#list-repository-commits)
        '''
        is_next_page_exist, df = self._load_data(
            f"repository/commits?ref_name={ref_name}&first_parent=False&per_page=100&page={page}")
        commits_df = df.loc[:, ['created_at', 'message', 'id', 'committed_date', 'authored_date']]
        if is_next_page_exist:
            next_commits_df = self.get_commits_details_per_branch(ref_name, page=page + 1)
            commits_df = pd.concat([commits_df, next_commits_df], ignore_index=True)
        return commits_df

    def get_single_commit(self, commits_df: pd.DataFrame) -> pd.DataFrame:
        '''
        Get recursively information on a single commit (added and removed lines etc)
        (details on page https://docs.gitlab.com/ee/api/commits.html#get-a-single-commit)
        '''
        single_commits_info = []
        commits_df = commits_df[~commits_df['title'].str.contains('^Merge branch .*', regex=True)]
        commits_df = commits_df[~commits_df['title'].str.contains("^Merge branch '.*' of .*", regex=True)]
        for commit in commits_df['id'].to_list():
            _, df = self._load_data(f"repository/commits/{commit}")
            single_commits_info += [[commit, df.loc[0, 'stats.total']]]
        single_commit_df = pd.DataFrame(single_commits_info, columns=['id', 'commit_size'])

        return single_commit_df

    def get_commits_details_and_size(self, since_date: str) -> Optional[pd.DataFrame]:
        '''
        Merge commits' details with info on their size
        Aggregations of all commits and extra information
        '''
        commits_df = self.get_commits_details(since_date)
        if commits_df is None or commits_df.empty:
            return None

        single_commit_df = self.get_single_commit(commits_df)
        commits_details_and_size_df: pd.DataFrame = commits_df.merge(single_commit_df, how='inner', on='id')
        commits_details_and_size_df['project_id'] = self.project_id
        commits_details_and_size_df = commits_details_and_size_df[['project_id', 'created_at', 'message',
                                                                    'id', 'committed_date',
                                                                    'authored_date', 'commit_size']]
        # Calculate upperbound for outliers
        s = commits_details_and_size_df['commit_size']
        upper_bound = get_outliers_upper_bound(s)
        commits_details_and_size_df['repos_name'] = None
        commits_details_and_size_df['upperBound'] = upper_bound
        print('Commits data has been downloaded')
        return commits_details_and_size_df

    def get_associated_commits_to_merge_req(self, merge_req_id: str) -> pd.DataFrame:
        '''
        (details on page https://docs.gitlab.com/ee/api/merge_requests.html#get-single-mr-commits)
        '''
        _, df = self._load_data(f"merge_requests/{merge_req_id}/commits")
        if df.empty:
            return pd.DataFrame()

        return df.loc[:, ['created_at', 'message', 'id']]

    def get_merge_req_state_count(self, page: int = 0) -> dict:
        '''
        Get statistics on merge requests states for one project (number of merge requests open, closed and merged)
        (details on page https://docs.gitlab.com/ee/api/merge_requests.html#list-project-merge-requests)
        '''
        request_url = f"https://{self.url}/api/v4/projects/{self.project_id}" + \
                      f"/merge_requests?state=all&per_page=100&page={page}"
        merge_req_state_count = {'Open': None, 'Closed': None, 'Merged': None, 'projects_id': self.project_id}
        data_fin = []
        while True:
            r = requests.get(request_url, headers={"PRIVATE-TOKEN": f"{self.token}"})  # pylint: disable=missing-timeout

            if r.status_code in [403, 404]:
                logging.warning(f'Error {r.status_code} while getting merge requests for the project {self.project_id}')
                return merge_req_state_count

            data = r.json()
            data_fin += data

            if 'next' in r.links:  # check if there is another page of organisations
                request_url = r.links['next']['url']
            else:
                break

        if data_fin:
            merge_req_state = [item['state'] for item in data_fin]
            merge_req_state_count.update({'Open': merge_req_state.count("opened"),
                                          'Closed': merge_req_state.count("closed"),
                                          'Merged': merge_req_state.count("merged")})

        return merge_req_state_count

    def get_all_merge_requests_details(self, created_after: str, page: int = 1) -> pd.DataFrame | None:
        '''
        Get recursively data on all merge requests for a project starting from specific date.
        Note: merge_at is a datetime of merge, merge_commit_sha is link to system commit of merge
        (details on page https://docs.gitlab.com/ee/api/merge_requests.html#list-project-merge-requests)
        '''
        is_next_page_exist, df = self._load_data(
            f"merge_requests?created_after={created_after}&state=all&per_page=100&page={page}")
        if df.empty:
            return None

        merge_req_ids = df['iid'].to_numpy()
        merge_req_df = df.loc[:, ['iid', 'created_at', 'merged_at', 'closed_at',
                                  'merge_commit_sha', 'source_branch']]
        merge_req_df.set_index('iid', inplace=True)
        merge_req_df['first_commit_date'] = ''
        merge_req_df['last_commit_date'] = ''
        for merge_req_id in merge_req_ids:
            merge_req_commits_df = self.get_associated_commits_to_merge_req(merge_req_id)
            if merge_req_commits_df.empty:
                print("empty df")
            else:
                commit_min_date = merge_req_commits_df['created_at'].min()
                commit_max_date = merge_req_commits_df['created_at'].max()
                merge_req_df.at[merge_req_id, 'first_commit_date'] = commit_min_date
                merge_req_df.at[merge_req_id, 'last_commit_date'] = commit_max_date
                merge_req_df['project_id'] = self.project_id
                merge_req_df = merge_req_df[['project_id', 'created_at', 'merged_at', 'closed_at',
                                             'merge_commit_sha', 'source_branch', 'first_commit_date',
                                             'last_commit_date']]
        if is_next_page_exist:
            next_merge_req_df = self.get_all_merge_requests_details(created_after, page=page + 1)
            merge_req_df = pd.concat([merge_req_df, next_merge_req_df], ignore_index=True)
            merge_req_df['project_id'] = self.project_id
            merge_req_df = merge_req_df[['project_id', 'created_at', 'merged_at', 'closed_at',
                                         'merge_commit_sha', 'source_branch', 'first_commit_date',
                                         'last_commit_date']]
        print('Merge requests data has been downloaded')
        return merge_req_df

    def get_repo_branches(self, page: int = 1) -> pd.DataFrame | None:
        '''
        Get recursively list of all repository branches for a project
        (details on page https://docs.gitlab.com/ee/api/branches.html)
        '''
        is_next_page_exist, df = self._load_data(f"repository/branches?page={page}")
        if df.empty:
            return None

        df['commit.committed_date'] = df['commit.committed_date'].map(
            lambda x: datetime.strptime(x[:10], '%Y-%m-%d'))
        df['lt'] = (datetime.today() - df['commit.committed_date']).dt.days
        df['branch_status'] = df['lt'].map(lambda x: "Active" if x < 90 else "Stale")
        if is_next_page_exist:
            next_branch_df = self.get_repo_branches(page=page + 1)
            df = pd.concat([df, next_branch_df], ignore_index=True)

        return df

    def get_commits_for_branches(self) -> pd.DataFrame:
        '''
        Get commits details for all branches in a project
        '''
        branch_df = self.get_repo_branches()
        if branch_df is None or branch_df.empty:
            logging.warning(f'No branches found for project {self.project_id}')
            return pd.DataFrame()

        count = 0
        branch_commits_details = pd.DataFrame(columns=['created_at', 'message', 'id',
                                                       'committed_date', 'authored_date', 'branch_name'])
        for branch in branch_df['name'].to_list():
            count += 1
            print(count)
            print(branch)
            df = self.get_commits_details_per_branch(branch)
            df['branch_name'] = branch
            branch_commits_details = pd.concat([branch_commits_details, df], ignore_index=True)

        committed_date = branch_commits_details['commit.committed_date']
        print(committed_date[0])
        return branch_commits_details

    def get_referenced_for_commit(self, commit_id: str) -> pd.DataFrame:
        '''
        Get references a commit is pushed to
        '''
        _, df = self._load_data(f"repository/commits/{commit_id}/refs?type=branch")
        return df
