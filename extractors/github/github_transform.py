"""Transformations for GitHub data."""
import logging
import pandas as pd


def add_pull_req_statistic_to_repos(df_repos: pd.DataFrame, df_pull_req: pd.DataFrame):
    """Add the number of open, closed and merged pull requests to the repositories DataFrame."""
    if df_pull_req.empty:
        return df_repos
    
    # Log column names for debugging
    logging.info(f"Columns in df_pull_req before renaming: {df_pull_req.columns.tolist()}")

    df_repos = df_repos.merge(df_pull_req.reset_index(), left_on='repository_id', right_on='project_id', how='left')
    df_repos = df_repos.rename(columns={
        'closed': 'pull_req_closed', 'merged': 'pull_req_merged', 'open': 'pull_req_open'})
    
    # Ensure the renamed columns exist, and fill missing columns with 0
    for col in ['pull_req_closed', 'pull_req_merged', 'pull_req_open']:
        if col not in df_repos.columns:
            logging.warning(f"Column {col} not found in df_repos. Initializing with 0.")
            df_repos[col] = 0
            
    df_repos['pull_req_total'] = (df_repos['pull_req_closed'] + df_repos['pull_req_merged'] +
                                  df_repos['pull_req_open'])

    # Drop columns only if they exist
    columns_to_drop = ['pushed_at', 'project_id', 'index']
    existing_columns = [col for col in columns_to_drop if col in df_repos.columns]
    df_repos = df_repos.drop(columns=existing_columns)

    return df_repos


def calculate_pull_req_statistic(df_pull_req: pd.DataFrame):
    """Calculates the number of open, closed and merged pull requests for each repository."""
    if df_pull_req.empty:
        return df_pull_req
    df_pull_req['req_state'] = df_pull_req.apply(lambda x: define_pull_req_state(x['merged_at'], x['closed_at']),
                                                 axis=1)
    df_result = pd.pivot_table(df_pull_req.reset_index(), values='index', index='project_id',
                               columns='req_state', aggfunc='count')
    df_result.columns.name = None
    return df_result


def define_pull_req_state(merged_date: str, closed_date: str) -> str:
    """Defines pull request state based on the dates."""
    if not pd.isna(closed_date) and not pd.isna(merged_date):
        status = 'merged'
    elif not pd.isna(closed_date) and pd.isna(merged_date):
        status = 'closed'
    else:
        status = 'open'
    return status
