import json
import mimetypes
import re
from typing import Optional, Union, List

from rdmo.projects.imports import Import
from rdmo.projects.models import Project, Value
from rdmo.questions.models import Catalog

from .utils import load_config

CONFIG_FILE = "somef-smp.toml"
RDMO_ATTRIBUTE_URI_TEMPLATE = "https://rdmorganiser.github.io/terms/domain/{attribute}"

class SomefImport(Import):

    def check(self):
        if mimetypes.guess_type('application/json'):
            try:
                with open(self.file_name) as f:
                    data = json.loads(f.read())
                    self.somef = data
            except (json.decoder.JSONDecodeError, UnicodeDecodeError):
                return False

            if self.somef:
                return True

    def process(self):
        if self.current_project is None:
            self.catalog = Catalog.objects.first()

            self.project = Project()
            self.project.title = self.somef.get('title')
            self.project.description = self.somef.get('description', '')
            self.project.created = self.somef.get('created', '')
            self.project.catalog = self.catalog
        else:
            self.project = self.current_project
            self.catalog = self.current_project.catalog

        somef_mapping = load_config(CONFIG_FILE)
        for attribute, somef_attr in somef_mapping.items():
            attribute_uri = RDMO_ATTRIBUTE_URI_TEMPLATE.format(attribute=attribute)
            value = self.create_value_for_project(attribute_uri, somef_attr)
            if value is not None:
                self.values.append(value)

    def create_value_for_project(self, attribute_uri: str, somef_attr: Union[List[str], str]) -> Value:
        if not attribute_uri:
            return

        somef_text_value = self.get_value_from_mapping(somef_attr)
        if somef_text_value:
            smp_value = Value(project=self.project,	attribute=self.get_attribute(attribute_uri), text=somef_text_value)
            # breakpoint()
            return smp_value

    def get_value_from_mapping(self, somef_attr) -> Optional[str]:
        if isinstance(somef_attr, str):
            if self.somef.get(somef_attr):
                return self.parse_somef_json_entry(somef_attr)
            return None
        if isinstance(somef_attr, list):
            somef_values = [self.parse_somef_json_entry(v) for v in somef_attr]
            somef_values = [v for v in somef_values if v]
            return somef_values[0] if somef_values else None

        raise TypeError(f"somef_attr must be a list or a string, not {type(somef_attr)}")

    def parse_somef_json_entry(self, somef_attr):
        somef_entry = self.somef.get(somef_attr)
        if isinstance(somef_entry, list):
            return '\n'.join(map(lambda x:x['result']['value'], somef_entry))
        elif isinstance(somef_entry, dict):
            return somef_entry['result']['value']
        else:
            return somef_entry
