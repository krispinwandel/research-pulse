# 🧬 ResearchPulse

**ResearchPulse** is an automated, AI-powered research discovery tool that keeps you on the cutting edge of your field by generating a daily digest of the most relevant and impactful papers from Arxiv, tailored to your specific research interests.

It fetches the latest papers from Arxiv and filters them semantically using Google Gemini based on your customized research interests, and generates a rich, interactive Markdown report optimized for VS Code.

<img src="./assets/research_pulse.gif" style="max-height: 500px; width: auto;">

## ✨ Features

* **🧠 Semantic Filtering:** Uses **Gemini 3 Flash Preview** to analyze paper abstracts and select only those that match your deep learning profile (e.g., "Foundational Vision" ✅ vs. "Applied Medical Imaging" ❌).
* **📝 AI Summaries:** Generates a single-sentence "TL;DR" for each paper, focusing strictly on the method's novelty and contribution.
* **🌐 Project Demos:** Detects project websites and embeds them as interactive iframes.
* **🖼️ Auto PDF-Download:** Automatically downloads PDFs and renders a **PDF Preview** directly in the report.
* **🐦 Community Signal:** Scans **X (Twitter)** to find if the paper is being discussed by key researchers.
* **⚡ VS Code Optimized:** The output is a clean Markdown file with collapsible sections (`<details>`) for abstracts, PDFs, and demos, keeping your daily feed clutter-free.

## 🚀 Installation

### Prerequisites
* Python 3.9+
* [uv](https://github.com/astral-sh/uv) (Recommended) or pip
* **Google Gemini API Key** for semantic filtering and summarization
* **X (Twitter) Bearer Token** for social signals

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/krispinwandel/research-pulse.git
    cd research-pulse
    ```

2.  **Install dependencies:**
    ```bash
    uv sync
    ```

3.  **Configure:**
    Create a `config.yaml` file in the root directory (see [Configuration](#configuration) below).

4.  **Environment Variables:**
    Create a `.env` file for your keys:
    ```bash
    GEMINI_API_KEY="your_key_here"
    X_BEARER_TOKEN="your_token_here" # Optional
    ```

## ⚙️ Configuration

Edit `config.yaml` to tailor the feed to your research interests. As an example, here’s a configuration for someone focused on **Foundational Computer Vision** and **Geometric Deep Learning**:

```yaml
# Research Configuration
research:
  lookback_days: 2           # How far back to search arXiv
  max_raw_papers: 100        # Initial fetch size
  max_selected_papers: 15    # Final curated list size
  require_project_link: true # If true, discards papers without code/web links
  categories:
    - "cs.CV"
    - "cs.RO"
    - "cs.LG"

# User Profile (The "Brain" of the filter)
interests: |
  I am a researcher focused on **Foundational Computer Vision** and **Geometric Deep Learning**.
  
  CORE INTERESTS:
  - **Foundational Vision:** Self-supervised learning (DINOv3, MAE), robust image representations.
  - **3D & 4D Representations:** NeRFs, 3D Gaussian Splatting, 4D space-time.
  
  STRICT EXCLUSIONS:
  - **Applied Papers:** Traffic control, agriculture, medical imaging.
  - **High-Level Robotics:** End-to-End VLA (unless novel visual rep).

# Output Settings
output:
  root_dir: "./research_reports"
  filename_prefix: "daily_pulse"
```
