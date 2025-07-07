''' Module for searching and extracting data from GitLab. '''
from functools import wraps
from typing import Optional
import requests
import pandas as pd

from ..utils import exceptions as e
from ..utils.read_config import GitConfig
from ..git.gitlab import GitLabV4

CONFIG_PATH = './conf/config.yml'


def loop_projects(data: list[dict]) -> tuple[list, list]:
    '''
    Loop through projects and extract information about them.
    '''
    projects_ids = []
    projects_lst = []
    for prj in data:
        projects_id = prj['id']
        project_name = prj['name']
        description = prj['description']
        commits_num = None
        http_url_to_repo = prj['http_url_to_repo']
        web_url = prj['web_url']
        default_branch = None
        try:
            default_branch = prj['default_branch']
        except KeyError:
            pass
        try:
            commits_num = prj['statistics']['commit_count']
        except KeyError:
            pass
        projects_ids += [projects_id]
        projects_lst += [
            [projects_id, project_name, description, commits_num, http_url_to_repo, web_url, default_branch]]
    return projects_ids, projects_lst


def add_merge_req_info(func):
    '''
    Decorator to add merge request information to the project data.
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        instance = args[0]  # args[0] is 'self'
        url = instance.url
        token = instance.token
        if not url or not token:           
            git_config = GitConfig(CONFIG_PATH)
            url, token = git_config.url, git_config.token

        count_merge_req = []
        if not isinstance(result, pd.DataFrame) and not result:
            return None
        for prj in result['projects_id'].to_list():
            git_project = GitLabV4(url=url, project_id=prj, default_branch_name='master', token=token)
            count_merge_req += [git_project.get_merge_req_state_count()]
        merge_req_df = pd.DataFrame(count_merge_req)
        merge_req_df.columns = ['pull_req_opened', 'pull_req_closed', 'pull_req_merged', 'projects_id']
        projects = result.merge(merge_req_df, on='projects_id')
        projects['pull_req_total'] = projects['pull_req_merged'] + projects['pull_req_closed'] + projects[
            'pull_req_opened']
        projects = projects.sort_values(['pull_req_total'], ascending=False)
        return projects

    return wrapper


def add_branches_info(func):
    '''
    Decorator to add branches information to the project data.
    '''
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        instance = args[0]  # args[0] is 'self'
        url = instance.url
        token = instance.token
        if not url or not token:
            git_config = GitConfig(CONFIG_PATH)
            url, token = git_config.url, git_config.token

        branches_count = []
        if not isinstance(result, pd.DataFrame) and not result:
            return None
        for prj in result['projects_id'].to_list():
            git_project = GitLabV4(url=url, project_id=prj, default_branch_name='master', token=token)
            try:
                branches_df = git_project.get_repo_branches()
                if branches_df is not None:
                    branches_count_one_prj = {'Active': branches_df['branch_status'].to_list().count("Active"),
                                              'Stale': branches_df['branch_status'].to_list().count("Stale"),
                                              'projects_id': git_project.project_id}
                else:
                    branches_count_one_prj = {'Active': None, 'Stale': None, 'projects_id': git_project.project_id}
            except (e.NotFoundException, e.AbsentAccessToRepository):
                branches_count_one_prj = {'Active': None, 'Stale': None, 'projects_id': git_project.project_id}
            branches_count += [branches_count_one_prj]
        branches_count_df = pd.DataFrame(branches_count)
        projects = result.merge(branches_count_df, on='projects_id')
        return projects

    return wrapper


class GitLabV4Search:
    '''
    Class for searching and extracting data from GitLab
    '''
    def __init__(self, url: str, default_branch_name: str, token: Optional[str] = None):
        self.url = url
        self.default_branch_name = default_branch_name
        self.token = token

    def _load_data(self, url_suffix: str) -> tuple[bool, dict]:
        '''
        Makes GET request to load data from GitLab API.
        '''

        request_url = f"https://{self.url}/api/v4/{url_suffix}"
        headers = {"PRIVATE-TOKEN": f"{self.token}"} if self.token else {}
        req = requests.get(request_url, headers=headers)  # pylint: disable=missing-timeout
        if req.status_code == 404:
            raise e.NotFoundException(CONFIG_PATH)
        if req.status_code != 200:
            raise requests.exceptions.HTTPError(f"Request failed with status {req.status_code}")

        next_page = req.headers.get('X-Next-Page')
        is_next_page_exist = bool(next_page)
        data = req.json()
        return is_next_page_exist, data

    def projects_info(self, last_activity_after: str, page: int = 1) -> pd.DataFrame:
        '''
        Get information about GitLab projects.
        '''
        is_next_page_exist, data = self._load_data(f'projects?page={page}&per_page=100'
                                                   f'&simple=False&statistics=True'
                                                   f'&state=open&last_activity_after={last_activity_after}')
        _, projects_lst = loop_projects(data)
        projects = pd.DataFrame(projects_lst, columns=['projects_id', 'project_name', 'description', 'commits_num',
                                                       'http_url_to_repo', 'web_url', 'default_branch'])
        projects = projects.sort_values(by='commits_num', na_position='last', ascending=False)
        # By default, GET requests return 20 results at a time because the API results are paginated
        if is_next_page_exist:
            next_projects = self.projects_info(last_activity_after, page + 1)
            projects = pd.concat([projects, next_projects], ignore_index=True)
        return projects

    extended_project_info = add_merge_req_info(add_branches_info(projects_info))

    def single_project(self, prj_ids: list[int]) -> list[dict]:
        '''
        Get data about a single GitLab project.
        '''
        data_single_prj = []
        for key in prj_ids:
            _, data = self._load_data(f'projects/{key}?statistics=True')
            data_single_prj += [data]
        return data_single_prj

    def search_projects_one_key(self, key: str, page: int = 1) -> tuple[list, list]:
        '''
        Search recursively GitLab all projects by key.
        '''
        is_next_page_exist, data = self._load_data(f'search?page={page}&scope=projects&search={key}')
        projects_ids, projects_lst = loop_projects(data)
        if is_next_page_exist:
            next_project_ids, next_projects = self.search_projects_one_key(key, page + 1)
            projects_ids += next_project_ids
            projects_lst += next_projects
        return projects_ids, projects_lst

    def search_projects_many_keys(self,  keys: str) -> tuple[list, list]:
        '''
        Search GitLab all projects by keys.
        '''
        key_lst = keys.split(",")
        projects_ids_all = []
        projects_lst_all = []
        for key in key_lst:
            projects_ids, projects_lst = self.search_projects_one_key(key)
            projects_ids_all += projects_ids
            projects_lst_all += projects_lst
        return projects_ids_all, projects_lst_all

    def search_merge_req_one_key(self, key: str, page: int = 1) -> list[int]:
        '''
        Search recursively all merge requests by key.
        '''
        merge_req_lst = []
        is_next_page_exist, data = self._load_data(f'search?page={page}&scope=merge_requests&search={key}')
        for prj in data:
            projects_id = prj['project_id']
            if projects_id not in merge_req_lst:
                merge_req_lst += [projects_id]
        if is_next_page_exist:
            next_merge_req = self.search_merge_req_one_key(key, page + 1)
            merge_req_lst += next_merge_req
            merge_req_lst = list(set(merge_req_lst))
        return merge_req_lst

    def search_merge_req_many_keys(self, keys: str) -> list[int]:
        '''
        Search all merge requests by keys.
        '''
        key_lst = keys.split(",")
        merge_req_lst_all = []
        for key in key_lst:
            merge_req_lst = self.search_merge_req_one_key(key)
            merge_req_lst_all += merge_req_lst
        return merge_req_lst_all

    def search_commits(self, *args, page: int = 1) -> list[int]:
        '''
        Search recursively all commits by keys.
        Note: This method doesn't work for Epam GitLab.
        '''
        data_commits = []
        commits_lst = []
        for key in args:
            is_next_page_exist, data = self._load_data(f'search?scope=commits&search={key}')
            if is_next_page_exist:
                next_data = self.search_commits(page=page + 1)
                data += next_data
            data_commits += data
        for commit in data_commits:
            projects_id = commit['project_id']
            if projects_id not in commits_lst:
                commits_lst += [projects_id]
        return commits_lst

    @add_branches_info
    @add_merge_req_info
    def compile_search(self, keys: str) -> pd.DataFrame | None:
        '''
        Search and extract projects and merge requests data.
        '''
        projects_ids, projects_lst = self.search_projects_many_keys(keys)
        merge_req_lst = self.search_merge_req_many_keys(keys)
        diff = [i for i in merge_req_lst if i not in projects_ids]
        # Get info on projects from commits
        diff_prj_info = self.single_project(diff)
        if len(projects_lst) != 0 or len(merge_req_lst) != 0:
            _, projects_lst_add = loop_projects(diff_prj_info)
            projects_lst_all = projects_lst + projects_lst_add
            projects = pd.DataFrame(projects_lst_all,
                                    columns=['projects_id', 'project_name', 'description', 'commits_num',
                                             'http_url_to_repo', 'web_url', 'default_branch'])
            return projects

        print('No projects were found')
        return None
