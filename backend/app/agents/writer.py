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
            prompt = f"""
            Write a HIGH-QUALITY content piece for {platform.value.upper()} in RUSSIAN.
            
            Analysis:
            - Summary: {analysis.summary}
            - Facts: {", ".join(analysis.facts)}
            - Sentiment: {analysis.sentiment}
            - PR Verdict: {analysis.pr_verdict} ({analysis.pr_reasoning})
            
            Brand Context:
            {context_str}
            
            Platform Strategy:
            - TELEGRAM: Short, "inside" info, emojis, clear CTA.
            - VK: Engaging storytelling, community focus, hashtags.
            - TENCHAT: Professional, business value, networking focus.
            - VC: Blog post style, "How we did it", industry insights.
            - DZEN: Educational, catchy headline, broad audience.
            - EMAIL: Internal report for the boss. Concise, impact analysis.
            - PRESS_RELEASE: Formal, third-person, official quote.
            
            REQUIRED STRUCTURE:
            1. 🎣 **Hook/Headline**: Catchy title.
            2. 📝 **Body**: The main content.
            3. 🖼️ **Image Prompt**: A creative prompt for AI image generator (in English).
            4. #️⃣ **Hashtags**: (If applicable).
            
            Output ONLY the post text. Ensure the main text is in RUSSIAN.
            """
            
            messages = [
                SystemMessage(content=f"You are a top-tier PR & Content Manager for {platform.value}. You write in fluent, engaging Russian."),
                HumanMessage(content=prompt)
            ]
            
            response = llm.invoke(messages)
            
            # Extract Image Prompt if possible (simple heuristic)
            content = response.content
            image_prompt = "Abstract modern technology, 4k, digital art" # Default
            
            if "Image Prompt:" in content:
                parts = content.split("Image Prompt:")
                if len(parts) > 1:
                    image_prompt = parts[1].split("\n")[0].strip()
            
            posts.append(GeneratedPost(
                platform=platform,
                content=content,
                image_prompt=image_prompt,
                status="draft"
            ))
            
    except Exception as e:
        return {"errors": [f"Writer LLM Error: {str(e)}"]}
        
    return {"posts": posts}
