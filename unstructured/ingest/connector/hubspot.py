import typing as t
from enum import Enum
from dataclasses import dataclass, field
from functools import cached_property
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
    SourceMetadata
)
from unstructured.ingest.logger import logger
from pathlib import Path
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from hubspot import HubSpot

CONTENT_TAG = 'content'

class HubSpotObjectTypes(Enum):
    CALLS = 'calls'
    COMMUNICATIONS = 'communications'
    EMAILS = 'emails'
    NOTES = 'notes'
    PRODUCTS = 'products'
    TICKETS = 'tickets'

@dataclass
class HubSpotSessionHandle(BaseSessionHandle):
    service: "HubSpot"

@dataclass
class SimpleHubSpotConfig(ConfigSessionHandleMixin, BaseConnectorConfig):

    api_token: str
    params: t.Optional[str] = None
    properties: t.Optional[dict] = None
    object_types: t.Optional[t.List[str]] = None
    ticket_content_tags: t.Optional[t.List[str]] = None

    #@requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def create_session_handle(self) -> HubSpotSessionHandle:
        from hubspot import HubSpot
        service = HubSpot(access_token=self.api_token)
        return HubSpotSessionHandle(service=service)

@dataclass
class HubSpotIngestDoc(IngestDocSessionHandleMixin, IngestDocCleanupMixin, BaseIngestDoc):
    connector_config: SimpleHubSpotConfig
    object_id: str 

    @property
    def filename(self):
        return (
            Path(self.read_config.download_dir) /
            f"{self.registry_name}/{self.object_id}.txt"
        ).resolve()

    @property
    def _output_filename(self):
        return (
            Path(self.partition_config.output_dir) /
            f"{self.registry_name}/{self.object_id}.json"
        ).resolve()

    @property
    def record_locator(self) -> t.Optional[t.Dict[str, t.Any]]:
        return {
            "object_id": self.object_id
        }
    
    @property
    def version(self) -> t.Optional[str]:
        return None

    @property
    def source_url(self) -> t.Optional[str]:
        return None
    
    def get_object(self, get_by_id_method, not_found_exception):
        try:
            response = get_by_id_method(self.object_id)
        except not_found_exception as e:
            logger.error(e)
            return None
        return response        

@dataclass
class HubSpotCallIngestDoc(HubSpotIngestDoc):
    connector_config: SimpleHubSpotConfig
    registry_name: str = "hubspot_call"

    #@requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def get_call(self):
        from hubspot.crm.objects.calls import NotFoundException
        method = self.session_handle.service.crm.objects.calls.basic_api.get_by_id
        return self.get_object(method, NotFoundException)
    
    def update_source_metadata(self, **kwargs) -> None:
        call = kwargs.get("call", self.get_call())
        if call is None:
            self.source_metadata = SourceMetadata(
                exists=False
            )
            return
        self.source_metadata = SourceMetadata(
            date_created=call.created_at.isoformat(),
            date_modified=call.updated_at.isoformat(),
            exists=True
        )

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        call = self.get_call()
        self.update_source_metadata(call=call)
        title = call.properties['hs_call_title']
        body = call.properties['hs_call_body']
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(f"{title}\n{body}")
        return

@dataclass
class HubSpotCommunicationIngestDoc(HubSpotIngestDoc):
    connector_config: SimpleHubSpotConfig
    registry_name: str = "hubspot_communication"
    
    #@requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def get_communication(self):
        from hubspot.crm.objects.communications.exceptions import NotFoundException
        method = self.session_handle.service.crm.objects.communications.basic_api.get_by_id
        return self.get_object(method, NotFoundException)
    
    def update_source_metadata(self, **kwargs) -> None:
        communication = kwargs.get("communication", self.get_communication())
        if communication is None:
            self.source_metadata = SourceMetadata(
                exists=False
            )
            return
        self.source_metadata = SourceMetadata(
            date_created=communication.created_at.isoformat(),
            date_modified=communication.updated_at.isoformat(),
            exists=True
        )

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        communication = self.get_communication()
        self.update_source_metadata(ticket=communication)
        content = communication.properties['hs_communication_body']
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(content)
        return

@dataclass
class HubSpotEmailIngestDoc(HubSpotIngestDoc):
    connector_config: SimpleHubSpotConfig
    registry_name: str = "hubspot_email"

    #@requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def get_email(self):
        from hubspot.crm.objects.emails.exceptions import NotFoundException
        method = self.session_handle.service.crm.objects.emails.api.basic_api.get_by_id
        return self.get_object(method, NotFoundException)
    
    def update_source_metadata(self, **kwargs) -> None:
        email = kwargs.get("email", self.get_email())
        if email is None:
            self.source_metadata = SourceMetadata(
                exists=False
            )
            return
        self.source_metadata = SourceMetadata(
            date_created=email.created_at.isoformat(),
            date_modified=email.updated_at.isoformat(),
            exists=True
        )

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        email = self.get_email()
        self.update_source_metadata(email=email)
        subject = email.properties['hs_email_subject']
        content = email.properties['hs_email_text']
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(f"{subject}\n{content}")
        return

