from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.state import AgentState
from app.models import NewsAnalysis
from app.utils.scraper import scrape_url
from app.agents.monitoring import search_brand_mentions
from app.llm_factory import get_llm
import json
import random

async def analyzer_node(state: AgentState) -> AgentState:
    """Analyzes the news content."""
    print("--- ANALYZER AGENT ---")
    
    # Get model provider from input
    model_provider = state['input'].model_provider if state.get('input') else "claude"
    print(f"Using Model: {model_provider}")
    
    try:
        llm = get_llm(model_provider)
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

    # 2. Prepare Brand Context - ROBUST extraction
    # news_input may be a Pydantic object OR a dict depending on LangGraph serialization
    brand_profile = None
    try:
        bp = getattr(news_input, "brand_profile", None)
        if not bp and isinstance(news_input, dict):
            bp = news_input.get("brand_profile")
        
        if bp:
            # bp could be BrandProfile object or dict
            brand_profile = bp
    except Exception as e:
        print(f"DEBUG [Analyzer]: Error extracting brand_profile: {e}")
    
    mode = state.get('mode', 'pr')
    target_brand = state.get('target_brand')
    
    brand_context = ""
    role_context = ""
    
    # Helper for robust property access
    def get_bp_prop(bp, prop):
        val = getattr(bp, prop, None)
        if val is None and isinstance(bp, dict):
            val = bp.get(prop)
        return val or ""
    
    if mode == "blogger":
        # Blogger mode: analyzing news about a target brand
        brand_name = target_brand
        if not brand_name and brand_profile:
            brand_name = get_bp_prop(brand_profile, "name")
        brand_name = brand_name or "Unknown Brand"
        
        role_context = f"""
        YOUR ROLE: You are a tech/business BLOGGER analyzing news about {brand_name}.
        You provide independent, objective analysis with your own opinion.
        """
        if brand_profile:
            brand_context = f"""
            YOUR PERSONAL STYLE:
            Tone of Voice: {get_bp_prop(brand_profile, "tone_of_voice")}
            Target Audience: {get_bp_prop(brand_profile, "target_audience")}
            """
    else:
        # PR mode: acting as the brand's voice
        if brand_profile:
            bp_name = get_bp_prop(brand_profile, "name")
            bp_desc = get_bp_prop(brand_profile, "description")
            bp_tone = get_bp_prop(brand_profile, "tone_of_voice")
            bp_audience = get_bp_prop(brand_profile, "target_audience")
            
            brand_context = f"""
            BRAND PROFILE:
            Name: {bp_name}
            Description: {bp_desc}
            Tone of Voice: {bp_tone}
            Target Audience: {bp_audience}
            """
            role_context = f"YOUR ROLE: You are a PR Strategist for {bp_name}."
        else:
            role_context = "YOUR ROLE: You are a PR Strategist."

    # 3. Analyze
    prompt = f"""
    {role_context}
    
    Analyze the following news text.
    
    {brand_context}
    
    News Text:
    {news_text[:10000]}
    
    Task:
    1. Extract key facts, quotes, and summary.
    2. Determine sentiment specifically towards the BRAND (if mentioned) or the market.
    3. Decide on a PR Verdict: Should we respond? Ignore? Newsjack?
       - CRITICAL: Look for "Newsjacking" opportunities! Even if the news is negative/unrelated, try to find a creative way to mention the Brand (e.g., "Health issues in city -> Brand Watch helps monitor health").
       - If "Ignore" is chosen, still provide a creative "What if" scenario in the reasoning.
    4. Provide a Relevance Score (0-100). Calculate based on:
        - Direct Brand Mention: +40
        - Market Impact: +30
        - Urgency: +30
        - Newsjacking Potential: +20 (Bonus)
    5. Determine the Category:
        - CRISIS: Negative sentiment, scandals, threats.
        - PRODUCT: Launches, updates, features.
        - COMPETITOR: Competitor news.
        - ROUTINE: General industry news, lists.
    6. Provide 3 actionable TIPS on how to execute this strategy.
    
    IMPORTANT: Output MUST be valid JSON matching the schema. All text fields in RUSSIAN (except 'sentiment').
    Sentiment MUST be one of: "POSITIVE", "NEGATIVE", "NEUTRAL".
    
    Schema:
    {{
        "summary": "string (in Russian)",
        "facts": ["string (in Russian)"],
        "quotes": ["string (in Russian)"],
        "sentiment": "POSITIVE|NEGATIVE|NEUTRAL",
        "topics": ["string (in Russian)"],
        "relevance_score": 0-100,
        "pr_verdict": "Отвечать|Игнорировать|Мониторить|Ньюсджекинг",
        "pr_reasoning": "string (in Russian)",
        "category": "CRISIS|PRODUCT|COMPETITOR|ROUTINE",
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
        # Robust parsing using regex to find the first JSON object
        content = response.content.strip()
        
        # 1. Try to extract from code blocks first
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        # 2. Cleanup and Load
        import re
        content = content.strip()
        
        # If still contains non-json text, try regex for {...}
        if not content.startswith("{"):
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                content = match.group(0)
        
        analysis_dict = json.loads(content)
        analysis = NewsAnalysis(**analysis_dict)
        
        return {"analysis": analysis}
    except Exception as e:
        print(f"Error parsing analysis: {e}")
        # Log bad content for debugging
        print(f"Content: {response.content[:500]}...") 
        return {"errors": [f"JSON Parse Error: {str(e)}"]}
