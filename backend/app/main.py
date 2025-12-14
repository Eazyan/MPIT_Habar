from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.models import NewsInput, MediaPlan, NewsAnalysis, RegenerateRequest, GeneratedPost, Platform, BrandProfile
from app.agents.graph import app as agent_app
import uuid

from app.database import engine, Base
from app.auth.router import router as auth_router, get_current_user
from app.auth.models import User
from app.auth.models import User
from fastapi import Depends
import redis
import json
import os

# Redis connection
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth_router)

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
async def get_history(user: User = Depends(get_current_user)):
    """Returns recent generations from MinIO for the current user."""
    from app.storage import storage
    return storage.list_generations(user_id=user.id, limit=12)

@app.get("/history/{plan_id}")
async def get_plan(plan_id: str, user: User = Depends(get_current_user)):
    """Returns a specific plan by ID for the current user."""
    from app.storage import storage
    data = storage.get_generation(user_id=user.id, plan_id=plan_id)
    if not data:
        raise HTTPException(status_code=404, detail="План не найден")
    return data

# Background task for generation
async def run_generation_task(task_id: str, news: NewsInput, user_id: int):
    """Background task that runs the actual generation."""
    from app.task_queue import update_task_status, TaskStatus
    from app.storage import storage
    
    try:
        update_task_status(task_id, TaskStatus.PROCESSING)
        
        # Run the LangGraph workflow with user context and mode
        initial_state = {
            "input": news, 
            "user_id": user_id, 
            "mode": news.mode or "pr",
            "target_brand": news.target_brand,
            "errors": []
        }
        result = await agent_app.ainvoke(initial_state)
        
        if result.get("errors"):
            update_task_status(task_id, TaskStatus.ERROR, error=str(result['errors']))
            return
            
        # Construct response
        final_input = result.get("input", news)
        
        plan = MediaPlan(
            id=task_id,  # Use task_id as plan_id
            original_news=final_input,
            analysis=result["analysis"],
            posts=result["posts"]
        )
        
        # Save to MinIO History (User specific)
        storage.save_generation(user_id, plan.id, plan.dict())
        
        # Update task with result
        update_task_status(task_id, TaskStatus.READY, data=plan.dict())
        
        # Get Telegram Chat ID
        telegram_chat_id = None
        try:
            from app.database import SessionLocal
            from app.auth.models import User
            with SessionLocal() as db:
                user_obj = db.query(User).filter(User.id == user_id).first()
                if user_obj:
                    telegram_chat_id = user_obj.telegram_chat_id
        except Exception as e:
            print(f"Error fetching User for notification: {e}")

        # Publish Notification to Redis
        try:
            # Find the best post (e.g. Telegram or first available)
            best_post = next((p for p in plan.posts if p.platform == "telegram"), plan.posts[0] if plan.posts else None)
            post_content = best_post.content if best_post else "Нет сгенерированного поста."

            redis_client.publish("task_updates", json.dumps({
                "type": "task_completed",
                "task_id": task_id,
                "user_id": user_id,
                "telegram_chat_id": telegram_chat_id,
                "summary": plan.analysis.summary,
                "score": plan.analysis.relevance_score,
                "verdict": plan.analysis.pr_verdict,
                "post_content": post_content,
                "status": "ready"
            }))
        except Exception as e:
            print(f"Redis Publish Error: {e}")
        
    except Exception as e:
        print(f"Generation Error: {e}")
        import traceback
        traceback.print_exc()
        update_task_status(task_id, TaskStatus.ERROR, error=str(e))
        
        # Publish Error Notification
        try:
            redis_client.publish("task_updates", json.dumps({
                "type": "task_error",
                "task_id": task_id,
                "user_id": user_id,
                "telegram_chat_id": telegram_chat_id if 'telegram_chat_id' in locals() else None,
                "error": str(e)
            }))
        except:
            pass

class BotGenerateRequest(BaseModel):
    url: str
    telegram_chat_id: str
    model_provider: str = "claude"
    mode: str = "pr"

