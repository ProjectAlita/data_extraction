# Data Extraction Plugin Documentation

## Overview
The data_extraction plugin is designed to extract data from various sources, including Jira, Azure DevOps (ADO), GitHub, and GitLab. It provides tools and configurations to streamline data extraction processes.

## How It Works & Key Concepts

### Architecture
This plugin follows a modular architecture that enables data extraction from multiple sources:

1. **Service Provider Model**: The plugin functions as a service provider, exposing a set of tools through a descriptor that defines the capabilities and parameters required for each tool.

2. **Toolkit Structure**: Tools are organized into toolkits (e.g., JiraDataExtractorToolkit, AdoDataExtractorToolkit) based on the data source they extract from.

3. **Request-Response Flow**:
   - Client applications make requests to specific tool endpoints
   - The plugin authenticates with the external service (Jira, ADO, etc.)
   - Data is extracted, transformed, and returned in a standardized format (usually CSV)

4. **Configuration Management**: The plugin uses a centralized configuration system (`config.yml`) to manage connections and settings.

### Key Components

1. **Extractors**: Core modules that handle the API communication with external services:
   - Each extractor specializes in a specific data source (e.g., `extractors/jira`, `extractors/ado`)
   - Extractors handle authentication, pagination, and error handling

2. **Descriptor**: The descriptor route (`routes/descriptor.py`) defines the public interface of the plugin:
   - Tool definitions (name, parameters, description)
   - Expected input schemas
   - Output formats

3. **Methods**: Business logic layer that processes requests:
   - Methods receive parameters from API routes
   - They invoke the appropriate extractors
   - Process and transform the extracted data

4. **Routes**: API endpoints that receive client requests:
   - `/descriptor`: Returns the plugin's capabilities
   - `/health`: Health check endpoint
   - `/invoke`: Entry point for tool invocation

5. **Utils**: Helper functions for common tasks like:
   - Input validation
   - Date conversion
   - Circuit breaking for API rate limits

### Data Flow

1. Client sends a request to invoke a specific tool (e.g., `get_jira_issues`)
2. The request parameters are validated
3. The appropriate method is called (e.g., `jira_tool_operations.py`)
4. The method uses extractors to fetch data from the external service
5. Data is processed, transformed, and formatted
6. Response is returned to the client as CSV data or message


## Usage
### Routes
The plugin provides the following API routes:

- `/health`: Returns the plugin's health status
- `/descriptor`: Returns the plugin's capabilities and configuration
- `/tools/<toolkit_name>/<tool_name>/invoke`: Main entry point for invoking tools
- `/tools/<toolkit_name>/<tool_name>/invocations/<invocation_id>`: Check the status of invocations

