# Developing V2 Connectors
## Intro
The Unstructured open source repo processes documents in a pipeline. The Source and Destination connectors sit at the front and back of the pipeline. For more details see below.

## Simplest Example of a Pipeline
The simplest example of a pipeline would start with a local source connector, followed by a partioner, and then end with a local destination connector. Here is what the code to run this would look like:

`local.py`

```
from unstructured.ingest.v2.interfaces import ProcessorConfig
from unstructured.ingest.v2.pipeline.pipeline import Pipeline
from unstructured.ingest.v2.processes.connectors.local import (
    LocalConnectionConfig,
    LocalDownloaderConfig,
    LocalIndexerConfig,
    LocalUploaderConfig,
)
from unstructured.ingest.v2.processes.partitioner import PartitionerConfig

if __name__ == "__main__":
    Pipeline.from_configs(
        context=ProcessorConfig(
            verbose=True,
            work_dir="local-working-dir",
            reprocess=True,
            re_download=True,
        ),
        source_connection_config=LocalConnectionConfig(),
        indexer_config=LocalIndexerConfig(input_path="example-docs/fake-text.txt"),
        downloader_config=LocalDownloaderConfig(),
        partitioner_config=PartitionerConfig(),
        uploader_config=LocalUploaderConfig(output_dir="local-working-dir/output"),
    ).run()
```
You can run this with `python local.py` (Adjust the `input_path` and `output_path` as appropriate.)

The result would be a partitioned `fake-text.txt.json` file in the `local-output` directory.

>This is the type of Python file you'll want to run while developing a new connector so that you can iterate on your connector.

The ProcessorConfig attributes are optional, but are added to make development easier.

Notice that the pipeline runs the following:

* context - The ProcessorConfig runs the pipeline. The arguments are related to the overall pipeline.
* source_connection - Takes arguments needed to connect to the source. Local files don't need anything here. Other connectors will.
* indexer - Takes the files in the `input_path` and creates .json files that point the downloader step to the right files 
* downloader - This does the actual downloading of the raw files (for non-blob files it may do something different like create a .txt file for every row in a source table)
* partitioner - Partitions the downloaded file provided it is a partionable file type.
* chunker/embedder - *Not represented here* but often needed to prepare files for upload to a vector database.
* stager - *Not represented here* but is often used to prepare partitioned files for upload.
* uploader - Uploads the blob-like files to the `output_dir`.


If you look at the folders/files in `local-working-dir` you will see the files that the pipeline creates as it runs.

```
local-working-dir
- index
  - a4a1035d57ed.json
- output
  - fake-text.txt.json
- partition
  - 36caa9b04378.json
```

(Note that the index and partition file names are deterministic and based on the BLABLABLA) In the case of the local source connector, it won't download files because they are already local. Also note that the final file is named based on the original file with a .json since it has been partitioned. Not all output files will be named the same as the input file. An example is a table as a file, the output will be BLABLABLA.



















## More Advanced Pipeline (S3 Source)
Here is a more advanced pipeline with an S3 source connector, followed by a partioner, and then ending with a local connector. 
>This is the type of Python file you'll want to create while developing a new **source** connector so that you can iterate on your source connector.

