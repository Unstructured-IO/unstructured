import typing as t
import uuid
from dataclasses import dataclass, field

from unstructured.ingest.enhanced_dataclass import enhanced_field
from unstructured.ingest.error import DestinationConnectionError
from unstructured.ingest.interfaces import (
    AccessConfig,
    BaseConnectorConfig,
    BaseDestinationConnector,
    WriteConfig,
)
from unstructured.ingest.logger import logger
from unstructured.staging.base import flatten_dict
from unstructured.utils import requires_dependencies

if t.TYPE_CHECKING:
    from clarifai.client.input import Inputs


@dataclass
class ClarifaiAccessConfig(AccessConfig):
    api_key: str = enhanced_field(sensitive=True)


@dataclass
class SimpleClarifaiConfig(BaseConnectorConfig):
    access_config: ClarifaiAccessConfig
    app_id: str
    user_id: str
    dataset_id: t.Optional[str] = None


@dataclass
class ClarifaiWriteConfig(WriteConfig):
    batch_size: int = 50


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
                if access_conf.api_key is not None:
                    clarifai_pat = access_conf.api_key
            except Exception as e:
                raise (f"please provide clarifai PAT key : {e}")

            self._client = Inputs(
                app_id=self.connector_config.app_id,
                user_id=self.connector_config.user_id,
                pat=clarifai_pat,
            )
        return self._client

    @requires_dependencies(["clarifai"], extras="clarifai")
    @DestinationConnectionError.wrap
    def initialize(self):
        _ = self.client

    def check_connection(self):
        try:
            _ = [inp for inp in self.client.list_inputs(page_no=1, per_page=1)]  # noqa: C416
        except Exception as e:
            logger.error(f"Failed to validate connection {e}", exc_info=True)
            raise DestinationConnectionError(f"failed to validate connection: {e}")

    def normalize_dict(self, element_dict: dict) -> dict:
        """Modifying schema of the dict in order to compile with clarifai input formats"""
        return {
            "input_id": str(uuid.uuid4().hex),
            "text": element_dict.pop("text", None),
            "metadata": {
                **flatten_dict(
                    element_dict,
                    separator="_",
                    flatten_lists=True,
                    remove_none=True,
                ),
            },
        }

    def write_dict(self, *args, elements_dict: t.List[t.Dict[str, t.Any]], **kwargs) -> None:
        from google.protobuf.struct_pb2 import Struct

        logger.info(
            f"writing {len(elements_dict)} objects to destination "
            f"app {self.connector_config.app_id} "
        )
        try:
            batch_size = self.write_config.batch_size
            for idx in range(0, len(elements_dict), batch_size):
                batch_dict = elements_dict[idx : batch_size + idx]
                input_batch = []
                for elem in batch_dict:
                    meta_struct = Struct()
                    meta_struct.update(elem["metadata"])
                    input_batch.append(
                        self._client.get_text_input(
                            input_id=elem["input_id"],
                            raw_text=elem["text"],
                            dataset_id=self.connector_config.dataset_id,
                            metadata=meta_struct,
                        )
                    )
                result_id = self._client.upload_inputs(inputs=input_batch)
                logger.debug(
                    f"Input posted successfully into {self.connector_config.app_id}. \
                    Result id: {result_id}"
                )

        except Exception as e:
            raise e
