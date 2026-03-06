# CourseForge — AI Course Generation Engine

CourseForge is an AI-driven content generation engine that produces dynamic, student-specific educational materials at scale. Give it a subject, a student persona, and an instructor profile — and it generates a complete, structured university-level course: outlines, introductions, module summaries, and full chapter content — then publishes it as an organized Notion webpage for easy sharing.

The core idea: use LLMs as domain experts to build contextual knowledge packs for any subject, generating personalized learning materials that adapt to the student's background and the instructor's teaching style.

Essentially, give it a topic, tell it what you already know and get back a comprehensive course.

---

## The Problem

Educational content creation is slow, expensive, and rarely personalized. Educators are expected to deliver high-quality, engaging materials tailored to individual learning styles — but they're working with generic tools, limited time, and fixed resources. When materials fail to connect with students, engagement drops and learning suffers.

CourseForge approaches this differently. Instead of retrofitting AI onto existing content workflows, it treats **AI as the content generation engine from the ground up** — designing AI-driven workflows where each stage of course creation is powered by LLMs that act as subject matter experts, producing adaptive content that reflects both the student's needs and the instructor's pedagogy.

---

## How It Works

CourseForge runs a **4-stage AI-driven workflow** where each stage feeds into the next, progressively building a complete course from a single input. The LLM acts as a domain expert at every stage, generating content that is contextually grounded in the student persona and instructor profile.

```
Subject Input → Course Outline → Module Summaries → Chapter Content → Notion Publishing
```

**Stage 1 — Outline Generation**
A course subject is combined with a student persona and a prompt template to generate a structured course outline — modules, learning objectives, key topics, and activities — tailored to the student's background and experience level.

**Stage 2 — Introduction Generation**
The raw outline is fed back into the AI with an introduction template to produce a course overview covering prerequisites, learning outcomes, and a module-by-module roadmap. The LLM uses the full course context to ensure coherence across the generated structure.

**Stage 3 — Module Summary Generation**
Each module from the outline is expanded individually into detailed summaries with chapter breakdowns, learning goals, and suggested activities. The AI acts as a domain expert for the subject area, producing content that adapts to the specified depth and pedagogical style. One API call per module.

**Stage 4 — Chapter Content Generation**
Each chapter summary is expanded into full lecture-ready content — explanations, examples, and exercises — using an instructor persona for tone and depth calibration. This stage produces the bulk of the learning materials, generating student-specific content that reflects both the subject matter and the target learner's needs.

Once generation completes, all content is published to Notion as an organized page hierarchy.

---

## Course Structure in Notion

CourseForge publishes courses with a three-level hierarchy:

### Course Home Page
```
📄 Course Title
├── Introduction
│   └── [course overview, outcomes, prerequisites]
├── Module 1: [Title]
│   ├── [module description with chapter summaries]
│   └── 📄 Module 1 sub-page
├── Module 2: [Title]
│   ├── [module description]
│   └── 📄 Module 2 sub-page
└── 📄 All Chapters (flat index of every chapter)
```

### Inside a Module Page
```
📄 Module 1: [Title]
├── Overview
│   └── [module overview paragraph]
├── ▼ Chapter 1: [Title] (expandable toggle)
│   ├── ▼ Outline (Objective, Key Topics, Activities)
│   └── ▼ Content (link to chapter page)
├── ▼ 1.1: [Sub-topic] (expandable toggle)
│   ├── ▼ Outline
│   └── ▼ Content (link to sub-section page)
├── ▼ 1.2: [Sub-topic]
│   └── ...
└── ▼ Chapter 2: [Title]
    └── ...
```

### Chapter Pages (inside All Chapters)
```
📄 M1 - Chapter 1: [Title]
└── [Full generated lecture content — headings, paragraphs, bullets, examples]

📄 M1 - 1.1: [Sub-topic]
└── [Sub-section content]
```

Each chapter and sub-section has its own dedicated page with the full generated content, linked from the Content toggle inside the module page. The "All Chapters" page provides a flat index for browsing without navigating the module structure.

---

## Model-Agnostic Backend

CourseForge supports multiple AI backends through a simple toggle:

