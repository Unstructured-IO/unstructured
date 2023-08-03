import os

# import pyairtable as pyair
from pyairtable import Api

from unstructured.ingest.logger import logger

SCALE_TEST_NUMBER_OF_RECORDS = 20_000

token = os.environ["AIRTABLE_ACCESS_TOKEN_WRITE"]
large_table_base_id = os.environ["LARGE_TABLE_BASE_ID"]
large_table_table_id = os.environ["LARGE_TABLE_TABLE_ID"]
large_base_base_id = os.environ["LARGE_BASE_BASE_ID"]


def create_n_bases(api, number_of_bases):
    raise NotImplementedError(
        "Creating bases is not yet supported in pyairtable. \
                              Try Airtable Web API instead: \
                              https://airtable.com/developers/web/api/create-base",
    )
    # if len(pyair.metadata.get_api_bases(api)["bases"])>99:
    #     logger.warning("Airtable Org already has a high number of bases. \
    #                Aborting creation of new bases to avoid duplication and bloating.")
    #     return

    number_of_bases


def create_n_tables(base, number_of_tables):
    raise NotImplementedError(
        "Creating tables is not yet supported in pyairtable. \
                              Try Airtable Web API instead: \
                              https://airtable.com/developers/web/api/create-table",
    )
    # if len(pyair.metadata.get_base_schema(base)["tables"])>99:
    #     logger.warning("Base already has a high number of tables. \
    #               Aborting creation of new tables to avoid duplication and bloating.")
    #     return


def create_n_records(table, number_of_records):
    logger.warning(
        "Fetching table records to count, before creation of new records.\
                   This should take around 1 second per 415 records.",
    )
    if len(table.all()) > SCALE_TEST_NUMBER_OF_RECORDS - 1:
        logger.warning(
            "Table already has a high number of records. \
                Aborting creation of new records to avoid duplication and bloating.",
        )
        return

    records = [{"Name": f"My Name is {i}"} for i in range(number_of_records)]
    table.batch_create(records)


if __name__ == "__main__":
    api = Api(token)
    large_table = api.table(large_table_base_id, large_table_table_id)
    logger.info("Creating records, this should take about 1 second per 40 records.")
    create_n_records(large_table, SCALE_TEST_NUMBER_OF_RECORDS)
