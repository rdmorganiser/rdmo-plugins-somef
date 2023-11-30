#!/bin/bash

# Set up bash python environment
echo "pwd: $(pwd), 0: ${0}, 1: ${1} "

source $(dirname ${0})/env/bin/activate

python --version
# pip show somef
echo "Starting somef with ${1}"
somef describe -r ${1} -o test.json -t 0.8
