import typing as t
from dataclasses import dataclass, field
from enum import Enum
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
class SimpleHubSpotConfig(ConfigSessionHandleMixin, BaseConnectorConfig):
    api_token: str = field(repr=False)
    params: t.Optional[str] = None
    properties: t.Optional[dict] = None
    object_types: t.Optional[t.List[str]] = None
    custom_properties: t.Optional[t.Dict[str, t.List[str]]] = None

    @requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def create_session_handle(self) -> HubSpotSessionHandle:
        from hubspot import HubSpot

        service = HubSpot(access_token=self.api_token)
        return HubSpotSessionHandle(service=service)


@dataclass
class HubSpotIngestDoc(IngestDocSessionHandleMixin, IngestDocCleanupMixin, BaseIngestDoc):
    connector_config: SimpleHubSpotConfig
    object_id: str
    content_properties: t.List[str] = field(init=False)
    registry_name: str

    @property
    def filename(self):
        return (
            Path(self.read_config.download_dir)
            / f"{self.registry_name}/{self.object_id}.txt"  # type: ignore
        ).resolve()

    @property
    def _output_filename(self):
        return (
            Path(self.processor_config.output_dir)
            / f"{self.registry_name}/{self.object_id}.json"  # type: ignore
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

    def _fetch_obj(self, get_by_id_method, not_found_exception, **kwargs):
        try:
            response = get_by_id_method(self.object_id, **kwargs)
        except not_found_exception as e:
            logger.error(e)
            return None
        return response

    def _add_custom_properties(self, obj_type):
        if (self.connector_config.custom_properties is not None) and (
            (cprops := self.connector_config.custom_properties.get(obj_type)) is not None
        ):
            self.content_properties += cprops

    def update_source_metadata(self, **kwargs) -> None:
        obj = kwargs.get("object", self.get_object())  # type: ignore
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

    def _join_object_properties(self, obj) -> str:
        return "\n".join(
            [
                obj.properties[cprop]
                for cprop in self.content_properties
                if (obj.properties.get(cprop) is not None)
            ],
        )


@dataclass
class HubSpotCallIngestDoc(HubSpotIngestDoc):
    connector_config: SimpleHubSpotConfig
    registry_name: str = "hubspot_call"

    def __post_init__(self):
        self.content_properties = ["hs_call_title", "hs_call_body"]
        self._add_custom_properties(HubSpotObjectTypes.CALLS.value)

    @requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def get_object(self):
        from hubspot.crm.objects.calls.exceptions import NotFoundException

        method = self.session_handle.service.crm.objects.calls.basic_api.get_by_id
        return self._fetch_obj(
            method,
            NotFoundException,
            properties=self.content_properties,
        )

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        call = self.get_object()
        self.update_source_metadata(object=call)
        output = self._join_object_properties(call)
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(output)
        return


@dataclass
class HubSpotCommunicationIngestDoc(HubSpotIngestDoc):
    connector_config: SimpleHubSpotConfig
    registry_name: str = "hubspot_communication"

    def __post_init__(self):
        self.content_properties = ["hs_communication_body"]
        self._add_custom_properties(HubSpotObjectTypes.COMMUNICATIONS.value)

    @requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def get_object(self):
        from hubspot.crm.objects.communications.exceptions import NotFoundException

        method = self.session_handle.service.crm.objects.communications.basic_api.get_by_id
        return self._fetch_obj(method, NotFoundException, properties=["hs_communication_body"])

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        communication = self.get_object()
        self.update_source_metadata(object=communication)
        output = self._join_object_properties(communication)
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(output)
        return


@dataclass
class HubSpotEmailIngestDoc(HubSpotIngestDoc):
    connector_config: SimpleHubSpotConfig
    registry_name: str = "hubspot_email"

    def __post_init__(self):
        self.content_properties = ["hs_email_subject", "hs_email_text"]
        self._add_custom_properties(HubSpotObjectTypes.EMAILS.value)

    @requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def get_object(self):
        from hubspot.crm.objects.emails.exceptions import NotFoundException

        method = self.session_handle.service.crm.objects.emails.basic_api.get_by_id
        return self._fetch_obj(
            method,
            NotFoundException,
            properties=["hs_email_subject", "hs_email_text"],
        )

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        email = self.get_object()
        self.update_source_metadata(object=email)
        output = self._join_object_properties(email)
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(output)
        return


@dataclass
class HubSpotNotesIngestDoc(HubSpotIngestDoc):
    connector_config: SimpleHubSpotConfig
    registry_name: str = "hubspot_note"

    def __post_init__(self):
        self.content_properties = ["hs_note_body"]
        self._add_custom_properties(HubSpotObjectTypes.NOTES.value)

    @requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def get_object(self):
        from hubspot.crm.objects.notes.exceptions import NotFoundException

        method = self.session_handle.service.crm.objects.notes.basic_api.get_by_id
        return self._fetch_obj(method, NotFoundException, properties=["hs_note_body"])

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        note = self.get_object()
        self.update_source_metadata(object=note)
        output = self._join_object_properties(note)
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(output)
        return


@dataclass
class HubSpotProductIngestDoc(HubSpotIngestDoc):
    connector_config: SimpleHubSpotConfig
    registry_name: str = "hubspot_product"

    def __post_init__(self):
        self.content_properties = ["description"]
        self._add_custom_properties(HubSpotObjectTypes.PRODUCTS.value)

    @requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def get_object(self):
        from hubspot.crm.products.exceptions import NotFoundException

        method = self.session_handle.service.crm.products.basic_api.get_by_id
        return self._fetch_obj(method, NotFoundException, properties=["description"])

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        product = self.get_object()
        self.update_source_metadata(object=product)
        output = self._join_object_properties(product)
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(output)
        return


@dataclass
class HubSpotTicketIngestDoc(HubSpotIngestDoc):
    connector_config: SimpleHubSpotConfig
    registry_name: str = "hubspot_ticket"

    def __post_init__(self):
        self.content_properties = ["subject", "content"]
        self._add_custom_properties(HubSpotObjectTypes.PRODUCTS.value)

    @requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def get_object(self):
        from hubspot.crm.tickets.exceptions import NotFoundException

        method = self.session_handle.service.crm.tickets.basic_api.get_by_id
        return self._fetch_obj(method, NotFoundException)

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        ticket = self.get_object()
        self.update_source_metadata(object=ticket)
        output = self._join_object_properties(ticket)
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(output)
        return


@dataclass
class HubSpotSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):
    connector_config: SimpleHubSpotConfig

    def initialize(self):
        self.hubspot = self.connector_config.create_session_handle().service

    @requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def _list_objects(self, get_page_method, ingest_doc_class):
        try:
            objects = get_page_method()
        except Exception as e:
            logger.error(e)
            logger.error(
                f"Failed to retrieve {type(ingest_doc_class).__name__}, omitting processing...",
            )
            return []
        return [
            ingest_doc_class(
                connector_config=self.connector_config,
                processor_config=self.processor_config,
                read_config=self.read_config,
                object_id=obj.id,
            )
            for obj in objects.results
        ]

    def _get_calls(self) -> t.List[HubSpotCallIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.objects.calls.basic_api.get_page,
            HubSpotCallIngestDoc,
        )

    def _get_communications(self) -> t.List[HubSpotCommunicationIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.objects.communications.basic_api.get_page,
            HubSpotCommunicationIngestDoc,
        )

    def _get_emails(self) -> t.List[HubSpotEmailIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.objects.emails.basic_api.get_page,
            HubSpotEmailIngestDoc,
        )

    def _get_notes(self) -> t.List[HubSpotNotesIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.objects.notes.basic_api.get_page,
            HubSpotNotesIngestDoc,
        )

    def _get_products(self) -> t.List[HubSpotProductIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.products.basic_api.get_page,
            HubSpotProductIngestDoc,
        )

    def _get_tickets(self) -> t.List[HubSpotTicketIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.tickets.basic_api.get_page,
            HubSpotTicketIngestDoc,
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
