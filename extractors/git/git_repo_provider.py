""" This module contains the GitRepo class and its subclasses. """
# pylint: disable=too-few-public-methods


class GitRepo():
    """Base GitRepo class"""
    def __init__(self):
        # This empty constructor allows the creation of GitRepo objects without any arguments
        pass


class GitLab(GitRepo):
    """Base GitLab class"""
    def __init__(self):
        pass


class GitHub(GitRepo):
    """Base GitHub class"""
    def __init__(self):
        pass


def get_repo(git_provider: str = 'gitlab'):
    """Return a GitRepo object based on the git_provider argument."""
    provider = None
    if git_provider == 'gitlab':
        provider = GitLab()
    return provider
