import typing as t
from dataclasses import dataclass
from enum import Enum
from functools import reduce
from pathlib import Path

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import SourceConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseSessionHandle,
    BaseSingleIngestDoc,
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
    from hubspot import HubSpot

CONTENT_TAG = "content"


class HubSpotObjectTypes(Enum):
    CALLS = "calls"
    COMMUNICATIONS = "communications"
    EMAILS = "emails"
    NOTES = "notes"
    PRODUCTS = "products"
    TICKETS = "tickets"


@dataclass
class HubSpotSessionHandle(BaseSessionHandle):
    service: "HubSpot"


@dataclass
class HubSpotAccessConfig(AccessConfig):
    api_token: str = enhanced_field(repr=False, sensitive=True)


@dataclass
class SimpleHubSpotConfig(ConfigSessionHandleMixin, BaseConnectorConfig):
    access_config: HubSpotAccessConfig
    params: t.Optional[str] = None
    properties: t.Optional[dict] = None
    object_types: t.Optional[t.List[str]] = None
    custom_properties: t.Optional[t.Dict[str, t.List[str]]] = None

    @requires_dependencies(["hubspot"], extras="hubspot")
    def create_session_handle(self) -> HubSpotSessionHandle:
        from hubspot import HubSpot

        service = HubSpot(access_token=self.access_config.api_token)
        return HubSpotSessionHandle(service=service)


@dataclass
class HubSpotIngestDoc(IngestDocSessionHandleMixin, IngestDocCleanupMixin, BaseSingleIngestDoc):
    connector_config: SimpleHubSpotConfig
    object_id: str
    object_type: str
    content_properties: t.List[str]
    registry_name: str = "hubspot"

    def __post_init__(self):
        self._add_custom_properties()

    @property
    def filename(self):
        return (
            Path(self.read_config.download_dir)
            / f"{self.object_type}/{self.object_id}.txt"  # type: ignore
        ).resolve()

    @property
    def _output_filename(self):
        return (
            Path(self.processor_config.output_dir)
            / f"{self.object_type}/{self.object_id}.json"  # type: ignore
        ).resolve()

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:
        return {
            f"{self.registry_name}_id": self.object_id,
        }

    @property
    def version(self) -> t.Optional[str]:
        return None

    @property
    def source_url(self) -> t.Optional[str]:
        return None

    def _add_custom_properties(self):
        if (self.connector_config.custom_properties is not None) and (
            (cprops := self.connector_config.custom_properties.get(self.object_type)) is not None
        ):
            self.content_properties += cprops

    def _join_object_properties(self, obj) -> str:
        return "\n".join(
            [
                obj.properties[cprop]
                for cprop in self.content_properties
                if (obj.properties.get(cprop) is not None)
            ],
        )

    def _resolve_getter(self):
        method_path = ""
        if self.object_type in [
            HubSpotObjectTypes.CALLS.value,
            HubSpotObjectTypes.COMMUNICATIONS.value,
            HubSpotObjectTypes.EMAILS.value,
            HubSpotObjectTypes.NOTES.value,
        ]:
            method_path = f"crm.objects.{self.object_type}.basic_api.get_by_id"
        if self.object_type in [
            HubSpotObjectTypes.PRODUCTS.value,
            HubSpotObjectTypes.TICKETS.value,
        ]:
            method_path = f"crm.{self.object_type}.basic_api.get_by_id"

        method = reduce(getattr, method_path.split("."), self.session_handle.service)
        return method

    @requires_dependencies(["hubspot"], extras="hubspot")
    def _fetch_obj(self, check_only=False):
        from hubspot.crm.objects.exceptions import NotFoundException

        get_by_id_method = self._resolve_getter()
        try:
            response = get_by_id_method(
                self.object_id,
                properties=([] if check_only else self.content_properties),
            )
        except NotFoundException as e:
            logger.error(e)
            return None
        return response

    def update_source_metadata(self, **kwargs) -> None:
        obj = kwargs.get("object", self._fetch_obj(check_only=True))  # type: ignore
        if obj is None:
            self.source_metadata = SourceMetadata(
                exists=False,
            )
            return
        self.source_metadata = SourceMetadata(
            date_created=obj.created_at.isoformat(),
            date_modified=obj.updated_at.isoformat(),
            exists=True,
        )

    @SourceConnectionError.wrap
    @BaseSingleIngestDoc.skip_if_file_exists
    def get_file(self):
        obj = self._fetch_obj()
        if obj is None:
            raise ValueError(
                f"Failed to retrieve object {self.registry_name}",
                f"with ID {self.object_id}",
            )
        self.update_source_metadata(object=obj)
        output = self._join_object_properties(obj)
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(output)
        return


@dataclass
class HubSpotSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    connector_config: SimpleHubSpotConfig

    def initialize(self):
        self.hubspot = self.connector_config.create_session_handle().service

    def check_connection(self):
        return self.connector_config.create_session_handle().service

    @requires_dependencies(["hubspot"], extras="hubspot")
    def _list_objects(self, get_page_method, object_type: str, content_properties: t.List[str]):
        try:
            objects = get_page_method()
        except Exception as e:
            logger.error(e)
            logger.error(
                f"Failed to retrieve {object_type}, omitting processing...",
            )
            return []
        return [
            HubSpotIngestDoc(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                object_id=obj.id,
                object_type=object_type,
                content_properties=content_properties,
            )
            for obj in objects.results
        ]

    def _get_calls(self) -> t.List[HubSpotIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.objects.calls.basic_api.get_page,
            HubSpotObjectTypes.CALLS.value,
            ["hs_call_title", "hs_call_body"],
        )

    def _get_communications(self) -> t.List[HubSpotIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.objects.communications.basic_api.get_page,
            HubSpotObjectTypes.COMMUNICATIONS.value,
            ["hs_communication_body"],
        )

    def _get_emails(self) -> t.List[HubSpotIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.objects.emails.basic_api.get_page,
            HubSpotObjectTypes.EMAILS.value,
            ["hs_email_subject", "hs_email_text"],
        )

    def _get_notes(self) -> t.List[HubSpotIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.objects.notes.basic_api.get_page,
            HubSpotObjectTypes.NOTES.value,
            ["hs_note_body"],
        )

    def _get_products(self) -> t.List[HubSpotIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.products.basic_api.get_page,
            HubSpotObjectTypes.PRODUCTS.value,
            ["description"],
        )

    def _get_tickets(self) -> t.List[HubSpotIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.tickets.basic_api.get_page,
            HubSpotObjectTypes.TICKETS.value,
            ["subject", "content"],
        )

    def get_ingest_docs(self):
        obj_method_resolver = {
            HubSpotObjectTypes.CALLS.value: self._get_calls,
            HubSpotObjectTypes.COMMUNICATIONS.value: self._get_communications,
            HubSpotObjectTypes.EMAILS.value: self._get_emails,
            HubSpotObjectTypes.NOTES.value: self._get_notes,
            HubSpotObjectTypes.PRODUCTS.value: self._get_products,
            HubSpotObjectTypes.TICKETS.value: self._get_tickets,
        }

        if self.connector_config.object_types is not None:
            obj_method_resolver = {
                obj_name: obj_method_resolver.get(obj_name)  # type: ignore
                for obj_name in self.connector_config.object_types
            }

        ingest_docs: t.List[HubSpotIngestDoc] = []
        for obj_name, obj_method in obj_method_resolver.items():
            logger.info(f"Retrieving - {obj_name}")
            results: t.List[HubSpotIngestDoc] = obj_method()  # type: ignore
            ingest_docs += results  # type: ignore

        return ingest_docs
