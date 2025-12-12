from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.analyzer import analyzer_node
from app.agents.writer import writer_node
from app.rag.store import rag_store

def context_node(state: AgentState) -> AgentState:
    """Retrieves context from RAG."""
    print("--- CONTEXT AGENT ---")
    # Query RAG based on summary or text
    query = state['input'].text[:200] if state['input'].text else "News"
    context = rag_store.query(query)
    return {"context": context}

from app.agents.visual import visual_node

# Define Graph
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("analyzer", analyzer_node)
workflow.add_node("context", context_node)
workflow.add_node("writer", writer_node)
workflow.add_node("visual", visual_node)

# Set Entry Point
workflow.set_entry_point("analyzer")

# Add Edges
workflow.add_edge("analyzer", "context")
workflow.add_edge("context", "writer")
workflow.add_edge("writer", "visual")
workflow.add_edge("visual", END)

# Compile
app = workflow.compile()
