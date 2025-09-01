# {{ fullname }}

```{eval-rst}
.. automodule:: {{ fullname }}
   :members:
   :undoc-members:
   :show-inheritance:
```

{% if classes %}
## Classes

```{eval-rst}
.. autosummary::
   :toctree:
   :template: class.md
{% for item in classes %}
   {{ item }}
{%- endfor %}
```
{% endif %}

{% if functions %}
## Functions

```{eval-rst}
.. autosummary::
   :toctree:
{% for item in functions %}
   {{ item }}
{%- endfor %}
```
{% endif %}

{% if exceptions %}
## Exceptions

```{eval-rst}
.. autosummary::
   :toctree:
{% for item in exceptions %}
   {{ item }}
{%- endfor %}
```
{% endif %}
