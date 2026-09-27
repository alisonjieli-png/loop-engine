#!/bin/sh
# Print the number of data rows of a CSV file: every line after the header.
set -eu
if [ "$#" -ne 1 ]; then
  echo "usage: count_rows.sh FILE" >&2
  exit 2
fi
tail -n +2 "$1" | wc -l
