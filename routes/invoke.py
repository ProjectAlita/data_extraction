#!/usr/bin/python3
# coding=utf-8

"""Tool Invocation Route"""

import uuid
import json
import flask
from pylon.core.tools import log, web

from ..extractors.jira.jira_connect import connect_to_jira
from ..extractors.ado.azure_search import AzureSearch
from ..extractors.git.git_search import GitLabV4Search

from ..extractors.github.github_org import GitHubGetOrgLvl



class Route:
    """
    Invocation route

    self here is Method class instance, which provides access to tool methods.
    
    """

    @web.route("/tools/<toolkit_name>/<tool_name>/invoke", methods=["POST"])
    async def invoke_route(self, toolkit_name, tool_name):
        """Handle tool invocation"""

        # Validate toolkit
        if toolkit_name not in ["JiraDataExtractorToolkit", "AdoDataExtractorToolkit", "GitLabDataExtractorToolkit", "GitHubDataExtractorToolkit"]:
            return {
                "errorCode": "404",
                "message": "Toolkit not found",
                "details": [f"Unknown toolkit: {toolkit_name}"],
            }, 404

        log.info(f"Invoking tool: {toolkit_name}:{tool_name}")

        # Get request data
        request_data = flask.request.json
        if not request_data or "parameters" not in request_data:
            return {
                "errorCode": "400",
                "message": "Missing parameters",
                "details": ["Request must include 'parameters' field"],
            }, 400

        toolkit_params = request_data.get("configuration", {}).get("parameters", {})
        tool_params = request_data.get("parameters", {})
        # Log toolkit params excluding sensitive credentials
        safe_toolkit_params = {k: v for k, v in toolkit_params.items()
                                    if k not in ["username", "token", "api_key"]}
        log.info(f"Toolkit parameters: {safe_toolkit_params}")
        log.info(f"Tool parameters: {tool_params}")
        
        try:
            if toolkit_name == "JiraDataExtractorToolkit":
                jira_credentials = {
                    "username": toolkit_params.get("username"),
                    "base_url": toolkit_params.get("base_url"),
                    "token": toolkit_params.get("token"),
                    "api_key": toolkit_params.get("api_key"),
                    "verify_ssl": toolkit_params.get("verify_ssl", True),
                }
                log.info(f"Initializing Jira instance with credentials: username={jira_credentials["username"]}, base_url={jira_credentials["base_url"]}")

                # Init Jira client
                if not jira_credentials["username"] or not jira_credentials["base_url"]:
                    log.info(f"Jira credentials are not provided: username: {jira_credentials['username']}, base_url: {jira_credentials['base_url']}")
                    raise ValueError("Jira username and base URL must be provided in the configuration.")

                jira = connect_to_jira(credentials=jira_credentials)

                if not jira:
                    return {
                        "errorCode": "400",
                        "message": "Invalid Jira configuration",
                        "details": ["Jira instance could not be initialized with provided parameters."],
                    }, 400

                log.info(f"Jira connection established successfully {jira}")

                toolkit_params_keys = [
                "project_keys", "defects_name", "closed_status", "closed_issues_based_on", "environment_field", "add_filter", "custom_fields"
                ]

                for key in toolkit_params_keys:
                    if key not in toolkit_params:
                        raise ValueError(f"Missing required toolkit parameter: {key}")
                    
                project_keys = tool_params.get("project_keys") or toolkit_params.get("project_keys", "")

                # Route to appropriate tool
                if tool_name == "get_number_of_all_issues":
                    after_date = tool_params.get("after_date")
                    if not after_date:
                        raise ValueError("Missing required parameter: 'after_date'")

                    result, message = self.get_number_of_all_issues(jira, after_date, project_keys)
                elif tool_name == "get_jira_issues":
                    required_params = ["resolved_after", "updated_after", "created_after"]

                    for param in required_params:
                        if param not in tool_params:
                            raise ValueError(f"Missing required parameter: {param}")

                    custom_fields = toolkit_params.get("custom_fields", {}) 
                    log.info(f"Custom fields for Jira issues: {custom_fields}")
                    
                    # Validate and set closed_issues_based_on
                    closed_issues_based_on_value = toolkit_params.get("closed_issues_based_on", 1)
                    if closed_issues_based_on_value in [1, '1']:
                        closed_issues_based_on = 1
                    elif closed_issues_based_on_value in [2, '2']:
                        closed_issues_based_on = 2
                    else:
                        raise ValueError("Invalid value for closed_issues_based_on. Expected 1 (based on status) or 2 (based on resolved date).")
                    
                    result, message = self.get_jira_issues(
                        jira,
                        project_keys,
                        closed_issues_based_on=closed_issues_based_on,
                        closed_status=toolkit_params["closed_status"],
                        defects_name=toolkit_params.get("defects_name", ""),
                        resolved_after=tool_params["resolved_after"],
                        updated_after=tool_params["updated_after"],
                        created_after=tool_params["created_after"],
                        custom_fields=custom_fields,
                        add_filter=toolkit_params.get("add_filter", "")
                    )
                else:
                    return {
                        "errorCode": "404",
                        "message": "Tool not found",
                        "details": [f"Unknown tool: {tool_name}"],
                    }, 404

            elif toolkit_name == "AdoDataExtractorToolkit":
                organization = toolkit_params.get("organization")
                username = toolkit_params.get("username")
                token = toolkit_params.get("token")

                if not organization or not username or not token:
                    raise ValueError("Organization, username, and token must be provided.")

                ado_search = AzureSearch(organization=organization, user=username, token=token)

                if not ado_search:
                    return {
                        "errorCode": "400",
                        "message": "Invalid Azure DevOps configuration",
                        "details": ["Azure DevOps instance could not be initialized with provided parameters."],
                    }, 400

                log.info(f"Azure DevOps connection established successfully {ado_search}")

                # Check required toolkit parameters
                toolkit_params_keys = [ "project_keys", "area" ]

                for key in toolkit_params_keys:
                    if key not in toolkit_params:
                        raise ValueError(f"Missing required toolkit parameter: {key}")

                area = toolkit_params.get("area", "")

                # Route to appropriate tool
                if tool_name == "get_project_list":
                    result, message = self.get_project_list(ado_search)
                elif tool_name == "get_work_items":
                    required_params = ["resolved_after", "updated_after", "created_after"]

                    for param in required_params:
                        if param not in tool_params:
                            raise ValueError(f"Missing required parameter: {param}")

                    project_keys = toolkit_params.get("project_keys") or tool_params.get("project_keys", "")

                    result, message = self.get_work_items(
                        ado_search,
                        tool_params["resolved_after"],
                        tool_params["updated_after"],
                        tool_params["created_after"],
                        project_keys=project_keys,
                        area=area
                    )
                elif tool_name == "get_commits":
                    required_params = ["since_date"]

                    for param in required_params:
                        if param not in tool_params:
                            raise ValueError(f"Missing required parameter: {param}")

                    project_keys = toolkit_params.get("project_keys") or tool_params.get("project_keys", "")

                    result, message = await self.get_commits(ado_search, tool_params["since_date"], project_keys=project_keys)
                elif tool_name == "get_merge_requests":
                    required_params = ["since_date"]

                    for param in required_params:
                        if param not in tool_params:
                            raise ValueError(f"Missing required parameter: {param}")

                    project_keys = toolkit_params.get("project_keys") or tool_params.get("project_keys", "")

                    result, message = self.get_merge_requests(ado_search, tool_params["since_date"], project_keys=project_keys)
                elif tool_name == "get_pipelines_runs":
                    required_params = ["since_date"]

                    for param in required_params:
                        if param not in tool_params:
                            raise ValueError(f"Missing required parameter: {param}")

                    project_keys = toolkit_params.get("project_keys") or tool_params.get("project_keys", "")

                    result, message = self.get_pipelines_runs(ado_search, project_keys=project_keys)
            elif toolkit_name == "GitLabDataExtractorToolkit":
                base_url = toolkit_params.get("url")
                token = toolkit_params.get("token")
                default_branch_name = toolkit_params.get("default_branch_name", "main")

                if not base_url or not token:
                    raise ValueError("GitLab base URL and token must be provided in the configuration.")
                
                # Initialize GitLab search client
                gitlab_search = GitLabV4Search(
                    url=base_url,
                    default_branch_name=default_branch_name,
                    token=token
                )

                if not gitlab_search:
                    return {
                        "errorCode": "400",
                        "message": "Invalid GitLab configuration",
                        "details": ["GitLab instance could not be initialized with provided parameters."],
                    }, 400

                log.info(f"GitLab connection established successfully {gitlab_search}")

                # Check required toolkit parameters
                toolkit_params_keys = ["jira_project_keys", "project_ids"]

                for key in toolkit_params_keys:
                    if key not in toolkit_params:
                        raise ValueError(f"Missing required toolkit parameter: {key}")

                project_ids = toolkit_params.get("project_ids", "")

                # Route to appropriate tool
                if tool_name == "get_gitlab_project_list":
                    date = tool_params.get("date")
                    if not date:
                        raise ValueError("Missing required parameter: 'date'")
                    result, message = self.get_gitlab_project_list(gitlab_search, date=date)
                elif tool_name == "get_gitlab_projects_that_in_jira":
                    jira_project_keys = toolkit_params.get("jira_project_keys") or tool_params.get("jira_project_keys", "")
                    if not jira_project_keys:
                        raise ValueError("Missing required parameter: 'jira_project_keys'")
                    result, message = self.get_gitlab_projects_that_in_jira(gitlab_search, jira_project_keys)
                elif tool_name == "get_gitlab_commits":
                    since_date = tool_params.get("since_date")
                    if not since_date:
                        raise ValueError("Missing required parameter: 'since_date'")
                    
                    project_ids = tool_params.get("project_ids") or toolkit_params.get("project_ids", "")
                    if not project_ids:
                        raise ValueError("Missing required parameter: 'project_ids'")

                    result, message = self.get_gitlab_commits(gitlab_search, since_date, project_ids)
                elif tool_name == "get_gitlab_merge_requests":
                    since_date = tool_params.get("since_date")
                    if not since_date:
                        raise ValueError("Missing required parameter: 'since_date'")
                    
                    project_ids = tool_params.get("project_ids") or toolkit_params.get("project_ids", "")

                    if not project_ids:
                        raise ValueError("Missing required parameter: 'project_ids'")

                    result, message = self.get_gitlab_merge_requests(gitlab_search, since_date, project_ids)
                else:
                    return {
                        "errorCode": "404",
                        "message": "Tool not found",
                        "details": [f"Unknown tool: {tool_name}"],
                    }, 404
            elif toolkit_name == "GitHubDataExtractorToolkit":
                owner = toolkit_params.get("owner")
                token = toolkit_params.get("token")

                if not owner or not token:
                    raise ValueError("GitHub owner and token must be provided.")

                github = GitHubGetOrgLvl(owner=owner, token=token)
                if not github:
                    return {
                        "errorCode": "400",
                        "message": "Invalid GitHub configuration",
                        "details": ["GitHub instance could not be initialized with provided parameters."],
                    }, 400
                
                log.info(f"GitHub connection established successfully {github}")
                
                repos = toolkit_params.get("repos", "") or tool_params.get("repos", "")

                # Route to appropriate tool
                if tool_name == "get_commits_from_repos":
                    since_after = tool_params.get("since_after")
                    if not since_after:
                        raise ValueError("Missing required parameter: 'since_after'")

                    result, message = self.get_commits_from_repos(github, since_after, repos)
                elif tool_name == "get_pull_requests_from_repos":
                    since_after = tool_params.get("since_after")
                    if not since_after:
                        raise ValueError("Missing required parameter: 'since_after'")

                    result, message = self.get_pull_requests_from_repos(github, since_after, repos)
                elif tool_name == "get_github_repository_list":
                    pushed_after = tool_params.get("pushed_after")
                    if not pushed_after:
                        raise ValueError("Missing required parameter: 'pushed_after'")

                    result, message = self.get_repositories(github, pushed_after)
                elif tool_name == "get_github_repository_list_extended":
                    pushed_after = tool_params.get("pushed_after")
                    if not pushed_after:
                        raise ValueError("Missing required parameter: 'pushed_after'")

                    result, message = self.get_repositories_extended_data(github,pushed_after)
                else:
                    return {
                        "errorCode": "404",
                        "message": "Tool not found",
                        "details": [f"Unknown tool: {tool_name}"],
                    }, 404
                   
            # For result_composition: "list_of_objects", return list with message and csv_data objects
            result_objects = [
                {
                    "object_type": "message",
                    "data": message
                }
            ]

            # Only add csv_data object if we have actual CSV data
            if result and result.strip():
                result_objects.append({
                    "object_type": "csv_data",
                    "data": result
                })

            response = {
                "invocation_id": str(uuid.uuid4()),
                "status": "Completed",
                "result": json.dumps(result_objects),  # JSON string as expected by provider_worker
                "result_type": "String",
            }

            return response

        except Exception as e:
            log.exception(f"Tool invocation failed: {toolkit_name}:{tool_name}")
            
            error_message = str(e)
            
            if toolkit_name == "JiraDataExtractorToolkit":
                # Check for JIRA field validation errors
                if "fields are not valid or do not exist in your JIRA instance" in error_message:
                    return {
                        "errorCode": "400",
                        "message": "Invalid JIRA Fields",
                        "details": [
                            error_message,
                            "Please verify the field names in your JIRA configuration.",
                            "You can find available fields in JIRA Administration > Issues > Custom fields."
                        ],
                    }, 400
                
                # Check for specific JIRA authentication failure
                if "JIRA authentication failed" in error_message:
                    return {
                        "errorCode": "401",
                        "message": "JIRA Authentication Failed",
                        "details": [
                            "JIRA authentication failed - received login page instead of API response.",
                            "Please check your credentials (username/token) and try reconnecting to JIRA.",
                            "Your JIRA session may have expired or the credentials may be invalid."
                        ],
                    }, 401
                
                # Check for JSON decode error (also indicates auth issues)
                if "Expecting value: line 1 column 1 (char 0)" in error_message:
                    return {
                        "errorCode": "401", 
                        "message": "JIRA Authentication Failed",
                        "details": [
                            "JIRA returned HTML instead of JSON, indicating authentication failure.",
                            "Please check your JIRA credentials and try reconnecting.",
                            "This usually happens when your JIRA session has expired."
                        ],
                    }, 401
            
            return {
                "errorCode": "500",
                "message": "Internal server error",
                "details": [str(e)],
            }, 500
