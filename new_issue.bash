#!/bin/bash

##
# Sets up new issue
#
# Usage:
# bash setup.bash `ISSUE`
#
##

issue=$1

mkdir -p issues/"$issue"
cd issues/"$issue" || exit

# Prepare directory structure
for dir in meta \
           config \
           src/csv \
           src/json \
           src/templates \
           dist/json \
           dist/images \
           dist/documents/pdf \
           dist/documents/mails \
           dist/templates/partials
do
    mkdir -p "$dir"
done

# Fill with CSV files (if present)
if [ -d ../../"$issue" ]; then
    # (1) Move files from dummy directory
    for file in ../../"$issue"/*.csv; do
        base_name=$(basename "$file")
        mv "$file" src/csv/"$base_name"
    done

    # (2) Remove dummy directory
    rm -d ../../"$issue"
fi
