"""This module contains the GitHubBasic class used to interact with the GitHub API."""

import logging
import time

from urllib.parse import urlparse, parse_qs
from typing import Optional
from abc import ABC

import requests


class GitHubBase(ABC):  # pylint: disable=too-few-public-methods
    """
    An abstract class used to interact with the GitHub API.

    Attributes
    ----------
    owner : str
        The owner of the repository.
    token : str
        The token used to authenticate with the GitHub API.
    base_url : str
        The base URL for the GitHub API for the specified repository.
    """

    def __init__(self, owner, token):
        """
        Constructs all the necessary attributes for the GitHubGet object.

        Parameters
        ----------
        owner : str
            The owner of the repository.
        token : str
            The token used to authenticate with the GitHub API.
        """
        self.owner = owner
        self.token = token
        self.base_url = 'https://api.github.com'

    def _load_data(self, url_suffix: str, params: dict = None, per_page: int = 100) -> Optional[list | dict]:
        """Loads data from the GitHub API."""
        if params is None:
            params = {}
        page = 1
        data = []
        while True:
            url = f"{self.base_url}/{url_suffix}"
            headers = {'Authorization': f'Bearer {self.token}'}
            params['per_page'] = per_page
            params['page'] = page
            response = self._make_request(url, headers, params)

            # In some cases, there is only on object in json
            if not isinstance(response.json(), list):
                return response.json()

            data.extend(response.json())
            next_page = self._get_page_from_header(response)
            if not next_page:
                break
            page = next_page
        return data

    @staticmethod
    def _make_request(url: str, headers: dict, params: dict) -> requests.Response:
        """Makes a request to the GitHub API."""
        response = None
        while True:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as err:
                if 'X-RateLimit-Reset' in response.headers and response.status_code == 403:
                    reset_time = int(response.headers['X-RateLimit-Reset'])
                    sleep_time = max(0, reset_time - int(time.time()))
                    logging.info('Rate limit exceeded. Sleeping for %s seconds.', sleep_time)
                    time.sleep(sleep_time)
                else:
                    logging.error('Failed to load data from %s: %s', url, err)
                    raise err
        return response

    @staticmethod
    def _get_page_from_header(response: requests.Response) -> Optional[int]:
        """Extracts the next page number from the Link header of a GitHub API response."""
        link_header = response.headers.get('Link')
        next_page = None
        if link_header:
            links = link_header.split(', ')
            for link in links:
                if 'rel="next"' in link:
                    next_url = link[link.index('<')+1:link.index('>')]
                    next_page = parse_qs(urlparse(next_url).query).get('page')
                    if next_page:
                        next_page = int(next_page[0])
        return next_page
