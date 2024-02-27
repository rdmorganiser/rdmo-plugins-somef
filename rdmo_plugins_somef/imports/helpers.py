from pathlib import Path

import subprocess
from typing import Optional

from django.conf import settings

from .utils import add_token_to_somef_config


def run_somef_subprocess(repository_url: str, somef_config_file: Optional[Path]=None, create_env_script: Optional[Path]=None,
                        dependency_script: Optional[Path]=None,
                        debug=False) -> str:
    # TODO call somef to create json from repository_url
    if debug or somef_config_file is None:
        return "Debug mode, will load from json file. success"
    somef_create_env_output = ''
    if not somef_config_file.exists():
        somef_create_env_output = subprocess.check_output(["/bin/bash", f"{create_env_script}",
                                    ], text=True)

    add_token_to_somef_config(somef_config_file, settings.GITHUB_ACCESS_TOKEN)

    call_cmd = ["/bin/bash", f"{dependency_script}", repository_url]
    try:
        somef_call = subprocess.check_output(call_cmd, text=True)
    except subprocess.CalledProcessError as e:
        somef_call = f"ERROR somef call failed: {e}"
        somef_call += f"\n{somef_create_env_output}"

    return somef_call


def validate_somef_process_call(somef_call: str):
    if somef_call:
        if "ERROR" not in somef_call:
            _msg = f"somef call successful: {somef_call}"
            return True, _msg
        else:
            print("somef call returned an error")
            _msg = f"somef call returned an error: {somef_call}"
            return False, _msg
    else:
        _msg = f"somef call script failed: {somef_call}"
        print("somef call script failed")
        return False, _msg

def parse_somef_json_entry(somef_data: dict, somef_attr) -> Optional[str]:
    somef_entry = somef_data.get(somef_attr)
    if isinstance(somef_entry, list):
        return '\n'.join(map(lambda x: x['result']['value'], somef_entry))
    elif isinstance(somef_entry, dict):
        return somef_entry['result']['value']
    else:
        return somef_entry

def get_value_from_mapping(somef_data: dict, somef_attr) -> Optional[str]:
    if isinstance(somef_attr, str):
        if somef_data.get(somef_attr):
            return parse_somef_json_entry(somef_data, somef_attr)
        return None
    if isinstance(somef_attr, list):
        somef_values = [parse_somef_json_entry(somef_data, v) for v in somef_attr]
        somef_values = [v for v in somef_values if v]
        return somef_values[0] if somef_values else None

    raise TypeError(f"somef_attr must be a list or a string, not {type(somef_attr)}")


