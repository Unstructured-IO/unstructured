Processor Configuration
=========================

A common process configuration plays a pivotal role in overseeing the entire ingest process, encompassing various
aspects to ensure efficiency and reliability. This configuration includes parameters for managing a pool of workers,
which allows for parallelization of the ingest process to maximize throughput. Additionally, it addresses the
storage and retrieval of intermediate results, supporting caching strategies that enable replayability in case of
errors or interruptions. By configuring worker pools, the process can efficiently handle multiple tasks concurrently,
enhancing performance. Furthermore, saving intermediate results allows for the resumption of the process from a known
state, reducing data loss and ensuring robustness in the face of unexpected errors or system failures. This
comprehensive configuration promotes an organized and resilient approach to data ingestion, improving overall
system reliability and efficiency.

Configs
---------------------
* ``reprocess (default False)``: If set to true, will ignore all content that may have been cached and rerun each step.
* ``verbose (default False)``: Boolean flag to set if debug logging should be included in the output or not.
* ``work_dir``: The file path for where intermediate results should be saved. If one is not set, a default will be used relative to the users' home location.
* ``output_dir``: Where the final results will be located when the process is finished. This will be regardless of if a destination is configured.
* ``num_processes``: For every step that can use a pool of workers to increase throughput, how many workers to configure in the pool.
* ``raise_on_error (default False)``: By default, for any single document that might fail in the process, will cause the error to be
  logged but allow for all other documents to proceed in the process. If this flag is set, will cause the entire process to fail and raise the error if any one document fails.