@app.post("/bot/generate")
async def bot_generate(req: BotGenerateRequest, background_tasks: BackgroundTasks):
    """
    Internal endpoint for Bot to trigger generation.
    """
    from app.database import SessionLocal
    from app.task_queue import save_task, can_start_task, TaskStatus
    
    # 1. Find User by Telegram ID
    with SessionLocal() as db:
        user = db.query(User).filter(User.telegram_chat_id == req.telegram_chat_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not linked. Please link account first.")
        user_id = user.id
    
    # Check limits
    if not can_start_task(user_id):
        raise HTTPException(status_code=429, detail="Максимум 3 активных генерации. Подождите.")

    # 2. Create Task
    task_id = str(uuid.uuid4())
    save_task(task_id, user_id, TaskStatus.PENDING)
    
    # 3. Create Input
    # Use params from request
    news_input = NewsInput(
        url=req.url,
        model_provider=req.model_provider,
        mode=req.mode, 
        brand_profile=BrandProfile(**user.brand_profile) if user.brand_profile else None
    )
    
    # 4. Run
    background_tasks.add_task(run_generation_task, task_id, news_input, user_id)
    
    return {"task_id": task_id, "status": "pending"}

@app.post("/generate")
async def generate_plan(news: NewsInput, background_tasks: BackgroundTasks, user: User = Depends(get_current_user)):
    """
    Starts async generation. Returns task ID immediately.
    Poll /task/{id}/status for updates.
    """
    from app.task_queue import save_task, can_start_task, TaskStatus
    
    # Check if user can start new task
    if not can_start_task(user.id):
        raise HTTPException(status_code=429, detail="Максимум 3 активных генерации. Подождите завершения.")
    
    # Create task
    task_id = str(uuid.uuid4())
    save_task(task_id, user.id, TaskStatus.PENDING)
    
    # Инжектируем профиль бренда из БД (фронтенд его не передаёт)
    if user.brand_profile:
        try:
            news.brand_profile = BrandProfile(**user.brand_profile) if isinstance(user.brand_profile, dict) else user.brand_profile
        except Exception:
            pass
    
    # Queue background task
    background_tasks.add_task(run_generation_task, task_id, news, user.id)
    
    return {"id": task_id, "status": "pending"}

@app.get("/task/{task_id}/status")
async def get_task_status(task_id: str, user: User = Depends(get_current_user)):
    """Get status of a generation task."""
    from app.task_queue import get_task
    
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    
    # Verify ownership
    if task.get("user_id") != user.id:
        raise HTTPException(status_code=403, detail="Нет доступа")
    
    return task

@app.post("/regenerate", response_model=GeneratedPost)
async def regenerate_post(request: RegenerateRequest, user: User = Depends(get_current_user)):
    """
    Regenerates a single post for a specific platform.
    """
    from app.agents.writer import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    from app.models import GeneratedPost
    import urllib.parse

    try:
        # Use the same model that was used for original generation
        model_provider = request.original_news.model_provider if request.original_news else "claude"
        llm = get_llm(model_provider)
        
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
async def scan_news(target_brand: str | None = None, user: User = Depends(get_current_user)):
    """
    Scans for recent news about a brand.
    - PR mode: uses user's saved brand profile
    - Blogger mode: uses target_brand parameter
    """
    from app.agents.monitoring import search_brand_mentions
    from app.models import BrandProfile
    
    if target_brand:
        # Blogger mode: create temporary profile with just the name
        profile = BrandProfile(
            name=target_brand,
            description="",
            tone_of_voice="",
            target_audience="",
            keywords=[target_brand]
        )
    elif user.brand_profile:
        # PR mode: use user's saved profile
        profile = BrandProfile(**user.brand_profile)
    else:
        raise HTTPException(status_code=400, detail="Укажите бренд для поиска или настройте профиль!")
    
    try:
        results = await search_brand_mentions(profile)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def feedback(plan_id: str, like: bool, user: User = Depends(get_current_user)):
    """
    Handles user feedback. Updates 'liked' status and promotes to RAG if liked.
    """
    from app.storage import storage
    from app.rag.store import rag_store

    try:
        # 0. Update 'liked' status in persistence
        storage.update_generation(user.id, plan_id, {"liked": like})
        
        if not like:
            return {"status": "unliked"}
            
        # 1. Get Data first to know the category
        data = storage.get_generation(user.id, plan_id)
        if not data:
             raise HTTPException(status_code=404, detail="Plan not found in history")

        # Extract category (default to ROUTINE if missing, e.g. old plans)
        category = data['analysis'].get('category', 'ROUTINE')
        
        # 2. Promote in MinIO (Copy from history to rag-knowledge/{category})
        success = storage.promote_to_rag(user.id, plan_id, category)
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
            "bucket": "rag-knowledge",
            "user_id": user.id
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

# --- PUBLISH ENDPOINTS ---

class PublishRequest(BaseModel):
    content: str
    platform: str

@app.post("/publish/telegram")
async def publish_telegram(req: PublishRequest, user: User = Depends(get_current_user)):
    """
    Sends the post content to user's linked Telegram chat.
    Works as a "preview" - real channel posting requires bot to be admin in channel.
    """
    if not user.telegram_chat_id:
        raise HTTPException(status_code=400, detail="Telegram не привязан. Используйте кнопку 'Подключить Telegram'.")
    
    # Send via Redis to the bot
    message = {
        "type": "publish",
        "telegram_chat_id": user.telegram_chat_id,
        "content": req.content,
        "platform": req.platform
    }
    
    try:
        redis_client.publish("task_updates", json.dumps(message))
        return {
            "status": "sent",
            "message": "Пост отправлен в Telegram! 📤\n\n💡 Совет: Добавьте бота (@RezonansAI_bot) админом в ваш канал для автоматической публикации."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка отправки: {str(e)}")