For detailed information on these routes, see the [API Routes](#api-routes) section.

### Tools
The plugin includes tools for:

- **Jira**: Extract issues, projects, and sprints.
- **ADO**: Extract work items, commits, and pipelines.
- **GitHub**: Extract repositories, commits, and pull requests.
- **GitLab**: Extract projects, commits, and merge requests.

## Development
### Folder Structure
- `extractors/`: Contains source-specific extractors (e.g., Jira, ADO, GitHub, GitLab).
  - `jira/`: Jira-specific extraction modules
  - `ado/`: Azure DevOps extraction modules
  - `github/`: GitHub extraction modules
  - `git/`: GitLab extraction modules
- `methods/`: Implements business logic for the API routes.
  - `jira_tool_operations.py`: Jira toolkit implementation
  - `ado_tool_operations.py`: Azure DevOps toolkit implementation
  - `github_tool_operations.py`: GitHub toolkit implementation
  - `gitlab_tool_operations.py`: GitLab toolkit implementation
- `routes/`: Defines API endpoints that clients can call.
  - `descriptor.py`: Provides plugin capabilities and tool definitions
  - `health.py`: Health check endpoint
  - `invoke.py`: Main entry point for tool invocation
  - `invocations.py`: Handles invocation status checking
- `utils/`: Utility functions and helpers for common tasks.

## Getting Started

### Prerequisites
- Python 3.8 or higher
- Access to one or more of the supported data sources (Jira, Azure DevOps, GitHub, GitLab)
- API tokens or credentials for the data sources you want to access

### Installation
1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure your data sources in `config.yml` (create this file if it doesn't exist):
   ```yaml
   jira:
     base_url: https://your-jira-instance.atlassian.net
     username: your-username
     token: your-api-token
   
   azure_devops:
     organization: your-organization
     username: your-username
     token: your-personal-access-token
   
   github:
     owner: your-github-username-or-org
     token: your-personal-access-token
   
   gitlab:
     url: https://gitlab.com
     token: your-api-token
   ```

### Running the Plugin
The plugin is designed to run as part of the Pylon framework. Ensure that the plugin is correctly registered in your Pylon installation.

For development or testing purposes, you can use the plugin's API directly:

1. Start your Pylon server
2. Access the plugin's descriptor at `/descriptor` to see available toolkits and tools
3. Use the `/tools/<toolkit_name>/<tool_name>/invoke` endpoint to extract data

## Toolkits and Tools Reference

This section provides detailed documentation for each toolkit and the tools it offers.

### Jira Toolkit (JiraDataExtractorToolkit)

The Jira toolkit provides tools for extracting data from Jira instances.

#### Configuration Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| username | String | Yes | Jira username |
| base_url | URL | Yes | Jira base URL |
| token | Secret | No | Jira API token |
| api_key | Secret | No | Optional API key (either token OR api_key is required) |
| verify_ssl | Bool | No | Verify SSL certificate (default: true) |
| project_keys | String | No | One or more project keys separated by comma |
| environment_field | String | No | Jira environment for issues |
| defects_name | String | No | Jira defects name for issues |
| closed_status | String | No | Jira status to consider issues as closed |
| closed_issues_based_on | Integer | No | Define whether issues can be thought as closed based on their status (1) or not empty resolved date (2) (default: 1) |
| custom_fields | JSON | No | Custom fields to include in the issues data |
| add_filter | String | No | Additional filter |

#### Tools

1. **get_number_of_all_issues**
   - **Description**: Get projects a user has access to and merge them with issues count.
   - **Parameters**:
     - `after_date`: Date after which issues are considered (required)
     - `project_keys`: One or more project keys separated with comma (optional)

2. **get_jira_issues**
   - **Description**: Get Jira issues based on provided parameters.
   - **Parameters**:
     - `project_keys`: One or more project keys separated with comma (optional)
     - `resolved_after`: Resolved after date in format 'YYYY-MM-DD' (required)
     - `updated_after`: Updated after date in format 'YYYY-MM-DD' (required)
     - `created_after`: Created after date in format 'YYYY-MM-DD' (required)

### Azure DevOps Toolkit (AdoDataExtractorToolkit)

The ADO toolkit provides tools for extracting data from Azure DevOps.

#### Configuration Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| organization | String | Yes | Azure DevOps organization name |
| username | String | Yes | Azure DevOps username |
| token | Secret | Yes | Azure DevOps personal access token |
| project_keys | String | No | Comma-separated project names |
| area | String | No | Area path filter for work items |

#### Tools

1. **get_project_list**
   - **Description**: Get projects a user has access to in Azure DevOps.
   - **Parameters**: None

2. **get_work_items**
   - **Description**: Get work items from multiple Azure DevOps projects.
   - **Parameters**:
     - `resolved_after`: Date filter for resolved items 'YYYY-MM-DD' (required)
     - `updated_after`: Date filter for updated items 'YYYY-MM-DD' (required)
     - `created_after`: Date filter for created items 'YYYY-MM-DD' (required)
     - `project_keys`: Comma-separated project names (optional)
     - `area`: Area path filter for work items (optional)

3. **get_commits**
   - **Description**: Get commits from multiple Azure DevOps projects.
   - **Parameters**:
     - `since_date`: Get commits after this date 'YYYY-MM-DD' (required)
     - `project_keys`: Comma-separated project names (optional)

4. **get_merge_requests**
   - **Description**: Get merge requests from multiple Azure DevOps projects.
   - **Parameters**:
     - `since_date`: Get merge requests after this date 'YYYY-MM-DD' (required)
     - `project_keys`: Comma-separated project names (optional)

5. **get_pipelines_runs**
   - **Description**: Get pipeline runs from multiple Azure DevOps projects.
   - **Parameters**:
     - `project_keys`: Comma-separated project names (optional)

### GitLab Toolkit (GitLabDataExtractorToolkit)

The GitLab toolkit provides tools for extracting data from GitLab instances.

#### Configuration Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | URL | Yes | GitLab base URL |
| token | Secret | Yes | GitLab API token |
| project_ids | String | No | Comma-separated project IDs |
| jira_project_keys | String | No | Comma-separated Jira project keys to filter GitLab projects |
| default_branch_name | String | No | Default branch name to filter commits and merge requests (default: main) |

#### Tools

1. **get_gitlab_project_list**
   - **Description**: Get GitLab projects a user has access to.
   - **Parameters**:
     - `date`: Filter projects by last activity date in 'YYYY-MM-DD' format (required)

2. **get_gitlab_projects_that_in_jira**
   - **Description**: Find GitLab projects that correspond to Jira projects by matching names.
   - **Parameters**:
     - `jira_project_keys`: Comma-separated Jira project keys to filter GitLab projects (required)

3. **get_gitlab_commits**
   - **Description**: Get commit data for specified GitLab projects.
   - **Parameters**:
     - `project_ids`: Comma-separated GitLab project IDs (required)
     - `since_date`: Get commits after this date 'YYYY-MM-DD' (required)

4. **get_gitlab_merge_requests**
   - **Description**: Get merge requests from specified GitLab projects.
   - **Parameters**:
     - `project_ids`: Comma-separated GitLab project IDs (required)
     - `since_date`: Get merge requests after this date 'YYYY-MM-DD' (required)

### GitHub Toolkit (GitHubDataExtractorToolkit)

The GitHub toolkit provides tools for extracting data from GitHub repositories.

#### Configuration Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| owner | String | Yes | GitHub owner name |
| token | Secret | Yes | GitHub personal access token |
| repos | String | No | Comma-separated list of GitHub repositories |

#### Tools

1. **get_commits_from_repos**
   - **Description**: Extracts commit data from multiple GitHub repositories since the specified date.
   - **Parameters**:
     - `since_after`: Get commits after this date 'YYYY-MM-DD' (required)
     - `repos`: Comma-separated list of GitHub repository names e.g. 'repo1,repo2' (optional)

2. **get_pull_requests_from_repos**
   - **Description**: Extracts pull request data from multiple GitHub repositories since the specified date.
   - **Parameters**:
     - `since_after`: Get pull requests after this date 'YYYY-MM-DD' (required)
     - `repos`: Comma-separated list of GitHub repository names e.g. 'repo1,repo2' (optional)

3. **get_github_repository_list**
   - **Description**: Extracts a list of GitHub repositories that were pushed after the specified date.
   - **Parameters**:
     - `pushed_after`: Get repositories pushed after this date 'YYYY-MM-DD' (required)

4. **get_github_repository_list_extended**
   - **Description**: Extracts a list of GitHub repositories with extended data that were pushed after the specified date.
   - **Parameters**:
     - `pushed_after`: Get repositories pushed after this date 'YYYY-MM-DD' (required)


## API Routes

The Data Extraction plugin exposes several API endpoints that enable interaction with the plugin's functionality. These endpoints handle configuration retrieval, tool invocation, and health monitoring.

### Available Routes

1. **Descriptor Route**
   - **Endpoint**: `/descriptor`
   - **Method**: GET
   - **Description**: Returns the plugin descriptor which includes detailed information about the available toolkits, tools, input parameters, and output formats.
   - **Response**: JSON object containing the plugin's capabilities and configuration.
   - **Usage**: Use this endpoint to discover what tools are available and what parameters they require.

2. **Health Check Route**
   - **Endpoint**: `/health`
   - **Method**: GET
   - **Description**: Returns the health status of the plugin.
   - **Response**: JSON object with the following fields:
     - `status`: "UP" if the plugin is running normally, "DOWN" if there's an issue
     - `providerVersion`: Plugin version
     - `uptime`: Time in seconds since the plugin started
     - `timestamp`: Current UTC time
     - `plugin`: "DataExtractor"
     - `configuration`: Current runtime configuration
     - `extra_info`: Additional health information (if any)
   - **Usage**: Use this endpoint for monitoring and alerting.

3. **Tool Invocation Route**
   - **Endpoint**: `/tools/<toolkit_name>/<tool_name>/invoke`
   - **Method**: POST
   - **Description**: Invokes a specific tool from a toolkit with the provided parameters.
   - **Path Parameters**:
     - `toolkit_name`: Name of the toolkit (e.g., "JiraDataExtractorToolkit")
     - `tool_name`: Name of the tool (e.g., "get_jira_issues")
   - **Request Body**:
     ```json
     {
       "configuration": {
         "parameters": {
           // Toolkit-specific configuration parameters
         }
       },
       "parameters": {
         // Tool-specific parameters
       }
     }
     ```
   - **Response**: Tool-specific data, typically in CSV format or JSON format.
   - **Usage**: This is the main endpoint for extracting data from the various supported systems.
   - **Supported Toolkits**:
     - JiraDataExtractorToolkit
     - AdoDataExtractorToolkit
     - GitLabDataExtractorToolkit
     - GitHubDataExtractorToolkit

4. **Invocation Status Route**
   - **Endpoint**: `/tools/<toolkit_name>/<tool_name>/invocations/<invocation_id>`
   - **Methods**: GET, DELETE
   - **Description**: 
     - GET: Retrieve the status of a previously initiated tool invocation
     - DELETE: Cancel a running invocation (if supported)
   - **Path Parameters**:
     - `toolkit_name`: Name of the toolkit
     - `tool_name`: Name of the tool
     - `invocation_id`: ID of the invocation to check or cancel
   - **Response**: 
     - GET: JSON object with invocation status information
     - DELETE: Confirmation message or error if cancellation is not supported
   - **Usage**: For asynchronous operations, use this endpoint to check the status of long-running extractions.

### Making API Requests

Here's an example of how to invoke a tool using curl:

```bash
curl -X POST http://your-server/tools/JiraDataExtractorToolkit/get_jira_issues/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "configuration": {
      "parameters": {
        "username": "your-username",
        "base_url": "https://your-jira-instance.atlassian.net",
        "token": "your-api-token"
      }
    },
    "parameters": {
      "project_keys": "PROJECT",
      "since_date": "2023-01-01"
    }
  }'
```

### Error Handling

API endpoints return standard HTTP status codes:

- **200 OK**: Request succeeded
- **400 Bad Request**: Invalid parameters or request format
- **401 Unauthorized**: Authentication failed
- **404 Not Found**: Toolkit or tool not found
- **500 Internal Server Error**: Server-side error occurred

Error responses include a JSON object with:
- `errorCode`: Error code
- `message`: Brief error description
- `details`: Array of detailed error information

## Configuration

### Plugin Configuration

The plugin's behavior can be configured through the `config.yml` file:

```yaml
# Base path for storing extracted data
base_path: /data/dataextractor

# Optional: Override service location URL
service_location_url: http://127.0.0.1:8080

# Optional: Override UI location URL
ui_location_url: http://127.0.0.1:8080

# Optional: Tool version
tool_version: 1.0.0
```

### Environment Variables

Configuration values can reference environment variables using the `${VAR_NAME}` or `${VAR_NAME:default}` syntax:

```yaml
# Use environment variable with default value
base_path: ${DATA_PATH:/tmp/dataextractor}

# Use required environment variable (will raise error if not set)
service_location_url: ${SERVICE_URL}
```

### Plugin Metadata

The plugin's metadata is defined in `metadata.json`:

```json
{
  "name": "Host for tools: DataExtraction",
  "version": "1.0.0",
  "description": "Plugin for data extraction from Jira, ADO, GitHub, and GitLab.",
  "depends_on": [],
  "init_after": []
}
```

This metadata defines the plugin's name, version, and dependencies within the Pylon framework.



## License
This plugin is licensed under the MIT License. See the `LICENSE` file for details.

## Based On
This project was created based on the [Integration Template](https://github.com/ProjectAlita/integration-template) repository.