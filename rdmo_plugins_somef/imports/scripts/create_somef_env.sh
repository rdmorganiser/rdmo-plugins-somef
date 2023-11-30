#!/bin/bash

ENV_DIR=env
make_python3_env () {
    if [[ -d "$ENV_DIR" ]]; then
        echo "There is already and env there and it will be re-used, $ENV_DIR"
    else
        echo "Will setup new environment"
        python3.9 -m venv $ENV_DIR
    fi
    source $ENV_DIR/bin/activate
}

make_python3_env

pip install somef
# pip install git+https://github.com/KnowledgeCaptureAndDiscovery/somef.git@dev

somef configure -a