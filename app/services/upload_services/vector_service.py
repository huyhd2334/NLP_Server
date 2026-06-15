from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.qdrant import client
from app.core.config import COLLECTION_NAME


def init_qdrant():
    collections = client.get_collections()
    existing = [c.name for c in collections.collections]

    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE
            )
        )
     
        print("Created collection documents-rag")
    else:
        print("Collection documents already exists")


