#!/usr/bin/python3
# coding=utf-8

""" Plugin Descriptor Route """

from pylon.core.tools import web


class Route:
    """ Descriptor route """

    @web.route("/descriptor")
    def descriptor_route(self):
        """ Return plugin descriptor """

        def _get_tool_metadata(bucket_name: str = "extracted_data") -> dict:
            """ Returns tool metadata for the toolkit """
            return {
                "result_composition": "list_of_objects",
                "result_objects": [
                    {
                        "object_type": "message",
                        "result_target": "response",
                        "result_encoding": "plain"
                    },
                    {
                        "object_type": "csv_data",
                        "result_target": "artifact",
                        "result_extension": "csv",
                        "result_encoding": "utf-8",
                        "result_bucket": bucket_name,
                    }
                ]
            }

        service_location_url = self.descriptor.config.get(
            "service_location_url", "http://127.0.0.1:8082"
        )
        #
        ui_location_url = self.descriptor.config.get(
            "ui_location_url", "http://127.0.0.1:8081"
        )
        config = self.runtime_config()
        if "service_location_url" not in config:
            config["service_location_url"] = service_location_url

        jira_parameters = {
            "username":   {"type": "String",  "required": True,  "description": "Jira username"},
            "base_url":   {"type": "URL",     "required": True,  "description": "Jira base URL"},
            # ??? Required: either token OR api_key (not both)
            "token":      {"type": "Secret",  "required": False,  "description": "Jira API token"},
            "api_key":    {"type": "Secret",  "required": False, "description": "Optional API key"},
            "verify_ssl": {"type": "Bool", "required": False, "default_value": True, "description": "Verify SSL certificate"},

            "project_keys": {"type": "String", "required": False, "description": "One or more project keys separated by comma.", "default_value": ""},
            # "team_field": {"type": "String", "required": False, "description": "Jira team field name for issues", "default_value": ""},
            "environment_field": {"type": "String", "required": False, "description": "Jira environment for issues", "default_value": ""},
            "defects_name": {"type": "String", "required": False, "description": "Jira defects name for issues", "default_value": ""},
            "closed_status": {"type": "String", "required": False, "description": "Jira status to consider issues as closed (required when closed_issues_based_on=1)", "default_value": ""},
            "closed_issues_based_on": {"type": "Integer", "required": False, "description": "Define whether issues can be thought as closed based on their status (1) or not empty resolved date (2).", "default_value": 1},
            "custom_fields": {"type": "JSON", "required": False, "description": "Custom fields to include in the issues data. Format: {\"field_name\": \"field_value\"}. Example: {\"customfield_10001\": \"value1\", \"customfield_10002\": \"value2\"}", "default_value": "{}"},
            "add_filter": {"type": "String", "required": False, "description": "Additional filter", "default_value": ""},
        }

        ado_parameters = {
            "organization": { "type": "String", "required": True, "description": "Azure DevOps organization name" },
            "username": { "type": "String", "required": True, "description": "Azure DevOps username" },
            "token": { "type": "Secret", "required": True, "description": "Azure DevOps personal access token."  },
            # Optional parameters
            "project_keys": { "type": "String", "required": False, "description": "Comma-separated project names. " },
            "area": { "type": "String", "required": False, "description": "Area path filter for work items." }
        }

        gitlab_parameters =  {
            "url": {"type": "URL", "required": True, "description": "GitLab base URL"},
            "token": {"type": "Secret", "required": True, "description": "GitLab API token"},
            # Optional parameters
            "project_ids": {"type": "String", "required": False, "description": "Comma-separated project IDs."},
            "jira_project_keys": {"type": "String", "required": False, "description": "Comma-separated Jira project keys to filter GitLab projects."},
            "default_branch_name": {"type": "String", "required": False, "description": "Default branch name to filter commits and merge requests.", "default_value": "main"},
        }

        github_parameters = {
            "owner": { "type": "String", "required": True, "description": "GitHub owner name" },
            "token": { "type": "Secret", "required": True, "description": "GitHub personal access token" },
            "repos": { "type": "String", "required": False, "description": "Comma-separated list of GitHub"}
        }

        jira_toolkit = {
            "name": "JiraDataExtractorToolkit",
            "description": "Plugin for data extraction from Jira",
            "toolkit_config": {
                "type": "JiraDataExtractor Configuration",
                "description": "Configuration for JiraDataExtractor.",
                "parameters": jira_parameters
            },
            "provided_tools": [
                {
                    "name": "get_number_of_all_issues",
                    "args_schema": {
                        "after_date": { "type": "String", "required": True, "description": "date after which issues are considered" },
                        "project_keys": { "type": "String", "required": False, "description": "one or more projects keys separated with comma" }
                    },
                    "description": "Get projects a user has access to and merge them with issues count.",
                    "tool_metadata": _get_tool_metadata("jira_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                },
                {
                    "name": "get_jira_issues",
                    "args_schema": {
                        "project_keys": { "type": "String", "required": False, "description": "one or more projects keys separated with comma" },
                        "resolved_after": { "type": "String", "required": True, "description": "Resolved after date in format 'YYYY-MM-DD'." },
                        "updated_after": { "type": "String", "required": True, "description": "Updated after date in format 'YYYY-MM-DD'." },
                        "created_after": { "type": "String", "required": True, "description": "Created after date in format 'YYYY-MM-DD'." }
                    },
                    "description": "Get Jira issues based on provided parameters.",
                    "tool_metadata": _get_tool_metadata("jira_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                }
            ],
            "toolkit_metadata": {}
        }

        ado_toolkit = {
            "name": "AdoDataExtractorToolkit",
            "description": "Plugin for data extraction from Azure DevOps",
            "toolkit_config": {
                "type": "AdoDataExtractor Configuration",
                "description": "Configuration for AdoDataExtractor.",
                "parameters": ado_parameters
            },
            "provided_tools": [
                {
                    "name": "get_project_list",
                    "args_schema": {},
                    "description": "Get projects a user has access to in Azure DevOps.",
                    "tool_metadata": _get_tool_metadata("ado_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                },
                {
                    "name": "get_work_items",
                    "args_schema": {
                        "resolved_after": { "type": "String", "required": True, "description": "Date filter for resolved items 'YYYY-MM-DD'." },
                        "updated_after": { "type": "String", "required": True, "description": "Date filter for updated items 'YYYY-MM-DD'." },
                        "created_after": { "type": "String", "required": True, "description": "Date filter for created items 'YYYY-MM-DD'." },
                        "project_keys": { "type": "String", "required": False, "description": "Comma-separated project names." },
                        "area": { "type": "String", "required": False, "description": ("Area path filter for work items. " "(Optional, leave empty to search all areas).") }
                    },
                    "description": "Get work items from multiple Azure DevOps projects.",
                    "tool_metadata": _get_tool_metadata("ado_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                },
                {
                    "name": "get_commits",
                    "args_schema": {
                        "since_date": { "type": "String", "required": True, "description": "Get commits after this date 'YYYY-MM-DD'." },
                        "project_keys": { "type": "String", "required": False, "description": "Comma-separated project names." },
                    },
                    "description": "Get commits from multiple Azure DevOps projects.",
                    "tool_metadata": _get_tool_metadata("ado_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                },
                {
                    "name": "get_merge_requests",
                    "args_schema": {
                        "since_date": { "type": "String", "required": True, "description": "Get merge requests after this date 'YYYY-MM-DD'." },
                        "project_keys": { "type": "String", "required": False, "description": "Comma-separated project names." }
                    },
                    "description": "Get merge requests from multiple Azure DevOps projects.",
                    "tool_metadata": _get_tool_metadata("ado_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                },
                {
                    "name": "get_pipelines_runs",
                    "args_schema": {
                        "since_date": { "type": "String", "required": False, "description": "Get pipeline runs after this date 'YYYY-MM-DD'." },
                        "project_keys": { "type": "String", "required": False, "description": "Comma-separated project names." }
                    },
                    "description": "Get pipeline runs from multiple Azure DevOps projects.",
                    "tool_metadata": _get_tool_metadata("ado_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                }
            ],
            "toolkit_metadata": {}
        }

        gitlab_toolkit = {  
            "name": "GitLabDataExtractorToolkit",
            "description": "Plugin for data extraction from GitLab",
            "toolkit_config": {
                "type": "GitLabDataExtractor Configuration",
                "description": "Configuration for GitLabDataExtractor.",
                "parameters": gitlab_parameters
            },
            "provided_tools": [
                {
                    "name": "get_gitlab_project_list",
                    "args_schema": {
                        "date": {"type": "String", "required": True, "description": "Filter projects by last activity date in 'YYYY-MM-DD' format."}
                    },
                    "description": "Get GitLab projects a user has access to.",
                    "tool_metadata": _get_tool_metadata(bucket_name="gitlab_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                },
                {
                   "name": "get_gitlab_projects_that_in_jira",
                   "args_schema": {
                       "jira_project_keys": {"type": "String", "required": True, "description": "Comma-separated Jira project keys to filter GitLab projects."}
                   },
                   "description": "Find GitLab projects that correspond to Jira projects by matching names.",
                   "tool_metadata": _get_tool_metadata(bucket_name="gitlab_data"),
                   "tool_result_type": "String",
                   "sync_invocation_supported": True,
                   "async_invocation_supported": False
                },
                {
                    "name": "get_gitlab_commits",
                    "args_schema": {
                        "project_ids": {"type": "String", "required": True, "description": "Comma-separated GitLab project IDs."},
                        "since_date": {"type": "String", "required": True, "description": "Get commits after this date 'YYYY-MM-DD'."}
                    },
                    "description": "Get commit data for specified GitLab projects.",
                    "tool_metadata": _get_tool_metadata(bucket_name="gitlab_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                },
                {
                    "name": "get_gitlab_merge_requests",
                    "args_schema": {
                        "project_ids": {"type": "String", "required": True, "description": "Comma-separated GitLab project IDs."},
                        "since_date": {"type": "String", "required": True, "description": "Get merge requests after this date 'YYYY-MM-DD'."}
                    },
                    "description": "Get merge requests from specified GitLab projects.",
                    "tool_metadata": _get_tool_metadata(bucket_name="gitlab_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                }
            ],
            # Metadata for the toolkit
            "toolkit_metadata": {}
        }

        github_toolkit = {
            "name": "GitHubDataExtractorToolkit",
            "description": "Plugin for data extraction from GitHub",
            "toolkit_config": {
                "type": "GitHubDataExtractor Configuration",
                "description": "Configuration for GitHubDataExtractor.",
                "parameters": github_parameters
            },
            "provided_tools": [
                {
                    "name": "get_commits_from_repos",
                    "args_schema": {
                        "since_after": {"type": "String", "required": True, "description": "Get commits after this date 'YYYY-MM-DD'."},
                        "repos": {"type": "String", "required": False, "description": "Comma-separated list of GitHub repository names e.g. 'repo1,repo2'"}
                    },
                    "description": "Extracts commit data from multiple GitHub repositories since the specified date.",
                    "tool_metadata": _get_tool_metadata(bucket_name="github_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                },
                {
                    "name": "get_pull_requests_from_repos",
                    "args_schema": {
                        "since_after": {"type": "String", "required": True, "description": "Get pull requests after this date 'YYYY-MM-DD'."},
                        "repos": {"type": "String", "required": False, "description": "Comma-separated list of GitHub repository names e.g. 'repo1,repo2'"}
                    },
                    "description": "Extracts pull request data from multiple GitHub repositories since the specified date.",
                    "tool_metadata": _get_tool_metadata(bucket_name="github_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                },
                {
                    "name": "get_github_repository_list",
                    "args_schema": {
                        "pushed_after": {"type": "String", "required": True, "description": "Get repositories pushed after this date 'YYYY-MM-DD'."}
                    },
                    "description": "Extracts a list of GitHub repositories that were pushed after the specified date.",
                    "tool_metadata": _get_tool_metadata(bucket_name="github_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                },
                {
                    "name": "get_github_repository_list_extended",
                    "args_schema": {
                        "pushed_after": {"type": "String", "required": True, "description": "Get repositories pushed after this date 'YYYY-MM-DD'."}
                    },
                    "description": "Extracts a list of GitHub repositories with extended data that were pushed after the specified date.",
                    "tool_metadata": _get_tool_metadata(bucket_name="github_data"),
                    "tool_result_type": "String",
                    "sync_invocation_supported": True,
                    "async_invocation_supported": False
                }
            ],
            # Metadata for the toolkit
            "toolkit_metadata": {}
        }

        descriptor = {
            "name": "DataExtractorServiceProvider",
            "service_location_url": config["service_location_url"],

            "configuration": {
                "name": "DataExtractorProvider",
                "provided_ui": [
                    {
                        "name": "DataExtractorUI",
                        "url": ui_location_url,
                        "options": {"pass_host_header": True}
                    }
                ],
            },
            "provided_toolkits": [
               jira_toolkit,
               ado_toolkit,
               gitlab_toolkit,
               github_toolkit
            ]
        }

        return descriptor
