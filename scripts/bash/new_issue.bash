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
           src/templates \
           dist/csv \
           dist/images \
           dist/images \
           dist/documents/pdf \
           dist/documents/mails \
           dist/templates/partials
do
    mkdir -p "$dir"
done

# (2) Copy blocklist & proper ages skeletons
cp ../../shared/block-list.json config/
cp ../../shared/proper-ages.json config/

# (3) Convert CSV (if present)
if [ -d ../../"$issue" ]; then

    for file in ../../"$issue"/*.csv; do
        base_name=$(basename "$file")
        iconv --from-code=ISO8859-1 --to-code=UTF-8 "$file" | tr -d '\015' > src/csv/"$base_name"
    done

    rm -rf ../../"$issue"
fi
