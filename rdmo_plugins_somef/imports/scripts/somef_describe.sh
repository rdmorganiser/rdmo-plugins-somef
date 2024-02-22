#!/bin/bash

# Set up bash python environment
echo "pwd: $(pwd), 0: ${0}, 1: ${1} "
DIR=$(dirname ${0})

# activate py3.9 env from pyenv
. ${PYENV_ROOT}/versions/3.9.18//envs/rdmo-plugins-somef/bin/activate || exit 1

python --version
# pip show somef
echo "Starting somef with ${1}"
somef describe -r ${1} -o $DIR/test.json -t 0.8
