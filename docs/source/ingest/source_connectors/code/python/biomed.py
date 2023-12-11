from unstructured.ingest.connector.biomed import (
    SimpleBiomedConfig,
)
from unstructured.ingest.interfaces import (
    PartitionConfig,
    ProcessorConfig,
    ReadConfig,
)
from unstructured.ingest.runner import BiomedRunner

if __name__ == "__main__":
    runner = BiomedRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="azure-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(),
        connector_config=SimpleBiomedConfig(path="oa_pdf/07/07/sbaa031.073.PMC7234218.pdf"),
    )
    runner.run()
