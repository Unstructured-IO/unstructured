#!/usr/bin/env bash
BASE=$(basename $1)
DEST=$2/$BASE.txt
cat $1 | jq '.[].text' > $DEST