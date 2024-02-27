from pathlib import Path

from typing import Optional, Union, List

from django import forms
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _

from rdmo.projects.mixins import ProjectImportMixin
from rdmo.projects.imports import Import
from rdmo.projects.models import Project, Value
from rdmo.questions.models import Catalog

from .utils import load_config, read_json_file
from .helpers import run_somef_subprocess, validate_somef_process_call, get_value_from_mapping

DEBUG_MODE = True

CONFIG_FILE = "somef-smp.toml"
SOMEF_TEST_JSON = "somef_test.json"
RDMO_ATTRIBUTE_URI_TEMPLATE = "https://rdmorganiser.github.io/terms/domain/{attribute}"
SOMEF_PLUGIN_FORM_TEMPLATE = "plugins/somef/import_from_github_url_form.html"
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
        
        self.request.session['post_import_selection'] = False
        success = False
        self.somef_data = None
        self.source_title = 1
        if "cancel" in self.request.POST:
            return redirect("project", self.current_project.id)

        if not form.is_valid() and not 'repository_url' in self.request.session:
            return render(
            self.request, SOMEF_PLUGIN_FORM_TEMPLATE, {"form": form, 'source_title': 'URL'}, status=200
        )
        if "repository_url" in form.cleaned_data:
            repository_url = form.cleaned_data.get("repository_url", None)
        elif 'repository_url' in self.request.session:
            repository_url = self.request.session['repository_url']
        else:
            repository_url = ""

        self.source_title = repository_url
        somef_data, success, msg = self.prepare_somef_data(repository_url)
        self.somef_data = somef_data
        form.clean(success=success, msg=msg)

        if not somef_data:
            return redirect('project', self.current_project.id)

        # if somef_data:
            # process = self.process(repository_url=repository_url, somef_data=somef_data)
        # success = bool(somef_data and self.values)
        # if somef_data:
        # breakpoint()
        self.process()
        # [i.delete() for i in self.current_project.values.all()]
        # # self.project.values.clear()
        # for value in self.values:
        #     value.save()
                        # store information in session for ProjectCreateImportView
        self.request.session['import_file_name'] = str(SOMEF_JSON_OUTPUT_FILE)
        self.request.session['import_key'] = 'somef'
        self.request.session['repository_url'] = repository_url

        # attach questions and current values
        klass = ProjectImportMixin()
        # breakpoint()
        klass.update_values(self.current_project, self.catalog,
                            self.values, self.snapshots)
        # breakpoint()
        context = {
                # 'method': 'import_project',
                'repository_url': repository_url,
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
            attribute_uri_keys = [i for i in self.request.POST.keys() if i.startswith('http')]
            clean_attri_uris = [i.split('[')[0] for i in attribute_uri_keys]
            # breakpoint()
            selected_values = [i for i in self.values if i.attribute.uri in clean_attri_uris]
            if selected_values:
                self.request.session['post_import_selection'] = True
                [i.save() for i in selected_values]
                return redirect('project', self.current_project.id)
            else:
                return render(self.request, 'projects/project_import.html', context)
        else:
            return redirect('project_create_import')

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
            somef_call = run_somef_subprocess(repository_url, somef_config_file=SOMEF_CONFIG_FILE, 
                                              create_env_script=SOMEF_CREATE_ENV_SCRIPT,
                                              dependency_script=SOMEF_DEPENDENCY_SCRIPT, debug=DEBUG_MODE)
            success, msg = validate_somef_process_call(somef_call)
        if SOMEF_JSON_OUTPUT_FILE.exists():
            somef_data = read_json_file(SOMEF_JSON_OUTPUT_FILE)
            success = True
        else:
            msg += "\n somef call did not produce a json file"
        somef_data = somef_data if somef_data else {}
        return somef_data, success, msg


    def create_value_for_project(self, attribute_uri: str, somef_attr: Union[List[str], str]) -> Value:
        if not attribute_uri:
            return

        somef_text_value = get_value_from_mapping(self.somef_data, somef_attr)
        if somef_text_value:
            smp_value = Value(project=self.project,	attribute=self.get_attribute(attribute_uri), text=somef_text_value)
            # breakpoint()
            return smp_value
