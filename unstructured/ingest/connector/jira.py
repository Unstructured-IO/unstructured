import math
import os
import typing as t
from collections import abc
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from pathlib import Path

from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    BaseConnectorConfig,
    BaseIngestDoc,
    BaseSessionHandle,
    BaseSourceConnector,
    ConfigSessionHandleMixin,
    IngestDocCleanupMixin,
    IngestDocSessionHandleMixin,
    SourceConnectorCleanupMixin,
    SourceMetadata,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from atlassian import Jira


@dataclass
class JiraSessionHandle(BaseSessionHandle):
    service: "Jira"


@requires_dependencies(["atlassian"], extras="jira")
def create_jira_object(url, user_email, api_token):
    """
    Creates a jira object for interacting with Jira Cloud.
    Args:
        url: URL to Jira Cloud organization
        user_email: Email for the user with the permissions
        api_token: API Token, generated for the user

    Returns:
        Jira object
    """
    from atlassian import Jira

    jira = Jira(
        url,
        username=user_email,
        password=api_token,
    )

    response = jira.get_permissions("BROWSE_PROJECTS")
    permitted = response["permissions"]["BROWSE_PROJECTS"]["havePermission"]

    if permitted:
        return jira

    else:
        raise ValueError(
            """The user with the provided *user_email* and the *api_token*
                         is not permitted to browse projects for the jira organization
                         for the provided *url*. Try checking user_email, api_token,
                         and the url arguments.""",
        )


@dataclass
class SimpleJiraConfig(ConfigSessionHandleMixin, BaseConnectorConfig):
    """Connector config where:
    user_email is the email to authenticate into Atlassian (Jira) Cloud,
    api_token is the api token to authenticate into Atlassian (Jira) Cloud,
    url is the URL pointing to the Atlassian (Jira) Cloud instance,
    list_of_projects is a list of project that is aimed to be ingested.

    Check ...
    for more info on the api_token.
    """

    user_email: str
    api_token: str
    url: str
    projects: t.Optional[t.List[str]]
    boards: t.Optional[t.List[str]]
    issues: t.Optional[t.List[str]]

    def create_session_handle(
        self,
    ) -> JiraSessionHandle:
        service = create_jira_object(self.url, self.user_email, self.api_token)
        return JiraSessionHandle(service=service)


@dataclass
class JiraFileMeta:
    """Metadata specifying:
    project_id: id for the jira project that the issue locates in, and
    issue_key: key for the issue that is being reached to.
    """

    project_id: str
    board_id: t.Optional[str]
    issue_key: str
    issue_id: str


# An implementation to obtain nested-defaultdict functionality.
# Keys have default values in a recursive manner, allowing
# limitless templates to parse an api response object.
def nested_object_to_field_getter(object):
    if isinstance(object, abc.Mapping):
        new_object = {}
        for k, v in object.items():
            if isinstance(v, abc.Mapping):
                new_object[k] = FieldGetter(nested_object_to_field_getter(v))
            else:
                new_object[k] = v
        return FieldGetter(new_object)
    else:
        return object


class FieldGetter(dict):
    def __getitem__(self, key):
        value = super().__getitem__(key) if key in self else None
        if value is None:
            value = FieldGetter({})
        return value


def form_templated_string(issue, parsed_fields, c_sep="|||", r_sep="\n\n\n"):
    """Forms a template string via parsing the fields from the API response object on the issue
    The template string will be saved to the disk, and then will be processed by partition."""
    return r_sep.join(
        [
            _get_id_fields_for_issue(issue),
            _get_project_fields_for_issue(parsed_fields),
            _get_dropdown_fields_for_issue(parsed_fields),
            _get_subtasks_for_issue(parsed_fields),
            _get_comments_for_issue(parsed_fields),
            _get_text_fields_for_issue(parsed_fields),
        ],
    )


DEFAULT_C_SEP = " " * 5
DEFAULT_R_SEP = "\n"


def _get_id_fields_for_issue(issue, c_sep=DEFAULT_C_SEP, r_sep=DEFAULT_R_SEP):
    id, key = issue["id"], issue["key"]
    return f"IssueID_IssueKey:{id}{c_sep}{key}{r_sep}"


def _get_project_fields_for_issue(issue, c_sep=DEFAULT_C_SEP, r_sep=DEFAULT_R_SEP):
    if "project" in issue:
        return (
            f"""ProjectID_Key:{issue["project"]["key"]}{c_sep}{issue["project"]["name"]}{r_sep}"""
        )
    else:
        return ""


