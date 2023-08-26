import math
import os
from collections import abc
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from unstructured.ingest.interfaces import (
    BaseConnector,
    BaseConnectorConfig,
    BaseIngestDoc,
    ConnectorCleanupMixin,
    IngestDocCleanupMixin,
    StandardConnectorConfig,
)
from unstructured.ingest.logger import logger
from unstructured.utils import requires_dependencies


@dataclass
class SimpleJiraConfig(BaseConnectorConfig):
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
    list_of_paths: Optional[str]
    jql_query: Optional[str]


@dataclass
class JiraFileMeta:
    """Metadata specifying:
    project_id: id for the jira project that the issue locates in, and
    issue_key: key for the issue that is being reached to.
    """

    project_id: str
    issue_key: str
    issue_id: str


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

    #
    # def __missing__(self, key):
    #     new_defaultdict = self.__class__(self.default_factory)
    #     self[key] = new_defaultdict
    #     return new_defaultdict
    # def __repr__(self):
    #     return self.default_factory()


def get_fields_for_issue(issue, c_sep="|||", r_sep="\n\n\n"):
    issue_fields = nested_object_to_field_getter(issue["fields"])

    all_fields = r_sep.join(
        [
            _get_id_fields_for_issue(issue),
            _get_project_fields_for_issue(issue_fields),
            _get_dropdown_fields_for_issue(issue_fields),
            _get_subtasks_for_issue(issue_fields),
            _get_comments_for_issue(issue_fields),
            _get_text_fields_for_issue(issue_fields),
        ],
    )
    return all_fields


def _get_id_fields_for_issue(issue, c_sep="|||"):
    id, key = issue["id"], issue["key"]
    return f"{id}{c_sep}{key}"


def _get_project_fields_for_issue(issue, c_sep="|||", r_sep="\n\n\n"):
    if "project" in issue:
        return c_sep.join([issue["project"]["key"], issue["project"]["name"]])
    else:
        return ""


def _get_dropdown_fields_for_issue(issue, c_sep="|||", r_sep="==="):
    return f"""
    {issue["issuetype"]["name"]}
    {issue["status"]["name"]}
    {issue["priority"]}
    {issue["assignee"]["accountId"]}{c_sep}{issue["assignee"]["displayName"]}
    {issue["reporter"]["emailAddress"]}{c_sep}{issue["reporter"]["displayName"]}
    {c_sep.join(issue["labels"])}
    {c_sep.join([component["name"] for component in issue["components"]])}
    """


def _get_subtasks_for_issue(issue):
    return ""


def _get_text_fields_for_issue(issue, c_sep="|||", r_sep="\n\n\n"):
    return f"""
    {issue["summary"]}
    {issue["description"]}
    {c_sep.join([atch["self"] for atch in issue["attachment"]])}
    """


def _get_comments_for_issue(issue, c_sep="|||", r_sep="==="):
    return c_sep.join(
        [_get_fields_for_comment(comment) for comment in issue["comment"]["comments"]],
    )


def _get_fields_for_comment(comment, c_sep="|||"):
    return f"{comment['author']['displayName']}{c_sep}{comment['body']}"


def scroll_wrapper(func):
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
                all_results += func(*args, **kwargs)["results"]

            kwargs["start"] += kwargs["limit"]

        return all_results[:number_of_items_to_fetch]

    return wrapper


@dataclass
class JiraIngestDoc(IngestDocCleanupMixin, BaseIngestDoc):
    """Class encapsulating fetching a doc and writing processed results (but not
    doing the processing).

    Current implementation creates a Jira connection object
    to fetch each doc, rather than creating a it for each thread.
    """

    config: SimpleJiraConfig
    file_meta: JiraFileMeta

    @property
    def filename(self):
        return (
            Path(self.standard_config.download_dir)
            / self.file_meta.project_id
            / f"{self.file_meta.issue_id}.txt"
        ).resolve()

    @property
    def _output_filename(self):
        """Create output file path based on output directory, project id and issue key."""
        output_file = f"{self.file_meta.issue_id}.json"
        return Path(self.standard_config.output_dir) / self.file_meta.project_id / output_file

    @requires_dependencies(["atlassian"])
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        from atlassian import Jira

        logger.debug(f"Fetching {self} - PID: {os.getpid()}")

        # TODO: instead of having a separate connection object for each doc,
        # have a separate connection object for each process
        jira = Jira(
            self.config.url,
            username=self.config.user_email,
            password=self.config.api_token,
        )

        issue = jira.issue(self.file_meta.issue_key)
        print("\n\n\n\n\n\n", "DEBUG DEBUG DEBUG DEBUG DEBUG DEBUG", self.file_meta.issue_key)
        self.document = get_fields_for_issue(issue)
        self.filename.parent.mkdir(parents=True, exist_ok=True)

        debug_path = (
            Path("/Users/ahmet/Desktop/hi")
            / self.file_meta.project_id
            / f"{self.file_meta.issue_id}.txt"
        ).resolve()

        import json

        with open(debug_path, "w", encoding="utf8") as f:
            f.write(json.dumps(issue))

        with open(self.filename, "w", encoding="utf8") as f:
            f.write(self.document)


@requires_dependencies(["atlassian"])
@dataclass
class JiraConnector(ConnectorCleanupMixin, BaseConnector):
    """Fetches issues from projects in an Atlassian (Jira) Cloud instance."""

    config: SimpleJiraConfig

    def __init__(
        self,
        standard_config: StandardConnectorConfig,
        config: SimpleJiraConfig,
    ):
        super().__init__(standard_config, config)

    @requires_dependencies(["atlassian"])
    def initialize(self):
        from atlassian import Jira

        self.jira = Jira(
            url=self.config.url,
            username=self.config.user_email,
            password=self.config.api_token,
        )

    @requires_dependencies(["atlassian"])
    def _get_project_ids(self):
        """Fetches projects in a Jira domain."""
        project_ids = [project["key"] for project in self.jira.projects()]
        return project_ids

    @requires_dependencies(["atlassian"])
    def _get_issue_keys_within_one_project(
        self,
        project_id: str,
    ):
        get_issues_with_scroll = scroll_wrapper(self.jira.get_all_project_issues)
        results = get_issues_with_scroll(project=project_id, fields=["key"])

        return [(issue["key"], issue["id"]) for issue in results]

    @requires_dependencies(["atlassian"])
    def _get_issue_keys_within_projects(self):
        project_ids = self._get_project_ids()

        issue_keys_all = [
            self._get_issue_keys_within_one_project(project_id=id) for id in project_ids
        ]

        issue_keys_flattened = [
            (issue_key, issue_id)
            for issue_keys_project in issue_keys_all
            for issue_key, issue_id in issue_keys_project
        ]

        return issue_keys_flattened

    def get_ingest_docs(self):
        """Fetches all issues in a project."""
        issue_keys_and_ids = self._get_issue_keys_within_projects()
        return [
            JiraIngestDoc(
                self.standard_config,
                self.config,
                JiraFileMeta(
                    issue_id=issue_id,
                    issue_key=issue_key,
                    project_id=issue_key.split("-")[0],
                ),
            )
            for issue_key, issue_id in issue_keys_and_ids
        ]
