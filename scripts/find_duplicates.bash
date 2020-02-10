#!/bin/bash

##
# Finds all duplicate entries for given issue identifier
#
# Usage:
# bash find_duplicates.bash `ISSUE`
#
##

issue="$1"

root_directory=$(dirname "$(dirname "$0")")
cd "$root_directory"/issues/"$issue"/src/csv || exit

isbns=()

while IFS= read -r isbn; do
    isbns+=("$isbn")

    # Remove surrounding quotes
    isbn="${isbn%\"}"
    isbn="${isbn#\"}"

    # Search for files containing ISBN, remove duplicate file entries & put them all in one line
    duplicate=$(grep -l "$isbn" ./*.csv | uniq | paste -sd "" -)

    # Remove leading './' and trailing '.csv'
    duplicate="${duplicate:2:-4}"

    # Replace '.csv./' with ' & '
    duplicate=${duplicate//.csv.\//\ &\ }

    # Print the result
    printf "Duplicate found for %s in $duplicate\\n" "$isbn"

# Inject all duplicate entries across `.csv` files, cutting out their ISBNs
done < <(awk '_[$0]++' ./*.csv | awk -F ";" '{ print $4 }')


##
# Or, to look at those manually:
#
# awk '_[$0]++' *.csv > dupes.txt
# awk -F ";" '{ print $4 }' dupes.txt
# column -s\; -t < dupes.txt | less -#2 -N -S
#
# .. but why bother, right?
##
