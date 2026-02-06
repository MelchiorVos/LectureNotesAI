# Tutor

Turn lecture slides into AI-explained Notion pages — automatically.

Drop a PDF, pick a course, and Tutor processes every slide through OpenAI, generates structured explanations with proper math formatting, then pushes everything to Notion — complete with a lecture summary and practice exam questions.

**Example output (Notion page):**
- Reinforcement Learning — Lecture 2: https://pie-snowman-06c.notion.site/Lecture2-2ff9e9b4f80d81b1a9afc7df1d264d01?source=copy_link

![Launcher](screenshots/launcher.png)

## Features

- **Drag-and-drop PDF input** — launcher with file browser and drag-and-drop support
- **Slide review** — preview each slide and exclude ones you don't need explained
- **Structured AI explanations** — formulas are broken down with symbol definitions and intuition
- **Reasoning-first explanations** — uses a reasoning model that thinks through each slide before answering
- **KaTeX math** — all math is rendered as Notion equations, not plain text
- **Lecture summary** — auto-generated at the end of each lecture
- **Practice questions** — 5 exam-style questions with answers
- **Conversation memory** — the model sees all previous slides, so explanations build on each other

## How It Works

1. **Launch** — run `python main.py` to open the GUI
2. **Select PDF** — drop a lecture PDF or click to browse
3. **Choose course** — pick from courses configured in your `.env`
4. **Review slides** *(optional)* — toggle slides to skip trivial ones

![Slide Selector](screenshots/slide_selector.png)

5. **Processing** — each slide is analyzed sequentially (for conversation context), uploaded to Notion in parallel

> If you exclude slides during review, Tutor still uploads those slide images to Notion so the lecture page is a complete, single source of truth. Excluded slides simply won’t include an AI explanation.
6. **Result** — a new Notion page appears under your course with every slide image, its explanation, a summary, and practice questions

## Setup

### Prerequisites

- Python 3.12+
- An [OpenAI API key](https://platform.openai.com/api-keys)
- A Notion integration (see below)

### Notion Integration Setup

1. Go to [notion.so/profile/integrations](https://www.notion.so/profile/integrations) and click **New integration**
2. Give it a name (e.g. "UniTutor"), select your workspace, and save
3. Copy the **Internal Integration Secret** — this is your `NOTION_API_KEY`
4. Open the Notion page you want to use as a course root
5. Click **···** (top-right) → **Connections** → **Add connection** → select the integration you just created

<img src="screenshots/notion_connection.png" width="360" alt="Adding a Notion connection">

> Repeat step 4–5 for each course page. Without the connection, the API cannot write to the page.

### Install

```bash
git clone https://github.com/YOUR_USERNAME/Tutor.git
cd Tutor
pip install -r requirements.txt
```

### Configure

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
NOTION_API_KEY=ntn_...

# One entry per course — the page ID is where lecture sub-pages are created
NOTION_PAGE_REINFORCEMENT_LEARNING=abc123...
NOTION_PAGE_MACHINE_LEARNING=def456...
```

> **Finding your Notion page ID:** open the page in Notion, copy the URL — the 32-character hex string at the end is the page ID. Make sure your integration is connected to that page.

Course names are derived from the env var names: `NOTION_PAGE_REINFORCEMENT_LEARNING` → "Reinforcement Learning" in the dropdown.

### Run

```bash
python main.py
```

## Project Structure

```
Tutor/
├── main.py                  # Entry point
├── config.py                # Settings, env helpers, pipeline context
├── requirements.txt
├── prompts/
│   └── system.txt           # System prompt template (edit without touching code)
├── frontend/
│   ├── theme.py             # Shared colors and window helpers
│   ├── launcher.py          # Launcher GUI
│   └── slide_selector.py    # Slide exclusion GUI
├── backend/
│   ├── openai_client.py     # OpenAI API calls with retry logic
│   ├── notion_client.py     # Notion uploads, block building, AST conversion
│   └── pdf_parser.py        # PDF → images
└── pipeline/
    └── processor.py         # Orchestration — ties backend together
```

## Configuration

Key settings in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `OPENAI_SLIDE_MODEL` | `gpt-5.2` | Model for slide analysis |
| `OPENAI_SUMMARY_MODEL` | `gpt-5-mini` | Model for summary and exam questions |
| `PDF_ZOOM` | `2.0` | Render quality for PDF pages |
| `RETRY_ATTEMPTS` | `3` | API retry count with exponential backoff |

## Customizing the Prompt

Edit `prompts/system.txt` to change how the AI explains slides. The `{course_name}` placeholder is replaced at runtime. No code changes needed.
