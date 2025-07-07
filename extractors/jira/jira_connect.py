"""
This module connects to Jira instance with user's credentials from config.yml,
gets projects list an authenticated user has access to and gets issues number for each project.
"""

import logging
from typing import Optional, Tuple
import pandas as pd
from jira import JIRA, JIRAError

from ..utils.read_config import JiraConfig, Config
# from ..aws.read_secret import SecretManagerRetrieve
# from ..azure.get_key_vault_secret import get_secret


_jira_instance : Optional[JIRA] = None


def connect_to_jira(
    jira_creds_storage: str = 'local',
    config_path: str = './conf/config.yml',
    credentials: Optional[dict] = None,
) -> Optional[JIRA]:
    """
    Connects to Jira using either passed-in credentials or stored in a local or remote location specified
    by the jira_creds_storage parameter.

    Args:
        jira_creds_storage (str): One of ['local', 'aws', 'azure']. Ignored if 'credentials' is provided.

        config_path (str): Path to the config file, used only when loading from file.

        credentials (dict): Optional dict with keys: 'username', 'api_key', 'base_url', 'verify_ssl', 'token'

        jira (JIRA): Optional JIRA instance. If provided, it will be returned without creating a new connection.

        Returns (JIRA): authenticated Jira client.
    """
    if credentials is not None:
        global _jira_instance # pylint: disable=global-statement
        if _jira_instance is not None:
            return _jira_instance

        _jira_instance = connect_with_credentials(credentials)
        return _jira_instance

    # if jira_creds_storage not in ['local', 'aws', 'azure']:
    #     raise ValueError('jira_creds_storage must be either "local", "aws" or "azure"')
    # credentials = get_jira_credentials(jira_creds_storage, config_path)
    jira_options = {'server': credentials['url']}
    # options = get_jira_options(jira_creds_storage, config_path)
    # if options:
    #     jira_options.update(options)
    try:
        jira = JIRA(options=jira_options, basic_auth=(credentials['username'], credentials['password']))
    except JIRAError:
        try:
            jira = JIRA(options=jira_options, token_auth=credentials['password'])
        except JIRAError as err:
            logging.error('Could not connect to Jira. Error: %s, %s', err.status_code, err.text)
            raise err
    return jira


def connect_with_credentials(creds: dict) -> Optional[JIRA]:
    """
    Connects to Jira using provided credentials.
    Args:
        creds: dict with keys: 'base_url', 'username' (email), 'token' or 'api_key, 'verify_ssl'
    Returns:
        JIRA client instance or None
    """
    username = creds.get("username")
    base_url = creds.get("base_url")

    if not username or not base_url:
        raise ValueError("Missing required fields: 'username' or 'base_url'")

    token = creds.get("token")
    api_key = creds.get("api_key")

    if token:
        auth = (username, token)
    elif api_key:
        auth = (username, api_key)
    else:
        raise ValueError(
            "No valid authentication method found (token or api_key required)"
        )

    jira_options = {"verify": creds.get("verify_ssl", True)}
    
    try:
        jira = JIRA(server=base_url, options=jira_options, basic_auth=auth)
        # Test the connection by making a simple API call
        try:
            jira.myself()
        except (JIRAError, Exception) as e:
            # Check if we got HTML response (authentication redirect)
            error_message = str(e)
            if 'Expecting value: line 1 column 1 (char 0)' in error_message:
                raise ValueError(
                    "JIRA authentication failed - received login page instead of API response. "
                    "Please check your connection on the JIRA site and verify your credentials (username/token). "
                    "You may need to log in to JIRA again and reconnect."
                ) from e
            raise
        return jira
    except Exception as e:
        logging.error('Could not connect to Jira. Error: %s', str(e))
        raise e


# def get_jira_credentials(jira_creds_storage: str = 'local', config_path: str = './conf/config.yml') -> dict:
#     """
#     Function to get jira credentials based on jira_creds_storage type.

#     Parameters:
#         jira_creds_storage: str
#             a type of storage to get jira credentials from.
#             default value is 'local'. other possible values are 'aws' and 'azure'.
#         config_path: str
#             a path to a configuration file.
#             default value is './conf/config.yml'.
#     Returns:
#         dict
#             a dictionary with jira credentials.
#     """
#     username, url, password = None, None, None
#     try:
#         if jira_creds_storage == 'local':
#             jira_creds = JiraConfig(config_path)
#             username, url, password = jira_creds.username, jira_creds.url, jira_creds.token_or_password