@dataclass
class HubSpotNotesIngestDoc(HubSpotIngestDoc):
    connector_config: SimpleHubSpotConfig
    registry_name: str = "hubspot_note"
    
    #@requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def get_note(self):
        from hubspot.crm.objects.notes.exceptions import NotFoundException
        method = self.session_handle.service.crm.objects.notes.api.basic_api.get_by_id
        return self.get_object(method, NotFoundException)
    
    def update_source_metadata(self, **kwargs) -> None:
        note = kwargs.get("note", self.get_note())
        if note is None:
            self.source_metadata = SourceMetadata(
                exists=False
            )
            return
        self.source_metadata = SourceMetadata(
            date_created= note.created_at.isoformat(),
            date_modified=note.updated_at.isoformat(),
            exists=True
        )

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        note = self.get_note()
        self.update_source_metadata(note=note)
        content = note.properties['hs_note_body']
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(content)
        return

@dataclass
class HubSpotProductIngestDoc(HubSpotIngestDoc):
    connector_config: SimpleHubSpotConfig
    registry_name: str = "hubspot_product"
    
    #@requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def get_product(self):
        from hubspot.crm.products.exceptions import NotFoundException
        method = self.session_handle.service.crm.products.api.basic_api.get_by_id
        return self.get_object(method, NotFoundException)
    
    def update_source_metadata(self, **kwargs) -> None:
        product = kwargs.get("product", self.get_product())
        if product is None:
            self.source_metadata = SourceMetadata(
                exists=False
            )
            return
        self.source_metadata = SourceMetadata(
            date_created= product.created_at.isoformat(),
            date_modified=product.updated_at.isoformat(),
            exists=True
        )

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        product = self.get_product()
        self.update_source_metadata(product=product)
        content = product.properties['description']
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(content)
        return


@dataclass
class HubSpotTicketIngestDoc(HubSpotIngestDoc):
    connector_config: SimpleHubSpotConfig
    registry_name: str = "hubspot_ticket"
    
    #@requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def get_ticket(self):
        from hubspot.crm.tickets.exceptions import NotFoundException
        method = self.session_handle.service.crm.tickets.basic_api.get_by_id
        
        return self.get_object(method, NotFoundException)
    
    def update_source_metadata(self, **kwargs) -> None:
        ticket = kwargs.get("ticket", self.get_ticket())
        if ticket is None:
            self.source_metadata = SourceMetadata(
                exists=False
            )
            return
        self.source_metadata = SourceMetadata(
            date_created=ticket.created_at.isoformat(),
            date_modified=ticket.updated_at.isoformat(),
            exists=True
        )

    @SourceConnectionError.wrap
    @BaseIngestDoc.skip_if_file_exists
    def get_file(self):
        ticket = self.get_ticket()
        self.update_source_metadata(ticket=ticket)
        subject = ticket.properties['subject']
        content = ticket.properties['content']
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filename, "w", encoding="utf8") as f:
            f.write(f"{subject}\n{content}")
        return


@dataclass
class HubSpotSourceConnector(SourceConnectorCleanupMixin, BaseSourceConnector):

    connector_config: SimpleHubSpotConfig

    def initialize(self):
        self.hubspot = self.connector_config.create_session_handle().service

    #@requires_dependencies(["hubspot-api-client"], extras="hubspot")
    def _list_objects(self, get_page_method, ingest_doc_class):
        try:
            objects = get_page_method()
        except Exception as e:
            logger.error(e)
            logger.error(f"Failed to retrieve {type(ingest_doc_class).__name__}, omitting processing...")
            return []
        return [
            ingest_doc_class(
                connector_config=self.connector_config,
                partition_config=self.partition_config,
                read_config=self.read_config,
                object_id=obj.id
                )
            for obj in
            objects.results
        ]        

    def _get_calls(self) -> t.List[HubSpotCallIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.objects.calls.basic_api.get_page,
            HubSpotCallIngestDoc
        )
    
    def _get_communications(self) -> t.List[HubSpotCommunicationIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.objects.communications.basic_api.get_page,
            HubSpotCommunicationIngestDoc
        )

    def _get_emails(self) -> t.List[HubSpotEmailIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.objects.emails.basic_api.get_page,
            HubSpotEmailIngestDoc
        )
    
    def _get_notes(self) -> t.List[HubSpotNotesIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.objects.notes.basic_api.get_page,
            HubSpotNotesIngestDoc
        )
    
    def _get_products(self) -> t.List[HubSpotProductIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.products.basic_api.get_page,
            HubSpotProductIngestDoc
        )

    def _get_tickets(self) -> t.List[HubSpotTicketIngestDoc]:
        return self._list_objects(
            self.hubspot.crm.tickets.basic_api.get_page,
            HubSpotTicketIngestDoc
        )    

    def get_ingest_docs(self):
        obj_method_resolver = {
            HubSpotObjectTypes.CALLS.value: self._get_calls,
            HubSpotObjectTypes.COMMUNICATIONS.value: self._get_communications,
            HubSpotObjectTypes.EMAILS.value: self._get_emails,
            HubSpotObjectTypes.NOTES.value: self._get_notes,
            HubSpotObjectTypes.PRODUCTS.value: self._get_products,
            HubSpotObjectTypes.TICKETS.value: self._get_tickets
        }
        
        if self.connector_config.object_types is not None:
            obj_method_resolver = {k:obj_method_resolver.get(k) 
                                   for k in self.connector_config.object_types}


        ingest_docs = []
        for obj_name, obj_method in obj_method_resolver.items():
            logger.info(f"Retrieving - {obj_name}")
            ingest_docs += obj_method()

        return ingest_docs