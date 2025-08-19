# {{ objname }}

```{eval-rst}
.. currentmodule:: {{ module }}

.. autoclass:: {{ objname }}
   :members:
   :undoc-members:
   :show-inheritance:
   :inherited-members:
   :special-members: __init__, __str__, __repr__
```

{% if methods %}
## Methods

```{eval-rst}
.. autosummary::
   :nosignatures:
{% for item in methods %}
   ~{{ name }}.{{ item }}
{%- endfor %}
```
{% endif %}

{% if attributes %}
## Attributes

```{eval-rst}
.. autosummary::
{% for item in attributes %}
   ~{{ name }}.{{ item }}
{%- endfor %}
```
{% endif %}
