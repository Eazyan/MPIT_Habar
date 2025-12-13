from minio import Minio
import os
import io
import json
from datetime import timedelta

class StorageClient:
    def __init__(self):
        self.client = Minio(
            endpoint=os.getenv("MINIO_ENDPOINT", "minio:9000"),
            access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
            secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"),
            secure=False
        )
        self.history_bucket = "history"
        self.rag_bucket = "rag-knowledge"

    def save_generation(self, plan_id: str, data: dict):
        """Saves the full generation data to the history bucket."""
        try:
            # Save JSON
            json_data = json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')
            self.client.put_object(
                self.history_bucket,
                f"{plan_id}/data.json",
                io.BytesIO(json_data),
                len(json_data),
                content_type="application/json"
            )
            return True
        except Exception as e:
            print(f"MinIO Save Error: {e}")
            return False

    def promote_to_rag(self, plan_id: str):
        """Copies data from history bucket to rag-knowledge bucket."""
        from minio.commonconfig import CopySource
        try:
            # Copy JSON
            self.client.copy_object(
                self.rag_bucket,
                f"{plan_id}/data.json",
                CopySource(self.history_bucket, f"{plan_id}/data.json")
            )
            return True
        except Exception as e:
            print(f"MinIO Promote Error: {e}")
            return False

    def get_generation(self, plan_id: str) -> dict:
        """Reads generation data from history bucket."""
        try:
            response = self.client.get_object(self.history_bucket, f"{plan_id}/data.json")
            return json.loads(response.read())
        except Exception as e:
            print(f"MinIO Read Error: {e}")
            return None

# Global instance
storage = StorageClient()
