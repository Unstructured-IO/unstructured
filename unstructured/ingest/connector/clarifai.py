import os
import typing as t
from dataclasses import dataclass, field
import uuid
from pathlib import PurePath

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.enhanced_dataclass.core import _asdict
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    BaseSingleIngestDoc,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.utils.data_prep import chunk_generator
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from clarifai.client.input import Inputs

@dataclass
class ClarifaiAccessConfig(AccessConfig):
    api_key: str = enhanced_field(sensitive=True)
    #print("class initialized")

@dataclass
class SimpleClarifaiConfig(BaseConnectorConfig):
    access_config: ClarifaiAccessConfig
    app_id: t.Optional[str] = None
    user_id: t.Optional[str] = None
    
@dataclass
class ClarifaiWriteConfig(WriteConfig):
    batch_size: int = 50
    num_processes: int = 1

@dataclass
class ClarifaiDestinationConnector(BaseDestinationConnector):
    write_config: ClarifaiWriteConfig
    connector_config: SimpleClarifaiConfig
    _client: t.Optional["Inputs"] = field(init=False, default=None)
    
    @property
    @requires_dependencies(["clarifai"], extras="clarifai")
    def client(self) -> "Inputs":
        if self._client is None:
            from clarifai.client.input import Inputs
        access_conf = self.connector_config.access_config
        try:
            if access_conf.api_key is not None :
                clarifai_pat = access_conf.api_key   
        except Exception as e:
            raise (f"please provide clarifai PAT key : {e}")
    
        self._client = Inputs(app_id = self.connector_config.app_id, 
                             user_id = self.connector_config.user_id, 
                             pat = clarifai_pat)
        return self._client
        
        
    @requires_dependencies(["clarifai"], extras="clarifai")
    @DestinationConnectionError.wrap
    def initialize(self):
        _ = self.client  
       
    def check_connection(self):
        try:
            _ = self.client
        except Exception as e:
            logger.error(f"Failed to validate connection {e}", exc_info=True)
            raise DestinationConnectionError(f"failed to validate connection: {e}")
        
    
    def normalize_dict(self, element_dict: dict) -> dict:
        """Modifying schema of the dict in order to compile with clarifai input formats"""
        return (
            {
                "input_id" : str(uuid.uuid4().hex),
                "text" : element_dict.get("text"),
                "metadata" : {
                    "url": element_dict.get("metadata", {}).get("data_source", {}).get("url"),
                    "date_created": element_dict.get("metadata", {}).get("data_source", {}).get("date_created"),
                    "date_modified": element_dict.get("metadata", {}).get("data_source", {}).get("date_modified"),
                    "date_processed": element_dict.get("metadata", {}).get("data_source", {}).get("date_processed"),
                    "record_locator": element_dict.get("metadata", {}).get("data_source", {}).get("record_locator"),
                    "file_directory": element_dict.get("metadata",{}).get("file_directory"),
                    "filename": element_dict.get("metadata",{}).get("filename"),
                    "filetype": element_dict.get("metadata",{}).get("filetype"),
                    "languages": element_dict.get("metadata",{}).get("languages"),
                    "last_modified": element_dict.get("metadata",{}).get("last_modified"),
                }
            }
        )
        
    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        
        from google.protobuf.struct_pb2 import Struct
        
        logger.info(
            f"writing {len(elements_dict)} objects to destination "
            f"app {self.connector_config.app_id} "
        )
        try:
            batch = self.write_config.batch_size
            for idx in range (0, len(elements_dict), batch):
                batch_dict = elements_dict[idx : batch + idx]
                input_batch = []
                for elem in batch_dict :
                    meta_struct = Struct()
                    meta_struct.update(elem["metadata"])
                    input_batch.append(self._client.get_text_input(
                            input_id=elem["input_id"],
                            raw_text=elem["text"],
                            metadata=meta_struct,)
                        )
                result_id = self._client.upload_inputs(inputs=input_batch)
                logger.debug(f"Input posted successfully into {self.connector_config.app_id}.")
                
        except Exception as e :
            raise e 
                
        
        
    
    