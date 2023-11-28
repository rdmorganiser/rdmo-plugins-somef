# RDMO Plugin SOMEF
This plugin imports extracted metadata from the [SOMEF](https://github.com/KnowledgeCaptureAndDiscovery/somef) into RDMO for the SMP catalogue. It can be used for the automated transfer of information in GitHub repositories to RDMO.

## Setup

Install the plugin in your RDMO virtual environment using pip (directly from GitHub):
```bash
pip install git+https://github.com/rdmorganiser/rdmo-plugins-somef.git
```
The dependencies [`somef`](https://pypi.org/project/somef/) and [`tomli`](https://pypi.org/project/tomli/) will be installed automatically.
Add the `rdmo_plugins_somef` app to your `INSTALLED_APPS` in `config/settings/local.py``:
```py
from . import INSTALLED_APPS
INSTALLED_APPS = ['rdmo_plugins_somef'] + INSTALLED_APPS
```

Add the export plugins to the PROJECT_IMPORTS in config/settings/local.py:
```py
from django.utils.translation import gettext_lazy as _
from . import PROJECT_IMPORTS

PROJECT_IMPORTS += [
    ('somef', _('as somef JSON'), 'rdmo_plugins_somef.imports.somef.SomefImport')
]
```