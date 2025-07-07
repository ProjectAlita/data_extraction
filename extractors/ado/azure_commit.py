"""Module to work with Azure DevOps' commits."""

import asyncio
import codecs
import os
import subprocess

from typing import Optional

import aiohttp
import pandas as pd

from ..ado.azure_base import AzureBase
from ..utils.constants import OUTPUT_FOLDER


class AzureDevOpsCommit(AzureBase):
    """Class to work with ADO commits."""
    async def get_commits_details(self, since_date: str, with_commit_size: bool) -> Optional[pd.DataFrame]:
        """Get commits details on a page:
        https://docs.microsoft.com/ru-ru/rest/api/azure/devops/git/commits/get-commits?view=azure-devops-rest-6.0#all-commits
        """
        repos = self.get_repos()
        self.df = self._get_commits(repos, since_date)
        if self.df.empty:
            return None
        self._filter_out_service_commits()
        self._update_df_columns()
        if with_commit_size:
            await self._add_commit_sizes()
        return self.df

    def _get_commits(self, repos: dict, since_date: str) -> pd.DataFrame:
        data = []
        for key, value in repos.items():
            next_page = True
            skip = 0
            while next_page:
                request_url = f"https://dev.azure.com/{self.organization}/{self.project_id}/_apis/git/" \
                              f"repositories/{key}/commits?$top=200&$skip={skip}" \
                              f"&searchCriteria.excludeDeletes=True" \
                              f"&searchCriteria.fromDate={since_date}" \
                              f"&api-version=6.0"
                req = self.make_get_request(request_url)
                data_one_repo = req.json()['value']
                for commit in data_one_repo:
                    commit['repos_name'] = value[0]
                data += data_one_repo
                next_page = req.headers.get('Link')
                skip += 200
        return pd.json_normalize(data)

    def _update_df_columns(self):
        self.df['created_at'] = None  # There is no such field in Azure, but there is in GitLab
        self.df['project_id'] = self.project_id
        self.df = self.df[['project_id', 'created_at', 'comment', 'commitId', 'committer.date',
                           'author.date', 'repos_name']]
        self.df.rename(columns={'comment': 'message',
                                'commitId': 'id',
                                'committer.date': 'committed_date',
                                'author.date': 'authored_date'},
                       inplace=True)

    async def _add_commit_sizes(self):
        async with aiohttp.ClientSession() as session:
            self.session = session
            tasks = self._generate_tasks()
            dicts = await asyncio.gather(*tasks)
        df_with_sizes = pd.DataFrame(dicts)
        self.df = pd.merge(self.df, df_with_sizes, on='id')

    def _generate_tasks(self) -> list:
        return [asyncio.create_task(self._get_commit_size(row)) for _, row in self.df.iterrows()]

    async def _get_commit_size(self, row: pd.Series):
        response = await self._make_async_request(row)
        return await self._transform_to_commit_size(response, row['id'])

    async def _make_async_request(self, row: pd.Series):
        request_url = (f'https://dev.azure.com/{self.organization}/{self.project_id}/_apis/git/repositories/'
                       f'{row["repos_name"]}/commits/{row["id"]}/changes?api-version=7.0')
        if self.token is None:
            return await self.session.get(request_url)
        return await self.session.get(request_url, auth=aiohttp.BasicAuth(self.user, self.token))

    @staticmethod
    async def _transform_to_commit_size(response: aiohttp.client, commit_id: str) -> dict:
        data = await response.json()
        return {'id': commit_id, 'commit_size': sum(data['changeCounts'].values())}

    async def get_commits_details_and_size(self, since_date):
        """Get commits details and sizes."""
        df_commits = await self.get_commits_details(since_date, with_commit_size=False)
        commits_size = []
        # Get info on commits size
        repos_name_lst = df_commits['repos_name'].drop_duplicates().to_list()
        for repo in repos_name_lst:
            commits_size_one_repo = self.run_shell(repo)
            commits_size += commits_size_one_repo

        commits_size_df = pd.DataFrame(commits_size, columns=['id', 'commit_size'])
        upper_bound = self.outliers(commits_size_df['commit_size'])
        df_commits_with_sizes = df_commits.merge(commits_size_df, on='id')
        df_commits_with_sizes['upperBound'] = upper_bound
        print("Commits data has been downloaded to the folder 'raw_data'")
        return df_commits_with_sizes

    @staticmethod
    def run_shell(repos: str) -> list[str]:
        """Get commits size using shell command diff. Repos should be cloned to the folder raw_data."""

        def extract_commits(path: str) -> list[str]:
            with codecs.open(path, "r", "utf_8_sig") as file:
                return [line.split(' ')[0] for line in file]

        def execute_cmd(cmd: str) -> tuple[bytes, bytes]:
            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
                out, err = process.communicate()
            return out, err

        def calcualte_commit_size(commit: bytes) -> Optional[int]:
            lst_numbers = [int(str_) for str_ in commit.decode('utf-8').split() if str_.isdigit()]
            if len(lst_numbers) == 2:
                return lst_numbers[1]
            if len(lst_numbers) == 3:
                return lst_numbers[1] + lst_numbers[2]
            return None

        try:
            os.chdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), OUTPUT_FOLDER + repos))
        except FileNotFoundError:
            print(f'Clone the repos "{repos}" first')
            return []
        os.system('git pull')
        os.system('git log --format=oneline > log.txt')  # Get actual list of commits
        commits_lst = extract_commits("../log.txt")
        bad_commits = []
        prev_commits_length = 0
        while prev_commits_length != len(commits_lst):
            commits_size_one_repos = []
            # Loop through commits list and get commits size
            for index, commit in enumerate(commits_lst):
                parent_commit, _ = execute_cmd(f'git log --pretty=%P -n 1 {commit}')
                if len(parent_commit) > 42:
                    continue
                if len(parent_commit) < 41:
                    cmd = f"git diff '4b825dc642cb6eb9a060e54bf8d69288fbee4904' {commits_lst[index]} --shortstat"
                else:
                    parent_commit = parent_commit.decode('utf-8')[:40]
                    cmd = f"git diff {commits_lst[index]} {parent_commit} --shortstat"

                out, err = execute_cmd(cmd)

                if 'bad object' in err.decode('utf-8'):
                    bad_commits.append(err.decode('utf-8')[18:58])

                one_commit_size = calcualte_commit_size(out)
                commits_size_one_repos.append([commits_lst[index], one_commit_size])

            prev_commits_length = len(commits_lst)
            commits_lst = [item for item in commits_lst if item not in bad_commits]

        return commits_size_one_repos

    @staticmethod
    def outliers(size):
        """Calculate upper bound."""
        quantile1 = size.quantile(0.25)
        quantile3 = size.quantile(0.75)
        return quantile3 + (1.5 * (quantile3 - quantile1))
