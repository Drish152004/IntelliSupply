import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from .tools.web_search import search_web
from .tools.fetch_page import fetch_content
from .prompts import SYSTEM_PROMPT, PLANNER_PROMPT
from .guardrails import validate_input, validate_output

load_dotenv(override=True)

def get_client():
    provider = os.getenv("LLM_PROVIDER", "nvidia").lower()
    if provider == "nvidia":
        return OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY")
        )
    elif provider == "huggingface":
        # Using the unified HF router (OpenAI-compatible)
        return OpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=os.getenv("HF_API_KEY")
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

import asyncio
import re

async def call_llm_with_retry(client, kwargs, max_retries=3):
    """Executes an LLM call with exponential backoff for rate limits."""
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Rate limit hit. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise e

def extract_json(text: str):
    """
    Robustly extract JSON from a string that might contain markdown or filler.
    """
    try:
        # Look for the first '[' or '{' and the last ']' or '}'
        match = re.search(r'([\[\{].*[\]\}])', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        return json.loads(text)
    except Exception:
        return None

async def run_agent_stream(scenario: str):
    # ... existing code ...
    client = get_client()
    model = os.getenv("MODEL_NAME", "meta/llama-3.3-70b-instruct")

    # PHASE 1: LOGISTICS ARCHITECT
    yield json.dumps({"type": "log", "content": "[Agent: Logistics Architect] Analyzing supply chain gaps..."})
    try:
        architect_prompt = f"ACT AS A SENIOR SUPPLY CHAIN ANALYST. SCENARIO: {scenario}\nTASK: Generate 3 search queries to find: 1. Real-world inventory/logistics news for this case. 2. Supply chain frameworks (JIT, VMI, Safety Stock). 3. Corporate case studies. Respond ONLY with a JSON list of strings."
        
        response = await call_llm_with_retry(client, {
            "model": model,
            "messages": [{"role": "user", "content": architect_prompt}],
            "temperature": 0
        })
        
        content = response.choices[0].message.content
        queries = extract_json(content)
        if not queries or not isinstance(queries, list):
            raise ValueError("Invalid query format")
        yield json.dumps({"type": "log", "content": f"[Agent: Logistics Architect] Generated 3 specialized supply chain queries."})
    except Exception:
        queries = [f"{scenario} inventory mitigation", f"{scenario} supply chain best practices", f"{scenario} logistics case study"]

    # PHASE 2: OPERATIONS ANALYST
    research_results = []
    all_urls = {} 
    
    for i, query in enumerate(queries):
        yield json.dumps({"type": "log", "content": f"[Agent: Operations Analyst] Investigating: {query}..."})
        search_hits = search_web(query, max_results=3)
        
        valid_hits_in_track = 0
        for hit in search_hits:
            if valid_hits_in_track >= 2: break # Limit per track for speed/quality
            
            url = hit["url"]
            if url in all_urls: continue
            
            yield json.dumps({"type": "log", "content": f"[Agent: Operations Analyst] Evaluating Source: {hit['title']}..."})
            await asyncio.sleep(0.1)
            
            scraped = fetch_content(url)
            if scraped and scraped["text"]:
                yield json.dumps({"type": "log", "content": f"[Agent: Operations Analyst] Extracted logistics intelligence from {hit['title']}."})
                # Add to source map
                all_urls[url] = {"title": hit["title"], "id": len(all_urls) + 1}
                
                research_results.append({
                    "id": all_urls[url]["id"],
                    "title": hit["title"],
                    "url": url,
                    "content": scraped["text"][:6000] 
                })
                valid_hits_in_track += 1
            else:
                yield json.dumps({"type": "log", "content": f"[Agent: Operations Analyst] Skipped low-signal source: {url}"})

    # PHASE 3: CHIEF STRATEGY OFFICER
    yield json.dumps({"type": "log", "content": "[Agent: Chief Strategy Officer] Synthesizing Enterprise Dashboard Data..."})
    try:
        research_context = json.dumps(research_results, indent=2)
        source_map = json.dumps({v["id"]: {"url": k, "title": v["title"]} for k, v in all_urls.items()})
        
        synthesis_prompt = f"""
        ACT AS A CHIEF SUPPLY CHAIN STRATEGIST.
        
        SCENARIO: {scenario}
        RESEARCH DATA: {research_context}
        SOURCE MAP: {source_map}
        
        TASK:
        You are not a chatbot. You generate structured enterprise intelligence.
        Analyze the research and output a highly specific, tactical JSON payload.
        Do NOT include generic advice. Use specific data, numbers, and case studies found in the research.
        
        RESPOND EXACTLY WITH THIS JSON STRUCTURE (and nothing else):
        {{
            "title": "Title of the Strategy Brief",
            "executive_summary": "Deep synthesis of the situation and strategy. Cite sources like [1].",
            "financial_operational_impact": "Estimated impact on costs, lead times, or ROI based on research.",
            "timeline": [
                {{"phase": "0-48 Hours", "action": "Specific tactic...", "rationale": "Why based on research..."}},
                {{"phase": "1-2 Weeks", "action": "Specific tactic...", "rationale": "..."}},
                {{"phase": "Long-Term", "action": "Specific tactic...", "rationale": "..."}}
            ],
            "risk_matrix": [
                {{"risk": "Specific hidden risk", "severity": "High/Medium", "mitigation": "Tactical solution"}}
            ],
            "sources": [
                {{"id": 1, "title": "Source Name", "url": "https://..."}}
            ]
        }}
        
        CRITICAL: Ensure the "sources" array exactly matches the SOURCE MAP provided to you.
        """

        response = await call_llm_with_retry(client, {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a backend data engine. You only output valid JSON matching the exact schema requested."},
                {"role": "user", "content": synthesis_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 4000
        })
        
        final_brief_text = response.choices[0].message.content
        final_json = extract_json(final_brief_text)
        
        if not final_json:
            raise ValueError("Failed to generate structured JSON.")
            
        # PHASE 4: QUALITY INSPECTOR
        yield json.dumps({"type": "log", "content": "[Agent: Quality Inspector] Validating Dashboard Data Schema..."})
        
        yield json.dumps({"type": "final_dashboard", "content": final_json})
    except Exception as e:
        yield json.dumps({"type": "error", "content": f"Multi-Agent Failure: {str(e)}"})
