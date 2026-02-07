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

{% if paper.project_url %}
<details>
<summary><strong>🌐 Show Project Demo</strong></summary>
<br>
<div style="width: 100%; height: 400px; overflow: hidden; border: 1px solid #ddd; border-radius: 4px;">
    <iframe src="{{ paper.project_url }}" style="width: 100%; height: 100%; border: none;"></iframe>
</div>
<p><em><a href="{{ paper.project_url }}">Open Project Page ↗</a></em></p>
</details>
{% endif %}

<details>
<summary><strong>📄 Show PDF Preview</strong></summary>
<br>
<a href="{{ paper.local_pdf }}" target="_blank">
    <img src="{{ paper.pdf_preview }}" 
         alt="Click to open PDF" 
         style="width: 100%; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;" 
         title="Click to read full PDF">
</a>
<p align="center"><em>(Click image to open full PDF)</em></p>
</details>

<details>
<summary><strong>📝 Show Text Abstract</strong></summary>
<br>
{{ paper.abstract }}
</details>

{% if paper.tweets %}
**🐦 Community Signal**
{% for tweet in paper.tweets %}
* **[@{{ tweet.author_handle }}]({{ tweet.url }})** (♥ {{ tweet.likes }}): {{ tweet.text | replace('\n', ' ') }}
{% endfor %}
{% endif %}

---
{% endfor %}
"""

def generate_report(papers, output_path):
    """
    Generates a Markdown report and saves it to the specified path.
    Creates parent directories if they don't exist.
    """
    # 1. Prepare Template
    template = Template(TEMPLATE)
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
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