from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
from app.agents.state import AgentState
from app.models import GeneratedPost, Platform
import os

def get_llm():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=api_key,
        temperature=0.7
    )

def writer_node(state: AgentState) -> AgentState:
    """Generates posts based on analysis and context."""
    print("--- WRITER AGENT ---")
    
    if state.get("errors"):
        return {"errors": state["errors"]}
        
    analysis = state.get('analysis')
    if not analysis:
        return {"errors": ["No analysis found. Analyzer agent likely failed."]}

    context = state.get('context', [])
    context_str = "\n".join(context)
    
    # Define platforms and their specific strategies
    platforms = [
        Platform.TELEGRAM, 
        Platform.VK, 
        Platform.TENCHAT,
        Platform.VC,
        Platform.DZEN,
        Platform.EMAIL,
        Platform.PRESS_RELEASE
    ]
    
    posts = []
    
    try:
        llm = get_llm()
        
        for platform in platforms:
            # Define specific constraints per platform
            if platform in [Platform.EMAIL, Platform.PRESS_RELEASE]:
                style_guide = "STRICTLY FORMAL. NO EMOJIS. NO MARKDOWN HEADERS (like ## Hook). Standard business document format."
            else:
                style_guide = "Engaging social media style. Emojis allowed. NO MARKDOWN HEADERS (like ## Hook). The text must be ready to copy-paste and publish."

            prompt = f"""
            YOU ARE THE OFFICIAL VOICE OF THE BRAND: {analysis.summary} (Brand Name inferred from context).
            
            CRITICAL RULES:
            1. **Perspective**: Write AS THE BRAND. Do NOT write as a blogger, journalist, or fan.
               - BAD: "I have hot info...", "Rumors say...", "If this is true..."
               - GOOD: "We are proud to introduce...", "Our vision is...", "Experience the future with..."
            2. **Grounding**: Base your content strictly on the provided facts. Do not hallucinate "leaks" if the news is about a release.
            3. **Tone**: Confident, professional, but adapted to the platform.
               - If comparing with competitors: Highlight OUR advantages with dignity. Do not bash. Be superior but respectful.
            
            Analysis:
            - Summary: {analysis.summary}
            - Facts: {", ".join(analysis.facts)}
            - Sentiment: {analysis.sentiment}
            - PR Verdict: {analysis.pr_verdict} ({analysis.pr_reasoning})
            
            Brand Context:
            {context_str}
            
            Platform Strategy:
            - TELEGRAM: Official channel tone. Short, informative, clear value.
            - VK: Community engagement, official announcements.
            - TENCHAT: Professional insights, business impact.
            - VC: Corporate blog. Deep dive into technology/strategy.
            - DZEN: Brand media. Educational and inspiring.
            - EMAIL: Internal executive brief. "Here is the situation and our stance."
            - PRESS_RELEASE: Standard official press release format.
            
            Style Guide: {style_guide}
            
            REQUIRED OUTPUT FORMAT:
            1. The output must be ONLY the final post text.
            2. Do NOT include "Subject:", "Hook:", "Body:", "Image Prompt:" labels.
            3. Do NOT include the Image Prompt in the text.
            
            At the very end, strictly separated by "|||", provide the Image Prompt in English.
            """
            
            messages = [
                SystemMessage(content=f"You are the Head of Communications for the brand. You speak with authority, precision, and brand alignment."),
                HumanMessage(content=prompt)
            ]
            
            response = llm.invoke(messages)
            
            # Parse content and image prompt
            full_content = response.content
            content = full_content
            image_prompt = "Abstract modern technology, 4k, digital art" # Default
            
            if "|||" in full_content:
                parts = full_content.split("|||")
                content = parts[0].strip()
                if len(parts) > 1:
                    image_prompt = parts[1].strip()
            
            posts.append(GeneratedPost(
                platform=platform,
                content=content,
                image_prompt=image_prompt,
                status="draft"
            ))
            
    except Exception as e:
        return {"errors": [f"Writer LLM Error: {str(e)}"]}
        
    return {"posts": posts}
