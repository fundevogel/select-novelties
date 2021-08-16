#!/bin/bash

##
# Counts total books for given issue identifier
#
# Usage:
# bash count_books.bash `ISSUE`
#
##

issue=$1

root_directory=$(dirname "$(dirname "$0")")
cd "$root_directory"/issues/"$issue"/dist/csv || exit

# shellcheck disable=SC2012
headers=$(ls | wc -l)
entries=$(cat ./*.csv | wc -l)

total=$(("$entries" - "$headers"))

printf "%s" "$total"
