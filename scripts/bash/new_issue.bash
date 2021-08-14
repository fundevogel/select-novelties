#!/bin/bash

##
# Sets up new issue
#
# Usage:
# bash setup.bash `ISSUE`
#
##

issue=$1

root_directory=$(dirname "$(dirname "$(dirname "$0")")")

mkdir -p "$root_directory"/issues/"$issue"
cd "$root_directory"/issues/"$issue" || exit

# Preparing directory structure
# (1) Generate skeleton
for dir in config \
           meta \
           src/csv \
           src/json \
           src/templates \
           dist/csv \
           dist/json \
           dist/images \
           dist/images \
           dist/documents/pdf \
           dist/documents/mails \
           dist/templates/partials
do
    mkdir -p "$dir"
done

# (2) Copy CSV files (if present)
if [ -d ../../"$issue" ]; then

    for file in ../../"$issue"/*.csv; do
        base_name=$(basename "$file")
        mv "$file" src/csv/"$base_name"
    done

    rm -rf ../../"$issue"
fi
