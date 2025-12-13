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

    def add_case(self, doc_id: str, text: str, metadata: Dict):
        """Add a single case to the vector store."""
        self.collection.add(
            documents=[text],
            metadatas=[metadata],
            ids=[doc_id]
        )

    def query(self, query_text: str, n_results: int = 3, threshold: float = 1.5) -> List[str]:
        """Retrieve relevant documents with distance threshold."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        # results['distances'] contains the distance metric (lower is better)
        # results['documents'] contains the text
        
        if not results['documents']:
            return []
            
        final_docs = []
        # Check distances if available (default metric is L2 or Cosine depending on setup, usually L2 for Chroma default)
        # For L2, smaller is closer. 
        # Note: Chroma returns a list of lists (one per query)
        
        distances = results['distances'][0] if 'distances' in results and results['distances'] else []
        documents = results['documents'][0]
        
        print(f"DEBUG: Querying RAG. Found {len(documents)} candidates.")
        
        for i, doc in enumerate(documents):
            # If we have distances, filter. If not (unlikely), include all.
            if distances:
                dist = distances[i]
                print(f"DEBUG: Candidate {i}: Dist={dist:.4f} | Text={doc[:50]}...")
                # Heuristic: 1.5 is a loose threshold for L2. 
                # If distance > threshold, it's too far.
                if dist > threshold:
                    print(f"DEBUG: Dropped (Threshold {threshold})")
                    continue
            final_docs.append(doc)
            
        return final_docs

# Global instance
rag_store = RAGStore()
