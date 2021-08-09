#!/bin/bash

##
# Detects all entries without proper age recommendation for given issue identifier
#
# Usage:
# bash detect_age_ratings.bash `ISSUE`
#
##

issue=$1

root_directory=$(dirname "$(dirname "$0")")
cd "$root_directory"/issues/"$issue"/dist/csv || exit

newline=$'\n'
result=""

while IFS= read -r line; do
    # Extract ISBN & age rating
    isbn=$(echo "$line" | cut -d "," -f 1)
    age_rating=$(echo "$line" | cut -d "," -f 2)

    # Save result
    result+="Improper age rating for $isbn: $age_rating${newline}"

# (1) Inject all `.csv` files
# (2) Choose only entries from 'ISBN' and 'age recommendation' columns
# (3) Select lines containing strings indicating improper age ratings
# (4) Remove duplicates
done < <(cat -- *.csv | csvcut -c ISBN,Altersempfehlung | grep "Altersangabe\|bis" | uniq | sed "/ISBN,Altersempfehlung/d")


file=../../meta/age-ratings.txt

# Check if improper age ratings exists ..
if [ -z "$result" ]; then
    # .. otherwise there isn't anything to report back, really
    result="No improper age ratings found!"
fi

echo "$result" >$file
