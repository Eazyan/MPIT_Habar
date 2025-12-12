from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
from app.agents.state import AgentState
from app.models import NewsAnalysis
from app.utils.scraper import scrape_url
from app.agents.monitoring import search_brand_mentions
import os
import json
import random

def get_llm():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=api_key,
        temperature=0
    )

async def analyzer_node(state: AgentState) -> AgentState:
    """Analyzes the input news text with Brand Context."""
    print("--- ANALYZER AGENT ---")
    try:
        llm = get_llm()
    except ValueError as e:
        return {"errors": [str(e)]}

    news_input = state['input']
    news_text = news_input.text
    
    # 0. Handle Monitoring Trigger
    if news_input.url == "monitoring":
        print("--- MONITORING TRIGGERED ---")
        if not news_input.brand_profile:
             return {"errors": ["Monitoring requires a Brand Profile."]}
             
        found_news = await search_brand_mentions(news_input.brand_profile)
        if not found_news:
            return {"errors": ["No recent news found for this brand."]}
            
        # Pick the most relevant news (for now, the first one)
        # In a real app, we might analyze all or let user choose.
        best_news = found_news[0]
        print(f"Found news: {best_news.url}")
        
        # Update state input for downstream
        news_input.url = best_news.url
        news_input.text = best_news.text
        news_text = best_news.text
    
    # 1. Scrape if URL is provided but text is missing or short
    if news_input.url and news_input.url != "monitoring" and (not news_text or len(news_text) < 100):
        print(f"Scraping URL: {news_input.url}")
        scraped_text = await scrape_url(news_input.url)
        if scraped_text:
            news_text = scraped_text
    
    if not news_text:
        return {"errors": ["No text provided and scraping failed."]}

    # 2. Prepare Brand Context
    brand_profile = news_input.brand_profile
    brand_context = ""
    if brand_profile:
        brand_context = f"""
        BRAND PROFILE:
        Name: {brand_profile.name}
        Description: {brand_profile.description}
        Tone of Voice: {brand_profile.tone_of_voice}
        Target Audience: {brand_profile.target_audience}
        """

    # 3. Analyze
    prompt = f"""
    Analyze the following news text acting as a PR Strategist for the brand described below.
    
    {brand_context}
    
    News Text:
    {news_text[:10000]}
    
    Task:
    1. Extract key facts, quotes, and summary.
    2. Determine sentiment specifically towards the BRAND (if mentioned) or the market.
    3. Decide on a PR Verdict: Should we respond? Ignore? Newsjack?
    4. Provide a Relevance Score (0-100).
    5. Provide 3 actionable TIPS on how to execute this strategy (e.g. "Use humor", "Focus on data", "Avoid conflict").
    
    IMPORTANT: Output MUST be valid JSON matching the schema. All text fields in RUSSIAN.
    
    Schema:
    {{
        "summary": "string (in Russian)",
        "facts": ["string (in Russian)"],
        "quotes": ["string (in Russian)"],
        "sentiment": "positive|negative|neutral",
        "topics": ["string (in Russian)"],
        "relevance_score": 0-100,
        "pr_verdict": "Отвечать|Игнорировать|Мониторить|Ньюсджекинг",
        "pr_reasoning": "string (in Russian)",
        "tips": ["string (in Russian)"]
    }}
    """
    
    messages = [
        SystemMessage(content="You are an expert PR Strategist. Output ONLY JSON. Always reply in Russian."),
        HumanMessage(content=prompt)
    ]
    
    try:
        response = await llm.ainvoke(messages)
    except Exception as e:
        return {"errors": [f"LLM Invoke Error: {str(e)}"]}
    
    try:
        # Simple parsing
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        analysis_dict = json.loads(content.strip())
        analysis = NewsAnalysis(**analysis_dict)
        
        return {"analysis": analysis}
    except Exception as e:
        print(f"Error parsing analysis: {e}")
        return {"errors": [str(e)]}
