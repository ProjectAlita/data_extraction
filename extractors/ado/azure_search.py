"""Module to get a list of projects from ADO."""
import requests

from requests.exceptions import RequestException

import pandas as pd


pd.set_option('display.max_columns', None)


class AzureSearch:
    """Class to get ADO projects."""
    def __init__(self, organization: str, user: str, token: str = None):
        self.organization = organization
        self.user = user
        self.token = token

    def get_projects_list(self, skip: int = 0, skip_step: int = 200) -> pd.DataFrame:
        """
        Get all projects in the organization that the authenticated user has access to.
        Details on a page: https://docs.microsoft.com/en-us/rest/api/azure/devops/core/projects/list
        """
        next_page = True
        df_projects = pd.DataFrame(columns=['id', 'name', 'url'])
        while next_page:
            request_url = f"https://dev.azure.com/{self.organization}/_apis/projects?" \
                          f"$top=200&$skip={skip}&api-version=6.0"
            response = self.make_get_request(request_url)
            df_intermediate = self._convert_response_to_df(response)
            df_projects = pd.concat([df_projects, df_intermediate])
            next_page = response.headers.get('Link')
            skip += skip_step
        return df_projects

    def make_get_request(self, request_url: str) -> requests.Response:
        """Make a get request with or without authentication."""
        try:
            if self.token is None:
                return requests.get(request_url)  # pylint: disable=missing-timeout
            return requests.get(request_url, auth=(self.user, self.token))  # pylint: disable=missing-timeout
        except RequestException as err:
            print('The following exception occurred while executing a request:', err)
            print('Please check correctness of entered data and try again!')
            raise

    @staticmethod
    def _convert_response_to_df(response: requests.Response) -> pd.DataFrame:
        """Convert a response to an expected DataFrame."""
        data = response.json()['value']
        df_intermediate = pd.json_normalize(data)
        return df_intermediate[['id', 'name', 'url']]