```python
USE_BACKEND = "ollama"   # or "gemini"
```

| Backend | Model | Use Case |
|---------|-------|----------|
| Ollama (local) | Any model via Ollama (Llama 3, Mistral, etc.) | Development, offline use, no API costs |
| Google Gemini | gemini-2.0-flash / gemini-2.5-flash | Production, faster generation |

Switching backends is a one-line change. The pipeline architecture is model-agnostic by design — prompt engineering is handled through the template system, not hardcoded to any specific model's format.

---

## Prompt Template System — Context Packs

CourseForge uses a **template-driven prompt architecture** that functions as a set of context packs. Instead of hardcoding prompts in Python, each pipeline stage composes its prompt from reusable `.docx` template files in the `Docs/` directory. These templates encapsulate domain knowledge, pedagogical strategy, and student context — giving the LLM the information it needs to act as a subject matter expert:

| Template | Purpose |
|----------|---------|
| `Subject.docx` | The course topic — the only file you change per run |
| `Student Introduction File.docx` | Target student persona (background, learning style) |
| `Instructor Introduction File.docx` | Instructor persona (teaching style, expertise level) |
| `Outlines Prompt Skeleton.docx` | Structure instructions for outline generation |
| `Course Introduction Skeleton.docx` | Instructions for writing the course introduction |
| `Course Outline Prompt Skeleton.docx` | Instructions for expanding outlines into module summaries |
| `Chapter Prompt Skeleton.docx` | Instructions for generating full chapter content |

This means you can customize the AI's behavior — tone, depth, structure, pedagogy — by editing Word documents, not code. The template system is the core of CourseForge's AI-driven workflow design: prompt engineering is treated as a first-class configuration layer, not an afterthought buried in source code.

---

## Reliability Features

### Checkpoint & Resume
The pipeline saves progress after each major stage and after every individual chapter generation. If a crash or timeout occurs at chapter 13 of 25, rerunning the script picks up at chapter 13 — no regeneration of completed work.

```bash
python course_gen_main.py          # resumes from last checkpoint
python course_gen_main.py --fresh  # clears checkpoints, starts from scratch
```

### Retry with Backoff
API timeouts and rate limit errors are caught and retried automatically (3 attempts, 10-30 second backoff). The pipeline logs each retry and continues without manual intervention.

### Rate Limiting
Notion API calls are rate-limited with delays between requests to stay within API quotas. Block appends are batched at 100 per call (Notion's limit).

---

## Project Structure

```
courseforge/
├── sync/                        # Working engine
│   ├── course_gen_main.py       # Entry point & pipeline orchestration
│   ├── Gemini_Responses.py      # LLM backend (Ollama/Gemini toggle)
│   ├── Markdown_Function.py     # Text formatting & parsing utilities
│   ├── Notion_Update.py         # Notion SDK integration (content publishing)
│   ├── checkpoints/             # Auto-generated progress saves
│   └── Docs/                    # Prompt templates (context packs)
│       ├── Subject.docx
│       ├── Student Introduction File.docx
│       ├── Instructor Introduction File.docx
│       ├── Outlines Prompt Skeleton.docx
│       ├── Course Outline Prompt Skeleton.docx
│       ├── Course Introduction Skeleton.docx
│       └── Chapter Prompt Skeleton.docx
├── async/                       # Async version (WIP)
├── .env                         # API keys (not committed)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup

### Prerequisites

- Python 3.10+
- A Notion account with an integration configured
- One of: Ollama running locally OR a Google AI Studio API key

### 1. Clone & Install

```bash
git clone https://github.com/your-username/courseforge.git
cd courseforge
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file at the repo root:

```env
# Google Gemini (optional — only needed if using Gemini backend)
GOOGLE_API_KEY=your-gemini-api-key

# Notion Integration (required)
NOTION_TOKEN=your-notion-integration-secret
NOTION_COURSES_PAGE_ID=your-courses-main-page-id
```

**Setting up Notion:**
1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) → New Integration
2. Name it "CourseForge", select your workspace, enable Read + Update + Insert content
3. Copy the Internal Integration Secret (starts with `ntn_`)
4. In Notion, create a "CourseForge Results" page → `...` menu → Connections → add your integration
5. Copy the page ID from the URL (the 32-character hex string after the page name)

