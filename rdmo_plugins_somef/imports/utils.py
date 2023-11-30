from pathlib import Path
import tomli as toml
import json

def load_config(file_name):
    toml_file = Path(__file__).parent / file_name
    try:
        toml_dict = toml.loads(toml_file.read_bytes().decode())
        return toml_dict
    except FileNotFoundError as exc:
        raise exc from exc
    except toml.TOMLDecodeError as exc:
        raise toml.TOMLDecodeError(
            "\nThe {} file is not a valid TOML file.\n\t{}".format(toml_file, exc)
        ) from exc
    
def read_json_file(json_file):
    try:
        with open(Path(json_file)) as f:
            data = json.loads(f.read())
        return data
    except (json.decoder.JSONDecodeError, UnicodeDecodeError):
        return None
    except FileNotFoundError as exc:
        print(f"File {json_file} not found")
        return None
