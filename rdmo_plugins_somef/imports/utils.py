from pathlib import Path
import tomli as toml


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
    
# json.loads(jsonfile.read_text()).dump('01.scrape.pretty.json', sort_keys=True, indent=4)