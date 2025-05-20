# utils/render_minutes.py
import yaml, textwrap
from pathlib import Path
from jinja2 import Template

_MD_TEMPLATE = Template(textwrap.dedent("""
### {{ day }}

**Themes**  
{% for t in data.themes %}* {{ t }}{% endfor %}

---

| ID | Decision | Rationale | Status |
|----|----------|-----------|--------|
{% for d in data.decisions -%}
| {{ d.id }} | **{{ d.title }}**<br>{{ d.action }} | {{ d.rationale|replace('\n',' ') }} | {{ d.status }} |
{% endfor %}
"""))

def render_md(yaml_path: Path) -> str:
    data = yaml.safe_load(yaml_path.read_text())
    return _MD_TEMPLATE.render(day=yaml_path.stem[-8:], data=data)
