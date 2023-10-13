from dataclasses import dataclass

from unstructured.ingest.interfaces import PermissionsCleanupMixin, ProcessorConfig
from unstructured.ingest.pipeline.interfaces import PermissionsNode


@dataclass
class PermissionsDataCleaner(PermissionsNode, PermissionsCleanupMixin):
    processor_config: ProcessorConfig

    def run(self):
        self.cleanup_permissions()
