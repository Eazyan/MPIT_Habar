from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import NewsInput, MediaPlan, NewsAnalysis, RegenerateRequest, GeneratedPost, Platform, BrandProfile
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

@app.get("/history")
async def get_history():
    """Returns recent generations from MinIO."""
    from app.storage import storage
    return storage.list_generations(limit=12)

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
        # Use result['input'] to get the updated news object (with scraped text)
        final_input = result.get("input", news)
        
        plan = MediaPlan(
            id=str(uuid.uuid4()),
            original_news=final_input,
            analysis=result["analysis"],
            posts=result["posts"]
        )
        
        # Save to MinIO History
        from app.storage import storage
        storage.save_generation(plan.id, plan.dict())
        
        return plan
        
    except Exception as e:
        import traceback
        traceback.print_exc()
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
        
        # Determine style guide and structure based on platform
        if request.platform == Platform.EMAIL:
            style_guide = """
            ФОРМАТ СЛУЖЕБНОЙ ЗАПИСКИ.
            Структура:
            Тема: [Четкая, побуждающая к действию тема]
            Кому: [Целевые стейкхолдеры, например, Маркетинг, CEO]
            Рекомендация: [Конкретный совет на основе анализа]
            
            Текст:
            [Краткий анализ ситуации и обоснование позиции. Официально, но прямо.]
            """
        elif request.platform == Platform.PRESS_RELEASE:
            style_guide = """
            ФОРМАТ ОФИЦИАЛЬНОГО ПРЕСС-РЕЛИЗА.
            Структура:
            ДЛЯ НЕМЕДЛЕННОГО РАСПРОСТРАНЕНИЯ
            
            [ЗАГОЛОВОК: Прописными, Впечатляющий]
            
            [Город, Дата] — [Лид-абзац: Кто, что, когда, где, почему]
            
            [Основной текст: Детали, контекст, официальные цитаты]
            
            [О компании (справка)]
            
            Контакты для СМИ:
            [Имя/Email]
            """
            style_guide = """
            Telegram Channel Style.
            - Use Markdown (*bold*, _italic_) for emphasis.
            - Use Emojis 🚀.
            - Short paragraphs.
            - Call to Action (CTA) at the end.
            """
        elif request.platform == Platform.IMAGE:
             # Logic for Image Regeneration
             prompt = f"""
             YOU ARE AN AI ART DIRECTOR.
             TASK: Create a NEW, BETTER stable diffusion prompt for an image representing this news.
             
             News Analysis:
             {request.analysis.summary}
             
             Visual Analysis:
             Topics: {request.analysis.topics}
             Sentiment: {request.analysis.sentiment}
             
             REQUIREMENTS:
             - English ONLY.
             - Descriptive, visual, artistic.
             - No text in image.
             - Modern, premium, cinematic lighting.
             
             OUTPUT: Just the prompt string.
             """
             
             response = await llm.ainvoke([HumanMessage(content=prompt)])
             image_prompt = response.content.strip()
             
             encoded_prompt = urllib.parse.quote(image_prompt)
             image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?nologo=true"
             
             return GeneratedPost(
                platform=Platform.IMAGE,
                content="Image Updated",
                image_prompt=image_prompt,
                image_url=image_url,
                status="draft"
             )
             
        else:
            style_guide = "Engaging social media style. Emojis allowed. NO Markdown headers (like ##). Ready to publish."

        prompt = f"""
        YOU ARE THE OFFICIAL VOICE OF THE BRAND: {brand_name}.
        
        TASK: Rewrite the content for {request.platform.upper()} in RUSSIAN.
        
        Analysis:
        - Summary: {request.analysis.summary}
        - Facts: {", ".join(request.analysis.facts)}
        - Sentiment: {request.analysis.sentiment}
        - PR Verdict: {request.analysis.pr_verdict}
        
        Style Guide: 
        {style_guide}
        
        CRITICAL RULES:
        1. Write AS {brand_name}.
        2. Language: RUSSIAN.
        3. Follow the specific structure for {request.platform.value} defined above.
        
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
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/monitor/scan", response_model=list[NewsInput])
async def scan_news(profile: BrandProfile):
    """
    Scans for recent news about the brand.
    """
    from app.agents.monitoring import search_brand_mentions
    try:
        results = await search_brand_mentions(profile)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def feedback(plan_id: str, like: bool):
    """
    Handles user feedback. If like=True, promotes the case to RAG knowledge base.
    """
    if not like:
        return {"status": "ignored"}
        
    try:
        from app.storage import storage
        from app.rag.store import rag_store
        
        # 1. Get Data first to know the category
        data = storage.get_generation(plan_id)
        if not data:
             raise HTTPException(status_code=404, detail="Plan not found in history")

        # Extract category (default to ROUTINE if missing, e.g. old plans)
        category = data['analysis'].get('category', 'ROUTINE')
        
        # 2. Promote in MinIO (Copy from history to rag-knowledge/{category})
        success = storage.promote_to_rag(plan_id, category)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to promote in Storage")
            
        # 3. Index in ChromaDB
        # Create a rich context string
        # Format: "News: ... \n Verdict: ... \n Post: ..."
        # We index the SUMMARY primarily so we can find similar news later.
        # Using Summary ensures language consistency (Russian) and noise reduction.
        news_text = data['analysis']['summary']
        
        verdict = data['analysis']['pr_verdict']
        
        # Metadata allows us to filter or retrieve details
        metadata = {
            "plan_id": plan_id,
            "verdict": verdict,
            "category": category,
            "bucket": "rag-knowledge"
        }
        
        rag_store.add_case(
            doc_id=plan_id,
            text=news_text,
            metadata=metadata
        )
            
        return {"status": "promoted"}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
