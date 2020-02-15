#!/bin/bash

##
# Counts total books for given issue identifier
#
# Usage:
# bash count_books.bash `ISSUE`
#
##

path="$1"

cd "$path/../csv" || exit

entries=$(cat ./*.csv | wc -l)
headers=$(ls | wc -l)

total=$(("$entries" - "$headers"))

printf "%s" "$total"
