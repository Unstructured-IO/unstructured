#!/usr/bin/env bash

# Components below are all created using Airtable UI, however, in case they need
# to be recreated, it is also possible to create them using the Web API.
# pyairtable does not yet support creating these components (bases, tables).

# For documentation on the Web API for creating bases, check:
# https://airtable.com/developers/web/api/create-base

# For creating lots of tables inside a base, check:
# create_scale_test_components.sh

LARGE_TABLE_BASE_ID="appQqieVsbxpwwD3i"
LARGE_TABLE_TABLE_ID="tbll85GCfxED1OrvC"
LARGE_BASE_BASE_ID="appjPRwoyawsapoGW"
LARGE_WORKSPACE_BASE_ID_1="appSSCNWuIMjzeraO"
LARGE_WORKSPACE_BASE_ID_2="appyvCsaHWn38RzFc"
LARGE_WORKSPACE_BASE_ID_3="appbd8fkBv3AXj0Ab"
LARGE_WORKSPACE_BASE_ID_4="appHEvCPnpfiAwjPE"
LARGE_WORKSPACE_BASE_ID_5="appL9ND7LVWaItAmC"
LARGE_WORKSPACE_BASE_ID_6="appOGnidMsh93yCQI"
LARGE_WORKSPACE_BASE_ID_7="apps71HjvZRRgqHkz"
LARGE_WORKSPACE_BASE_ID_8="appvDbw5f7jCQqdsr"
LARGE_WORKSPACE_BASE_ID_9="appGFdtbLmqf2k8Ly"
LARGE_WORKSPACE_BASE_ID_10="appTn61bfU8vCIkGf"
LARGE_WORKSPACE_BASE_ID_11="app1c4CtIQ4ZToHIR"
LARGE_WORKSPACE_BASE_ID_12="apphvDFg6OC7l1xwo"
# shellcheck disable=SC2034
LARGE_TEST_LIST_OF_PATHS="$LARGE_BASE_BASE_ID $LARGE_TABLE_BASE_ID $LARGE_WORKSPACE_BASE_ID_1 $LARGE_WORKSPACE_BASE_ID_2 $LARGE_WORKSPACE_BASE_ID_3 $LARGE_WORKSPACE_BASE_ID_4 $LARGE_WORKSPACE_BASE_ID_5 $LARGE_WORKSPACE_BASE_ID_6 $LARGE_WORKSPACE_BASE_ID_7 $LARGE_WORKSPACE_BASE_ID_8 $LARGE_WORKSPACE_BASE_ID_9 $LARGE_WORKSPACE_BASE_ID_10 $LARGE_WORKSPACE_BASE_ID_11 $LARGE_WORKSPACE_BASE_ID_12"

export LARGE_TABLE_BASE_ID
export LARGE_TABLE_TABLE_ID
