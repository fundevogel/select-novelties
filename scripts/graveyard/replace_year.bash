#!/bin/bash

##
# Replaces all instances of '%%YEAR%%' with the current year
#
# Usage:
# bash replace_year.bash `ISSUE`
#
##

issue=$1

root_directory=$(dirname "$(dirname "$0")")
cd "$root_directory"/issues/"$issue"/dist/templates || exit

year=$(date +'%Y')

sed -i "s/%%YEAR%%/$year/g" ./edited.sla
