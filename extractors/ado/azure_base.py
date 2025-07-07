"""This module contains the base class for Azure DevOps API."""
import requests

from ..ado.utils import repeat_request
from ..utils import exceptions


class AzureBase:
    """Base class for Azure DevOps API."""
    def __init__(self, organization, project_id, user, token=None):
        self.organization = organization
        self.project_id = project_id
        self.user = user
        self.token = token
        self.response_code_handler = exceptions.ResponseCodeHandler(project_id)
        self.session = requests.Session()
        self.df = None

    def get_repos(self):
        """Get all repositories.
        Details on a page:
        https://docs.microsoft.com/en-us/rest/api/azure/devops/git/repositories/list?view=azure-devops-rest-4.1
        """
        request_url = (f"https://dev.azure.com/{self.organization}/{self.project_id}/"
                       f"_apis/git/repositories?api - version = 6.0")
        response = self.make_get_request(request_url)
        data = response.json()['value']
        repos_dict = {}
        for repo in data:
            repos_dict[repo['id']] = [repo['name'], repo['remoteUrl']]
        return repos_dict

    @repeat_request(repeat_num=10)
    def make_get_request(self, request_url: str):
        """Make a GET request to Azure DevOps API."""
        kwargs = {}
        if self.token is not None:
            kwargs['auth'] = (self.user, self.token)
        try:
            response = self.session.get(request_url, **kwargs)
        except requests.exceptions.RequestException as err:
            print('Oops: something went wrong while sending GET request:', err)
            raise
        response.raise_for_status()
        return response

    def _filter_out_service_commits(self):
        self.df = self.df[~self.df['comment'].str.contains('^Merged PR [0-9]+: .*', regex=True)]
        self.df = self.df[~self.df['comment'].str.contains('^Merge pull request [0-9]+ from .*', regex=True)]
