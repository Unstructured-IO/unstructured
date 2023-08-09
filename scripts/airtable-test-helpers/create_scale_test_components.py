import os

# import pyairtable as pyair
from pyairtable import Api

from unstructured.ingest.logger import logger

SCALE_TEST_NUMBER_OF_RECORDS = 20_000

# Access token that has read and write permissions for the respective workspace
token = os.environ["AIRTABLE_ACCESS_TOKEN_WRITE"]

# You can find the IDs below defined in component_ids.sh
# In case new ones are needed to be created, there's guidance below and in component_ids.sh.

# ID of a new base that is intended to contain one large table.
# The table will be filled using this python script.
# If the ID is not in the environment, it is possible to create a new base
# via the Airtable UI, and get the base ID from the URL structure.
# (https://support.airtable.com/docs/finding-airtable-ids)
large_table_base_id = os.environ["LARGE_TABLE_BASE_ID"]

# ID of the one table inside the base "large_table_base".
# The table is intended to be large, and will be filled using this python script.
# If the ID is not in the environment, it is possible to create a new table
# via the Airtable UI, and get the table ID from the URL structure.
# (https://support.airtable.com/docs/finding-airtable-ids)
large_table_table_id = os.environ["LARGE_TABLE_TABLE_ID"]

# ID of a base that is intended to contain lots of tables.
# large_base_base_id = os.environ["LARGE_BASE_BASE_ID"]
# Creating tables is not yet supported in pyairtable. Try Airtable Web API instead:
# https://airtable.com/developers/web/api/create-base"


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
