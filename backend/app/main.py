from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import NewsInput, MediaPlan, NewsAnalysis
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

