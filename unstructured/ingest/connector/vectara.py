import json
import typing as t
import uuid
from dataclasses import dataclass

from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.utils.data_prep import chunk_generator
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

import requests

@dataclass
class VectaraAccessConfig(AccessConfig):
    api_key: t.AnyStr = None

@dataclass
class SimpleVectaraConfig(BaseConnectorConfig):
    access_config: VectaraAccessConfig
    customer_id: t.AnyStr = None
    corpus_id: t.AnyStr = None
    endpoint = "api.vectara.io"

@dataclass
class VectaraWriteConfig(WriteConfig):
    batch_size: int = 100

@dataclass
class VectaraDestinationConnector(BaseDestinationConnector):
    write_config: VectaraWriteConfig
    connector_config: SimpleVectaraConfig

    def initialize(self):
        self.session = requests.Session()  # to reuse connections
        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        self.session.mount("http://", adapter)
        self.check_connection()

    @DestinationConnectionError.wrap
    def check_connection(self):
        #  write and delete a dummy document
        dummy_doc = {
            "documentId": str(uuid.uuid4()),
            "section": [
                {
                    "text": "dummy text for testing unstructured destination connector",
                    "metadataJson": json.dumps({"dummy": "dummy"})
                }
            ]
        }
        if not self._index_document(dummy_doc) or not self._delete_doc(dummy_doc["documentId"]):
            logger.error("Connection check failed")


        # delete document; returns True if successful, False otherwise
    def _delete_doc(self, doc_id: str) -> bool:
        """
        Delete a document from the Vectara corpus.

        Args:
            url (str): URL of the page to delete.
            doc_id (str): ID of the document to delete.

        Returns:
            bool: True if the delete was successful, False otherwise.
        """
        body = {'customer_id': self.connector_config.customer_id, 'corpus_id': self.connector_config.corpus_id, 
                'document_id': doc_id}
        post_headers = { 'x-api-key': self.connector_config.access_config.api_key, 
                         'customer-id': str(self.connector_config.customer_id) }
        response = self.session.post(
            f"https://{self.connector_config.endpoint}/v1/delete-doc", data=json.dumps(body),
            verify=True, headers=post_headers)
        
        if response.status_code != 200:
            logger.error(f"Delete request failed for doc_id = {doc_id} with status code {response.status_code}, reason {response.reason}, text {response.text}")
            return False
        return True

    def _index_document(self, document: t.Dict[str, t.Any]) -> bool:
        """
        Index a document (by uploading it to the Vectara corpus) from the document dictionary
        """
        api_endpoint = f"https://{self.connector_config.endpoint}/v1/index"

        request = {
            'customer_id': self.connector_config.customer_id,
            'corpus_id': self.connector_config.corpus_id,
            'document': document,
        }

        post_headers = { 
            'x-api-key': self.connector_config.access_config.api_key,
            'customer-id': str(self.connector_config.customer_id),
            'X-Source': 'unstructured'
        }
        try:
            data = json.dumps(request)
        except Exception as e:
            logger.info(f"Can't serialize request {request}, skipping")   
            return False

        try:
            response = self.session.post(api_endpoint, data=data, verify=True, headers=post_headers)
        except Exception as e:
            logger.info(f"Exception {e} while indexing document {document['documentId']}")
            return False

        if response.status_code != 200:
            logger.error("Document indexing failed with code %d, reason %s, text %s",
                          response.status_code,
                          response.reason,
                          response.text)
            return False

        result = response.json()
        if "status" in result and result["status"] and \
           ("ALREADY_EXISTS" in result["status"]["code"] or \
            ("CONFLICT" in result["status"]["code"] and "Indexing doesn't support updating documents" in result["status"]["statusDetail"])):
            logger.info(f"Document {document['documentId']} already exists, re-indexing")
            self._delete_doc(document['documentId'])
            response = self.session.post(api_endpoint, data=json.dumps(request), verify=True, headers=post_headers)
            return True
        if "status" in result and result["status"] and "OK" in result["status"]["code"]:
            return True
        
        logger.info(f"Indexing document {document['documentId']} failed, response = {result}")
        return False
    
    def write_dict(self, *args, docs_list: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        logger.info(f"Inserting / updating {len(docs_list)} documents to Vectara ")
        for vdoc in docs_list:
            self._index_document(vdoc)

    def write(self, docs: t.List[BaseIngestDoc]) -> None:
        docs_list: t.Dict[t.Dict[str, t.Any]] = []

        def get_metadata(element) -> t.Dict[str, t.Any]:
            '''
            Select which meta-data fields to include and optionaly map them to a new new.
            remove the "metadata-" prefix from the keys
            '''
            metadata_map = {
                'page_number': 'page_number', 
                'data_source-url': 'url', 
                'filename': 'filename', 
                'filetype': 'filetype', 
                'last_modified': 'last_modified'
            }
            md = flatten_dict(element, separator="-",flatten_lists=True)
            md = {k.replace('metadata-', ''): v for k, v in md.items()}
            md = {metadata_map[k]:v for k,v in md.items() if k in metadata_map.keys()}
            return md

        for doc in docs:
            local_path = doc._output_filename
            with open(local_path) as json_file:
                dict_content = json.load(json_file)
                all_types = [e["type"] for e in dict_content]
                vdoc = {
                    "documentId": str(uuid.uuid4()),
                    "section": [
                        {
                            "text": element.pop("text", None),
                            "metadataJson": json.dumps(get_metadata(element))
                        }
                        for element in dict_content
                    ]
                }
                logger.info(
                    f"Extending {len(vdoc)} json elements from content in {local_path}",
                )
                docs_list.append(vdoc)
        self.write_dict(docs_list=docs_list)
