import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict

class RAGStore:
    def __init__(self):
        host = os.getenv("CHROMA_DB_HOST", "chromadb")
        port = os.getenv("CHROMA_DB_PORT", "8000")
        
        # Connect to ChromaDB server
        self.client = chromadb.HttpClient(host=host, port=int(port))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(name="brand_context")

    def add_documents(self, documents: List[str], metadatas: List[Dict], ids: List[str]):
        """Add documents to the vector store."""
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query(self, query_text: str, n_results: int = 3) -> List[str]:
        """Retrieve relevant documents."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        # Flatten results
        return results['documents'][0] if results['documents'] else []

# Global instance
rag_store = RAGStore()
