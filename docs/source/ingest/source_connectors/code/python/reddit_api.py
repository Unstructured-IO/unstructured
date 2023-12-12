import os

from unstructured.ingest.connector.reddit import RedditAccessConfig, SimpleRedditConfig
from unstructured.ingest.interfaces import PartitionConfig, ProcessorConfig, ReadConfig
from unstructured.ingest.runner import RedditRunner

if __name__ == "__main__":
    runner = RedditRunner(
        processor_config=ProcessorConfig(
            verbose=True,
            output_dir="reddit-ingest-output",
            num_processes=2,
        ),
        read_config=ReadConfig(),
        partition_config=PartitionConfig(
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
        ),
        connector_config=SimpleRedditConfig(
            access_config=RedditAccessConfig(
                client_secret="<client secret here>",
            ),
            subreddit_name="machinelearning",
            client_id="<client id here>",
            user_agent=r"Unstructured Ingest Subreddit fetcher by \\u\...",
            search_query="Unstructured",
            num_posts=10,
        ),
    )
    runner.run()
