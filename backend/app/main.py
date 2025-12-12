from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import NewsInput, MediaPlan, NewsAnalysis, RegenerateRequest, GeneratedPost
from app.agents.graph import app as agent_app
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World", "Service": "AI-Newsmaker Backend"}

@app.post("/generate", response_model=MediaPlan)
async def generate_plan(news: NewsInput):
    """
    Triggers the AI Agent workflow to generate a media plan.
    """
    try:
        # Run the LangGraph workflow
        initial_state = {"input": news, "errors": []}
        result = await agent_app.ainvoke(initial_state)
        
        if result.get("errors"):
            print(f"Workflow Errors: {result['errors']}")
            raise HTTPException(status_code=500, detail=f"Agent Error: {result['errors']}")
            
        # Construct response
        plan = MediaPlan(
            id=str(uuid.uuid4()),
            original_news=news,
            analysis=result["analysis"],
            posts=result["posts"]
        )
        return plan
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/regenerate", response_model=GeneratedPost)
async def regenerate_post(request: RegenerateRequest):
    """
    Regenerates a single post for a specific platform.
    """
    from app.agents.writer import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    from app.models import GeneratedPost
    import urllib.parse

    try:
        llm = get_llm()
        
        # Reconstruct context (simplified for single post)
        brand_name = request.original_news.brand_profile.name if request.original_news.brand_profile else "Brand"
        
        # Determine style guide
        if request.platform in ["email", "press_release"]:
            style_guide = "STRICTLY FORMAL. NO EMOJIS. NO MARKDOWN HEADERS. Standard business document format."
        else:
            style_guide = "Engaging social media style. Emojis allowed. NO MARKDOWN HEADERS. Ready to publish."

        prompt = f"""
        YOU ARE THE OFFICIAL VOICE OF THE BRAND: {brand_name}.
        
        TASK: Rewrite the content for {request.platform.upper()} in RUSSIAN.
        
        Analysis:
        - Summary: {request.analysis.summary}
        - Facts: {", ".join(request.analysis.facts)}
        - Sentiment: {request.analysis.sentiment}
        - PR Verdict: {request.analysis.pr_verdict}
        
        Style Guide: {style_guide}
        
        CRITICAL RULES:
        1. Write AS {brand_name}.
        2. Language: RUSSIAN.
        3. NO Markdown headers (##).
        4. NO "Subject:", "Body:" labels.
        
        At the very end, strictly separated by "|||", provide a NEW Image Prompt in English.
        """
        
        messages = [
            SystemMessage(content=f"You are the Head of Communications for {brand_name}."),
            HumanMessage(content=prompt)
        ]
        
        response = await llm.ainvoke(messages)
        
        # Parse
        full_content = response.content
        content = full_content
        image_prompt = "Abstract modern technology"
        
        if "|||" in full_content:
            parts = full_content.split("|||")
            content = parts[0].strip()
            if len(parts) > 1:
                image_prompt = parts[1].strip()
                
        # Generate Image URL
        encoded_prompt = urllib.parse.quote(image_prompt)
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true"
        
        return GeneratedPost(
            platform=request.platform,
            content=content,
            image_prompt=image_prompt,
            image_url=image_url,
            status="draft"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

