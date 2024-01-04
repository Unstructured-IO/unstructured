import datetime
import json
import traceback
import typing as t
import uuid
from dataclasses import dataclass

import requests

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.staging.base import flatten_dict


@dataclass
class VectaraAccessConfig(AccessConfig):
    oauth_client_id: str = enhanced_field(sensitive=True)
    oauth_secret: str = enhanced_field(sensitive=True)


@dataclass
class SimpleVectaraConfig(BaseConnectorConfig):
    access_config: VectaraAccessConfig
    customer_id: t.AnyStr = None
    corpus_name: t.AnyStr = "vectara-unstructured"
    corpus_id: t.AnyStr = None


@dataclass
class VectaraWriteConfig(WriteConfig):
    batch_size: int = 100


@dataclass
class VectaraDestinationConnector(BaseDestinationConnector):
    write_config: VectaraWriteConfig
    connector_config: SimpleVectaraConfig

    BASE_URL = "https://api.vectara.io/v1"

    def initialize(self):
        self.check_connection()

    def _request(
        self,
        endpoint: str,
        http_method: str = "POST",
        params: t.Mapping[str, t.Any] = None,
        data: t.Mapping[str, t.Any] = None,
    ):
        url = f"{self.BASE_URL}/{endpoint}"

        current_ts = datetime.datetime.now().timestamp()
        if self.jwt_token_expires_ts - current_ts <= 60:
            self._get_jwt_token()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.jwt_token}",
            "customer-id": self.connector_config.customer_id,
            "X-source": "unstructured",
        }

        response = requests.request(
            method=http_method, url=url, headers=headers, params=params, data=json.dumps(data)
        )
        response.raise_for_status()
        return response.json()

    # get OAUth2 JWT token
    def _get_jwt_token(self):
        """Connect to the server and get a JWT token."""
        token_endpoint = f"https://vectara-prod-{self.connector_config.customer_id}. \
            auth.us-west-2.amazoncognito.com/oauth2/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self.connector_config.access_config.oauth_client_id,
            "client_secret": self.connector_config.access_config.oauth_secret,
        }

        request_time = datetime.datetime.now().timestamp()
        response = requests.request(method="POST", url=token_endpoint, headers=headers, data=data)
        response_json = response.json()

        self.jwt_token = response_json.get("access_token")
        self.jwt_token_expires_ts = request_time + response_json.get("expires_in")
        return self.jwt_token

    @DestinationConnectionError.wrap
    def check_connection(self):
        """
        Check the connection for Vectara and validate corpus exists.
        - If more than one exists - then return a message
        - If exactly one exists with this name - use it.
        - If does not exist - create it.
        """
        try:
            jwt_token = self._get_jwt_token()
            if not jwt_token:
                return "Unable to get JWT Token. Confirm your Client ID and Client Secret."

            list_corpora_response = self._request(
                endpoint="list-corpora",
                data={"numResults": 100, "filter": self.connector_config.corpus_name},
            )

            possible_corpora_ids_names_map = {
                corpus.get("id"): corpus.get("name")
                for corpus in list_corpora_response.get("corpus")
                if corpus.get("name") == self.connector_config.corpus_name
            }

            if len(possible_corpora_ids_names_map) > 1:
                return f"Multiple Corpora exist with name {self.connector_config.corpus_name}"
            if len(possible_corpora_ids_names_map) == 1:
                self.connector_config.corpus_id = list(possible_corpora_ids_names_map.keys())[0]
            else:
                data = {
                    "corpus": {
                        "name": self.connector_config.corpus_name,
                    }
                }
                create_corpus_response = self._request(endpoint="create-corpus", data=data)
                self.connector_config.corpus_id = create_corpus_response.get("corpusId")

        except Exception as e:
            return str(e) + "\n" + "".join(traceback.TracebackException.from_exception(e).format())

    # delete document; returns True if successful, False otherwise
    def _delete_doc(self, doc_id: str) -> None:
        """
        Delete a document from the Vectara corpus.

        Args:
            url (str): URL of the page to delete.
            doc_id (str): ID of the document to delete.
        """
        body = {
            "customer_id": self.connector_config.customer_id,
            "corpus_id": self.connector_config.corpus_id,
            "document_id": doc_id,
        }
        self._request(endpoint="delete-doc", data=body)

    def _index_document(self, document: t.Dict[str, t.Any]) -> None:
        """
        Index a document (by uploading it to the Vectara corpus) from the document dictionary
        """
        body = {
            "customer_id": self.connector_config.customer_id,
            "corpus_id": self.connector_config.corpus_id,
            "document": document,
        }

        try:
            result = self._request(endpoint="index", data=body, http_method="POST")
        except Exception as e:
            logger.info(f"Exception {e} while indexing document {document['documentId']}")
            return

        if (
            "status" in result
            and result["status"]
            and (
                "ALREADY_EXISTS" in result["status"]["code"]
                or (
                    "CONFLICT" in result["status"]["code"]
                    and "Indexing doesn't support updating documents"
                    in result["status"]["statusDetail"]
                )
            )
        ):
            logger.info(f"Document {document['documentId']} already exists, re-indexing")
            self._delete_doc(document["documentId"])
            result = self._request(endpoint="index", data=body, http_method="POST")
            return

        if "status" in result and result["status"] and "OK" in result["status"]["code"]:
            logger.info(f"Indexing document {document['documentId']} succeeded")
        else:
            logger.info(f"Indexing document {document['documentId']} failed, response = {result}")

    def write_dict(self, *args, docs_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(f"Inserting / updating {len(docs_list)} documents to Vectara ")
        for vdoc in docs_list:
            self._index_document(vdoc)

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        docs_list: t.Dict[t.Dict[str, t.Any]] = []

        def get_metadata(element) -> t.Dict[str, t.Any]:
            """
            Select which meta-data fields to include and optionaly map them to a new new.
            remove the "metadata-" prefix from the keys
            """
            metadata_map = {
                "page_number": "page_number",
                "data_source-url": "url",
                "filename": "filename",
                "filetype": "filetype",
                "last_modified": "last_modified",
            }
            md = flatten_dict(element, separator="-", flatten_lists=True)
            md = {k.replace("metadata-", ""): v for k, v in md.items()}
            md = {metadata_map[k]: v for k, v in md.items() if k in metadata_map}
            return md

        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                dict_content = json.load(json_file)
                [e["type"] for e in dict_content]
                vdoc = {
                    "documentId": str(uuid.uuid4()),
                    "section": [
                        {
                            "text": element.pop("text", None),
                            "metadataJson": json.dumps(get_metadata(element)),
                        }
                        for element in dict_content
                    ],
                }
                logger.info(
                    f"Extending {len(vdoc)} json elements from content in {local_path}",
                )
                docs_list.append(vdoc)
        self.write_dict(docs_list=docs_list)
