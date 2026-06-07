# Autonomous Supply Chain Strategist

An enterprise-grade, multi-agent research and planning application. Unlike standard conversational AI (like ChatGPT), this system acts as a sophisticated data engine that autonomously researches supply chain disruptions and outputs a highly structured, interactive SaaS dashboard.

## 🌟 The Core Paradigm Shift

Basic LLM interactions rely on a single prompt returning a wall of text. This application uses a **Multi-Agent Pipeline** that forces the AI to think in steps and output structured data:

1. **Logistics Architect:** Analyzes the scenario and generates 3 highly specific, technical search queries (e.g., searching for JIT frameworks or VMI case studies).
2. **Operations Analyst:** Executes the searches via Tavily AI and scrapes deep contextual data from the results, filtering out low-quality pages.
3. **Chief Strategy Officer:** Synthesizes the data into a strict **JSON payload** containing an Executive Summary, a Phased Timeline, a Risk Matrix, and Mapped Sources. 

The frontend then renders this JSON into an interactive business dashboard, rather than a chat bubble.

## 🚀 Key Features

* **Real-Time "Thought Tracing" (SSE):** Utilizing Server-Sent Events, the UI streams the agent's internal thought process and real-time actions (e.g., `[Agent: Operations Analyst] Evaluating Source: Toyota Supply Chain...`) to a live log panel.
* **Interactive Citation Mapping:** Every claim is tied to a specific source ID. The frontend intercepts these IDs and replaces them with beautifully styled, clickable badges that link directly to the verified URL.
* **Production Resilience:** Implements exponential backoff for API rate limits and robust Regex-based JSON extraction to prevent LLM formatting hallucinations from crashing the application.
* **Deployable Assets:** Dashboards feature an **Export Report** function to instantly generate clean PDFs for logistics teams.

## 🛠️ Tech Stack

* **Backend:** Python, FastAPI, SSE-Starlette
* **Frontend:** HTML5, Vanilla JavaScript, Tailwind CSS (via CDN), Markdown-it
* **LLM Engine:** NVIDIA NIM (running `meta/llama-3.3-70b-instruct`) via the OpenAI Python client
* **Search Engine:** Tavily AI (purpose-built for agentic RAG) with a DuckDuckGo fallback
* **Scraper:** `httpx` and `trafilatura` for high-signal text extraction

## 📂 Project Structure

```text
planning-research-agent/
├── .env                        # API Keys (NVIDIA, Hugging Face, Tavily)
├── requirements.txt            # Python dependencies
├── agent/
│   ├── loop.py                 # Multi-agent async generator and SSE logic
│   ├── prompts.py              # System prompts & supply chain frameworks
│   └── tools/
│       ├── web_search.py       # Tavily AI / DuckDuckGo search integration
│       └── fetch_page.py       # Trafilatura web scraping logic
├── app/
│   ├── main.py                 # FastAPI server and endpoints
│   └── static/
│       ├── index.html          # Dashboard UI and layout
│       └── app.js              # SSE handling, JSON rendering, and UI logic
└── smoke_test.py               # End-to-end Python test script for the SSE stream
```

## 🏁 Quick Start

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install sse-starlette tavily-python
   ```

2. **Configure Environment Variables:**
   Ensure your `.env` file is populated with your API keys:
   ```env
   NVIDIA_API_KEY=your_nvidia_key
   TAVILY_API_KEY=your_tavily_key
   LLM_PROVIDER=nvidia
   MODEL_NAME=meta/llama-3.3-70b-instruct
   ```

3. **Run the Application:**
   ```bash
   # Make sure you run this from the project root directory
   $env:PYTHONPATH = '.'; python app/main.py
   ```
   *(On macOS/Linux use `export PYTHONPATH='.'; python app/main.py`)*

4. **Access the UI:**
   Open your browser and navigate to `http://localhost:8000`. Click on one of the **Suggested Scenarios** to watch the autonomous agents in action!
