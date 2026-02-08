from jinja2 import Template
import datetime
from pathlib import Path

# VS Code Optimized Markdown Template
TEMPLATE = """
# 🧬 Research Pulse: {{ date }}

**Summary:** Found **{{ count }}** papers matching your interests.

---
{% for paper in papers %}
### [{{ paper.title }}]({{ paper.url }})
**{{ paper.authors_full }}** | {{ paper.published }}

> **🤖 AI TL;DR:** {{ paper.ai_summary }}

<details>
<summary><strong>🌐 {% if paper.project_url %}Show Project Demo{% else %}No Project Demo Available{% endif %}</strong></summary>
{% if paper.project_url %}
<p style="width: 100%; height: 400px; overflow: hidden; border: 1px solid #ddd; border-radius: 4px;">
    <iframe src="{{ paper.project_url }}" style="width: 100%; height: 100%; border: none;"></iframe>
</p>
<p><em><a href="{{ paper.project_url }}">Open Project Page ↗</a></em></p>
{% else %}
<p><em>No project demo available.</em></p>
{% endif %}
</details>
<details>
<summary><strong>📝 Show Text Abstract</strong></summary>
{{ paper.abstract }}
</details>
<details {% if paper.tweets %}open{% endif %}>
<summary><strong>🐦 {% if paper.tweets %}Community Signal{% else %}No Community Signal{% endif %}</strong></summary>
{% if paper.tweets %}<ul>{% else %}<p><em>No tweets found for this paper.</em></p>{% endif %}
{% for tweet in paper.tweets %}
<li>
<a href="{{ tweet.url }}">@{{ tweet.author_handle }}</a> (♥ {{ tweet.likes }}): {{ tweet.text | replace('\n', ' ') }}
</li>
{% endfor %}
{% if paper.tweets %}</ul>{% endif %}
</details>
<details>
<summary><strong>📄 Show PDF Preview</strong></summary>
{% if paper.pdf_preview %}
<a href="{{ paper.local_pdf }}">
    <img src="{{ paper.pdf_preview }}" 
         alt="Click to open PDF" 
         style="width: 100%; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;" 
         title="Click to read full PDF">
</a>
{% else %}
<p><em>No preview available. <a href="{{ paper.local_pdf }}">Open PDF</a></em></p>
{% endif %}
</details>

[Open Full PDF ↗]({{ paper.local_pdf }})

---
{% endfor %}
"""

def generate_report(papers, output_path, date=None):
    """
    Generates a Markdown report and saves it to the specified path.
    Creates parent directories if they don't exist.
    """
    # 1. Prepare Template
    template = Template(TEMPLATE)
    if date is None:
        date = datetime.datetime.now()
    date_str = date.strftime("%Y-%m-%d")
    
    markdown_content = template.render(
        papers=papers,
        date=date_str,
        count=len(papers)
    )
    
    # 2. Handle Paths
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 3. Write File
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    return str(path.absolute())