import os
from qdrant_client import AsyncQdrantClient
from qdrant_client import QdrantClient

async_client = AsyncQdrantClient(
    url=os.getenv("Cluster_Endpoint_QDrant"),
    api_key=os.getenv("API_Key_QDrant"),
    timeout=60.0,
)

client = QdrantClient(
    url=os.getenv("Cluster_Endpoint_QDrant"),
    api_key=os.getenv("API_Key_QDrant"),
)



