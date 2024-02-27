#!/bin/bash

# activate py3.9 env from pyenv
. ${PYENV_ROOT}/versions/3.9.18//envs/rdmo-plugins-somef/bin/activate || exit 1

python --version

pip install somef
# pip install git+https://github.com/KnowledgeCaptureAndDiscovery/somef.git@dev

somef configure -a