def _get_dropdown_fields_for_issue(issue, c_sep=DEFAULT_C_SEP, r_sep=DEFAULT_R_SEP):
    return f"""
    IssueType:{issue["issuetype"]["name"]}
    {r_sep}
    Status:{issue["status"]["name"]}
    {r_sep}
    Priority:{issue["priority"]}
    {r_sep}
    AssigneeID_Name:{issue["assignee"]["accountId"]}{c_sep}{issue["assignee"]["displayName"]}
    {r_sep}
    ReporterAdr_Name:{issue["reporter"]["emailAddress"]}{c_sep}{issue["reporter"]["displayName"]}
    {r_sep}
    Labels:{c_sep.join(issue["labels"])}
    {r_sep}
    Components:{c_sep.join([component["name"] for component in issue["components"]])}
    {r_sep}
    """


def _get_subtasks_for_issue(issue):
    return ""


def _get_text_fields_for_issue(issue, c_sep=DEFAULT_C_SEP, r_sep=DEFAULT_R_SEP):
    return f"""
    {issue["summary"]}
    {r_sep}
    {issue["description"]}
    {r_sep}
    {c_sep.join([atch["self"] for atch in issue["attachment"]])}
    {r_sep}
    """


def _get_comments_for_issue(issue, c_sep=DEFAULT_C_SEP, r_sep=DEFAULT_R_SEP):
    return c_sep.join(
        [_get_fields_for_comment(comment) for comment in issue["comment"]["comments"]],
    )


def _get_fields_for_comment(comment, c_sep=DEFAULT_C_SEP, r_sep=DEFAULT_R_SEP):
    return f"{comment['author']['displayName']}{c_sep}{comment['body']}{r_sep}"


def scroll_wrapper(func, results_key="results"):
    def wrapper(*args, **kwargs):
        """Wraps a function to obtain scroll functionality.
        Function needs to be able to accept 'start' and 'limit' arguments."""
        if "number_of_items_to_fetch" in kwargs:
            number_of_items_to_fetch = kwargs["number_of_items_to_fetch"]
            del kwargs["number_of_items_to_fetch"]
        else:
            number_of_items_to_fetch = 100

        kwargs["limit"] = min(100, number_of_items_to_fetch)
        kwargs["start"] = 0 if "start" not in kwargs else kwargs["start"]

        all_results = []
        num_iterations = math.ceil(number_of_items_to_fetch / kwargs["limit"])

        for _ in range(num_iterations):
            response = func(*args, **kwargs)
            if type(response) is list:
                all_results += func(*args, **kwargs)
            elif type(response) is dict:
                if results_key not in response:
                    raise KeyError(
                        "Response object has no known keys to \
                                   access the results, such as 'results' or 'values'.",
                    )
                all_results += func(*args, **kwargs)[results_key]
            kwargs["start"] += kwargs["limit"]

        return all_results[:number_of_items_to_fetch]

    return wrapper