#         elif jira_creds_storage == 'aws':
#             url, username, password = get_jira_creds_from_aws(config_path)

#         elif jira_creds_storage == 'azure':
#             url, username, password = get_jira_creds_from_azure(config_path)

#         return {'username': username, 'url': url, 'password': password}
#     except KeyError as err:
#         logging.error('Could not find a key in the %s: %s', config_path, err)
#         raise err


# def get_jira_options(jira_creds_storage: str = 'local', config_path: str = './conf/config.yml') -> dict:
#     """
#     Function to get jira options based on jira_creds_storage type.

#     Parameters:
#         jira_creds_storage: str
#             a type of storage to get jira options from.
#             default value is 'local'. other possible values are 'aws' and 'azure'.
#         config_path: str
#             a path to a configuration file.
#             default value is './conf/config.yml'.
#     Returns:
#         dict
#             a dictionary with jira options.
#     """
#     try:
#         result = None
#         if jira_creds_storage == 'azure':
#             header_name, header_value = try_get_headers_from_azure(config_path)
#             if header_name:
#                 result = {'headers': {header_name: header_value}}

#         return result
#     e   xcept KeyError as err:
#         logging.error('Could not find a key in the %s: %s', config_path, err)
#         raise err


# def get_jira_creds_from_aws(config_path: str = './conf/config.yml') -> Tuple[str, str, str]:
#     """Get Jira credentials from AWS Secret Manager."""
#     aws_config = Config.read_config(config_path)['SecretsIds']
#     secret_id, region = aws_config['jira_credentials'], aws_config['region']
#     jira_secrets = SecretManagerRetrieve(secret_id, region)
#     return jira_secrets.get_jira_credentials()


# def get_jira_creds_from_azure(config_path: str = './conf/config.yml') -> Tuple[str, ...]:
#     """Get Jira credentials from AWS Secret Manager."""
#     key_vault_config = Config.read_config(config_path)['KeyVault']
#     key_vault_url = key_vault_config['key_vault_url']

#     jira_secrets = key_vault_config['jira_credentials']
#     secret_jira_url, secret_jira_user, secret_jira_token = jira_secrets['url'], jira_secrets['username'], \
#         jira_secrets['token_or_password']

#     return tuple(get_secret(key_vault_url, secret) for secret in [secret_jira_url, secret_jira_user, secret_jira_token])


# def try_get_headers_from_azure(config_path: str = './conf/config.yml') -> Tuple[str, ...]:
#     """Get Jira options from AWS Secret Manager."""
#     key_vault_config = Config.read_config(config_path)['KeyVault']
#     key_vault_url = key_vault_config['key_vault_url']

#     jira_secrets = key_vault_config['jira_credentials']
#     secret_header_name, secret_header_value = jira_secrets['header_name'], jira_secrets['header_value']

#     return tuple(get_secret(key_vault_url, secret) for secret in [secret_header_name, secret_header_value])


def connect_to_jira_and_print_projects(jira_creds_storage: str = 'local',
    config_path: str = './conf/config.yml',
    credentials: Optional[dict] = None, jira: Optional[JIRA] = None
) -> Optional[Tuple[JIRA, pd.DataFrame]]:
    """Get information on all projects in Jira you have access to (their number, keys and names)."""
    if jira is None:
        jira = connect_to_jira(jira_creds_storage, config_path, credentials)
    if not jira:
        logging.error('Failed to connect to Jira')
        return None

    logging.info('You have connected to Jira')
    df_prj = pd.DataFrame()
    projects = jira.projects()
    prj_keys = []
    prj_names = []
    prj_num = len(projects)
    if prj_num:
        logging.info('You have access to the next %s projects:', prj_num)
        for prj in projects:
            prj_keys += [prj.key]
            prj_names += [prj.name]
        prj_info = {'key': prj_keys, 'name': prj_names}
        df_prj = create_df_from_dict(prj_info)
    else:
        logging.info("You don't have access to any project")

    return jira, df_prj


def create_df_from_dict(prj_info: dict) -> pd.DataFrame:
    """Create a dataframe with extracted information and save results to CSV file."""
    df_prj = pd.DataFrame.from_dict(prj_info)
    df_prj.index = df_prj.index + 1
    return df_prj