**Setting up Ollama (for local generation):**
```bash
ollama pull llama3.1:70b    # or any model you prefer
ollama serve                # start the server
```

### 3. Configure Your Course

Edit `sync/Docs/Subject.docx` with the course topic you want to generate. For example:

> *"Introduction to Machine Learning — covering supervised and unsupervised learning, neural networks, and practical applications in Python"*

Optionally customize the student and instructor personas in their respective `.docx` files.

### 4. Choose Your Backend

In `sync/Gemini_Responses.py`, set the backend:

```python
USE_BACKEND = "ollama"    # local generation, no API costs
# USE_BACKEND = "gemini"  # cloud generation, faster
```

If using Ollama, set your model:
```python
OLLAMA_MODEL = "llama3.1:70b"  # match your installed model
```

### 5. Run

```bash
cd sync
python course_gen_main.py
```

The pipeline logs progress to the console. A typical course takes 10-15 minutes with a cloud API or 30-60+ minutes with a local model, depending on course size and model speed.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| AI Backend | Ollama (local) or Google Gemini (cloud) — switchable |
| Content Publishing | Notion API (official `notion-client` SDK) |
| Runtime | Python 3.10+ |
| Prompt Templates | `.docx` files (read via `docx2txt`) |
| Checkpointing | Pickle-based per-stage and per-chapter saves |
| Retry Logic | Custom retry with backoff on API errors |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    CourseForge Engine                     │
│                                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────┐ │
│  │ Outline  │──→│ Module   │──→│ Chapter  │──→│Notion│ │
│  │Generator │   │Expander  │   │Generator │   │Publish│ │
│  └──────────┘   └──────────┘   └──────────┘   └──────┘ │
│       ▲               ▲              ▲                   │
│       │               │              │                   │
│  ┌─────────────────────────────────────────┐             │
│  │     Prompt Template System (Context     │             │
│  │     Packs: Subject + Personas +         │             │
│  │     Skeletons)                          │             │
│  └─────────────────────────────────────────┘             │
│                                                          │
│  ┌─────────────────────────────────────────┐             │
│  │         Infrastructure Layer            │             │
│  │  Checkpoint/Resume · Retry · Rate       │             │
│  │  Limiting · Backend Toggle              │             │
│  └─────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────┘
```

---

## Customization & Personalization

### How Content Adapts

CourseForge generates personalized learning materials by combining three context dimensions at prompt construction time:

- **Student persona** — The student's experience level, background, and learning style. Changing the target audience from "undergraduate CS student" to "working professional" or "high school AP student" shifts the content depth, vocabulary, and examples accordingly.
- **Instructor persona** — The instructor's teaching style (lecture-heavy, Socratic, example-driven) and subject expertise. The AI adapts chapter output to match the instructor's pedagogical approach.
- **Structural requirements** — Constraints like "always include 3 practice problems per chapter" or "add a real-world case study to every module" are encoded in the prompt skeletons and enforced across all generated content.

Currently, these are configured by editing `.docx` files in the `Docs/` directory. A planned web UI will allow users to set their experience level, preferred instructor persona, and structural requirements through a guided interface — making the personalization engine accessible to non-technical users without touching any files.

### Adding New Generation Stages

The pipeline is modular. Each stage is a function that takes input text/dict and returns output text/dict. Adding a new stage (e.g., quiz generation, slide deck outlines) means writing a new function and inserting it into the pipeline in `course_gen_main.py`.

---

## Roadmap

- [ ] Web UI — guided course creation with persona selection and structural preferences
- [ ] PDF textbook ingestion — RAG-powered generation grounded in existing course materials (Second Brain)
- [ ] Quiz & assessment generation stage
- [ ] Multi-model support (Claude, GPT-4 as additional backends)
- [ ] Adaptive content difficulty — adjust generated material based on student performance signals
- [ ] Async pipeline with parallel module generation
- [ ] Batch course generation

---

## License

MIT License — see [LICENSE](LICENSE) for details.
