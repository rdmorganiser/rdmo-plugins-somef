from pathlib import Path

import subprocess
from typing import Optional, Union, List

from django import forms
from django.conf import settings
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _

from rdmo.projects.mixins import ProjectImportMixin
from rdmo.projects.imports import Import
from rdmo.projects.models import Project, Value
from rdmo.questions.models import Catalog

from .utils import load_config, read_json_file, add_token_to_somef_config

DEBUG_MODE = True

CONFIG_FILE = "somef-smp.toml"
SOMEF_TEST_JSON = "somef_test.json"
RDMO_ATTRIBUTE_URI_TEMPLATE = "https://rdmorganiser.github.io/terms/domain/{attribute}"
SOMEF_PLUGIN_FORM_TEMPLATE = "plugins/somef/somef_import_form.html"
GITHUB_TEST_REPO = "https://github.com/rdmorganiser/rdmo"
SOMEF_DEPENDENCY_SCRIPT = Path(__file__).parent.joinpath("scripts/somef_describe.sh")
SOMEF_CREATE_ENV_SCRIPT = Path(__file__).parent.joinpath("scripts/create_somef_env.sh")
SOMEF_JSON_OUTPUT_FILE = SOMEF_DEPENDENCY_SCRIPT.parent.joinpath("test.json")
SOMEF_CONFIG_FILE = Path.home().joinpath(".somef/config.json")


class SomefImport(ProjectImportMixin, Import):

    upload = True
    somef_data = None

    class Form(forms.Form):
        repository_url = forms.URLField()

        def __init__(self, *args, **kwargs):

            super().__init__(*args, **kwargs)

            self.fields["repository_url"].widget = forms.URLInput(attrs={"class": "form-control"})

        def clean_dataset(self):
            url = self.data.get("repository_url")
            if not url:
                raise forms.ValidationError(_("Please enter a repository URL."))

        def clean(self, success: Optional[bool]=None, msg: Optional[str]=None):
            if success is None or msg is None:
                return super().clean()
            if success is False:
                self.add_error(None, msg)
            return super().clean()

    def render(self):

        form = self.Form(initial={"repository_url": GITHUB_TEST_REPO})

        return render(
            self.request,
            SOMEF_PLUGIN_FORM_TEMPLATE,
            {"form": form, "project_id": self.current_project.pk},
            status=200,
        )

    def submit(self):
        # dataset_choices = self.request.session[f"{self.class_name}.dataset_choices"]

        form = self.Form(self.request.POST)
        
        success = False
        self.somef_data = None
        self.source_title = 1
        if "cancel" in self.request.POST:
            return redirect("project", self.current_project.id)

        if form.is_valid():
            repository_url = form.cleaned_data.get("repository_url", None)
            self.source_title = repository_url
            somef_data, success, msg = self.prepare_somef_data(repository_url)
            self.somef_data = somef_data

            form.clean(success=success, msg=msg)
            # if somef_data:
                # process = self.process(repository_url=repository_url, somef_data=somef_data)
            # success = bool(somef_data and self.values)
            if somef_data:
                # breakpoint()
                self.process()
                # [i.delete() for i in self.current_project.values.all()]
                # # self.project.values.clear()
                # for value in self.values:
                #     value.save()
                                # store information in session for ProjectCreateImportView
                self.request.session['import_file_name'] = str(SOMEF_JSON_OUTPUT_FILE)
                self.request.session['import_key'] = 'somef'

                # attach questions and current values
                klass = ProjectImportMixin()
                # breakpoint()
                klass.update_values(self.current_project, self.catalog,
                                    self.values, self.snapshots)
                # breakpoint()
                context = {
                        # 'method': 'import_project',
                        'current_project': self.current_project,
                        'source_title': self.source_title,
                        'source_project': self.project,
                        'values': self.values,
                        'snapshots': self.snapshots if not self.current_project else None,
                        'tasks': self.tasks,
                        'views': self.views,
                        'source': self.current_project.id

                    }
                if self.current_project:
                    return render(self.request, 'projects/project_import.html', context)
                    # TODO somehow call the ProjectImportMixin.import_project
                else:
                    return redirect('project_create_import')
        else:
            pass

        return render(
            self.request, SOMEF_PLUGIN_FORM_TEMPLATE, {"form": form, 'source_title': 'URL'}, status=200
        )
    def check(self):
        return True

    def process(self):

        somef_data = self.somef_data

        if self.current_project is None:
            self.catalog = Catalog.objects.first()

            self.project = Project()
            self.project.title = self.somef_data.get('title')
            self.project.description = self.somef_data.get('description', '')
            self.project.created = self.somef_data.get('created', '')
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

    def prepare_somef_data(self, repository_url: str=None):
        msg = ""
        somef_data = None
        success = False
        if repository_url is not None:
            somef_call = self.run_somef_subprocess(repository_url)
            success, msg = self.validate_somef_prcess_call(somef_call)
        if SOMEF_JSON_OUTPUT_FILE.exists():
            somef_data = read_json_file(SOMEF_JSON_OUTPUT_FILE)
            success = True
        else:
            msg += "\n somef call did not produce a json file"
        somef_data = somef_data if somef_data else {}
        return somef_data, success, msg

    def run_somef_subprocess(self, repository_url: str) -> str:
        # TODO call somef to create json from repository_url
        # breakpoint()
        # breakpoint()
        if DEBUG_MODE:
            return "Debug mode, will load from json file. success"
        if not SOMEF_CONFIG_FILE.exists():
            somef_create_env = subprocess.check_output(["/bin/bash", f"{SOMEF_CREATE_ENV_SCRIPT}",
                                     ], text=True)

        add_token_to_somef_config(SOMEF_CONFIG_FILE, settings.GITHUB_ACCESS_TOKEN)

        call_cmd = ["/bin/bash", f"{SOMEF_DEPENDENCY_SCRIPT}", repository_url]
        try:
            somef_call = subprocess.check_output(call_cmd, text=True)
        except subprocess.CalledProcessError as e:
            somef_call = f"ERROR somef call failed: {e}"

        return somef_call
        
    def validate_somef_prcess_call(self, somef_call: str):
        # breakpoint()
        if somef_call:
            if not "ERROR" in somef_call:
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
            if self.somef_data.get(somef_attr):
                return self.parse_somef_json_entry(somef_attr)
            return None
        if isinstance(somef_attr, list):
            somef_values = [self.parse_somef_json_entry(v) for v in somef_attr]
            somef_values = [v for v in somef_values if v]
            return somef_values[0] if somef_values else None

        raise TypeError(f"somef_attr must be a list or a string, not {type(somef_attr)}")


    def parse_somef_json_entry(self, somef_attr):
        somef_entry = self.somef_data.get(somef_attr)
        if isinstance(somef_entry, list):
            return '\n'.join(map(lambda x: x['result']['value'], somef_entry))
        elif isinstance(somef_entry, dict):
            return somef_entry['result']['value']
        else:
            return somef_entry