@dataclass
class JiraIngestDoc(IngestDocSessionHandleMixin, IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing).

    Current implementation creates a Jira connection object
    to fetch each doc, rather than creating a it for each thread.
    """

    connector_config: SimpleJiraConfig
    file_meta: JiraFileMeta
    registry_name: str = "jira"

    @cached_property
    def record_locator(self):  # Values must be JSON-serializable
        """A dictionary with any data necessary to uniquely identify the document on
        the source system."""
        return {
            "base_url": self.connector_config.url,
            "issue_key": self.file_meta.issue_key,
        }

    @cached_property
    def issue(self):
        """Gets issue data"""
        jira = self.session_handle.service
        return jira.issue(self.file_meta.issue_key)

    @cached_property
    def parsed_fields(self):
        return nested_object_to_field_getter(self.issue["fields"])

    @property
    def grouping_folder_name(self):
        if self.file_meta.board_id:
            return self.file_meta.board_id
        else:
            return self.file_meta.project_id

    @property
    def filename(self):
        download_file = f"{self.file_meta.issue_id}.txt"

        return (
            Path(self.read_config.download_dir) / self.grouping_folder_name / download_file
        ).resolve()

    @property
    def _output_filename(self):
        """Create output file path."""
        output_file = f"{self.file_meta.issue_id}.json"

        return (
            Path(self.processor_config.output_dir) / self.grouping_folder_name / output_file
        ).resolve()

    @property
    def version(self) -> t.Optional[str]:
        return None

    def update_source_metadata(self, **kwargs) -> None:
        exists = bool(self.issue)
        if not exists:
            self.source_metadata = SourceMetadata(
                exists=exists,
            )
            return

        self.source_metadata = SourceMetadata(
            date_created=datetime.strptime(
                self.parsed_fields["created"],
                "%Y-%m-%dT%H:%M:%S.%f%z",
            ).isoformat(),
            date_modified=datetime.strptime(
                self.parsed_fields["updated"],
                "%Y-%m-%dT%H:%M:%S.%f%z",
            ).isoformat(),
            source_url=f"{self.connector_config.url}/browse/{self.file_meta.issue_key}",
            exists=exists,
        )

    @SourceConnectionError.wrap
    @requires_dependencies(["atlassian"], extras="jira")
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        logger.debug(f"Fetching {self} - PID: {os.getpid()}")

        document = form_templated_string(self.issue, self.parsed_fields)
        self.update_source_metadata()
        self.filename.parent.mkdir(parents=True, exist_ok=True)

        with open(self.filename, "w", encoding="utf8") as f:
            f.write(document)


@requires_dependencies(["atlassian"], extras="jira")
@dataclass
class JiraSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    """Fetches issues from projects in an Atlassian (Jira) Cloud instance."""

    connector_config: SimpleJiraConfig

    @requires_dependencies(["atlassian"], extras="jira")
    def initialize(self):
        self.jira = self.connector_config.create_session_handle().service

    @requires_dependencies(["atlassian"], extras="jira")
    def _get_all_project_ids(self):
        """Fetches ids for all projects in a Jira domain."""
        project_ids = [project["key"] for project in self.jira.projects()]
        return project_ids

    @requires_dependencies(["atlassian"], extras="jira")
    def _get_issues_within_one_project(
        self,
        project_id: str,
    ):
        get_issues_with_scroll = scroll_wrapper(self.jira.get_all_project_issues)
        results = get_issues_with_scroll(project=project_id, fields=["key"])

        return [(issue["key"], issue["id"], None) for issue in results]

    @requires_dependencies(["atlassian"], extras="jira")
    def _get_issue_keys_within_projects(self, project_ids: t.Optional[t.List[str]] = None):
        if project_ids is None:
            # for when a component list is provided, without any projects
            if bool(self.connector_config.boards or self.connector_config.issues):
                return []
            # for when no components are provided. all projects will be ingested
            else:
                return self._get_all_project_ids()

        # for when a component list is provided, including some projects
        issue_keys_all = [self._get_issues_within_one_project(project_id=id) for id in project_ids]

        issue_keys_flattened = [
            (issue_key, issue_id, None)
            for issue_keys_project in issue_keys_all
            for issue_key, issue_id, board_id in issue_keys_project
        ]

        return issue_keys_flattened

    def _get_issues_within_one_board(self, board_id: str):
        get_issues_with_scroll = scroll_wrapper(
            self.jira.get_issues_for_board,
            results_key="issues",
        )
        results = get_issues_with_scroll(board_id=board_id, fields=["key"], jql=None)

        return [(issue["key"], issue["id"], board_id) for issue in results]

    def _get_issue_keys_within_boards(self, board_ids):
        if board_ids is None:
            return []

        issue_keys_all = [self._get_issues_within_one_board(board_id=id) for id in board_ids]

        issue_keys_flattened = [
            (issue_key, issue_id, board_id)
            for issue_keys_board in issue_keys_all
            for issue_key, issue_id, board_id in issue_keys_board
        ]
        return issue_keys_flattened

    def get_issues_info(self, issues):
        issues_info = [self.jira.get_issue(issue, ["key", "id"]) for issue in issues]
        return [(info["key"], info["id"], None) for info in issues_info]

    def get_issue_keys_for_given_components(self):
        issues = []

        if self.connector_config.projects:
            issues += self._get_issue_keys_within_projects(self.connector_config.projects)
        if self.connector_config.boards:
            issues += self._get_issue_keys_within_boards(self.connector_config.boards)
        if self.connector_config.issues:
            issues += self.get_issues_info(self.connector_config.issues)

        return issues

    def get_ingest_docs(self):
        """Fetches all issues in a project."""
        if bool(
            self.connector_config.projects
            or self.connector_config.boards
            or self.connector_config.issues,
        ):
            issue_keys_and_ids = self.get_issue_keys_for_given_components()
        else:
            # gets all issue ids from all projects
            issue_keys_and_ids = self._get_issue_keys_within_projects()

        return [
            JiraIngestDoc(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                file_meta=JiraFileMeta(
                    issue_id=issue_id,
                    issue_key=issue_key,
                    project_id=issue_key.split("-")[0],
                    board_id=board_id,
                ),
            )
            for issue_key, issue_id, board_id in issue_keys_and_ids
        ]
