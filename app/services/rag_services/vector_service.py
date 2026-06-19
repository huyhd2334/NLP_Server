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


async def search(query_embed, file_ids ,top_k):
    
    if not file_ids:
        query_filter = None

    else:
        print("file_ids", file_ids)
        file_ids = [str(x) for x in file_ids]

        query_filter = {
            "must":[
                {
                    "key": "file_id",
                    "match": {
                        "any": file_ids
                    }
                }
            ]
        }

    results = client.query_points(
        collection_name = COLLECTION_NAME,
        query = query_embed,
        limit = top_k,
        query_filter=query_filter,
        with_payload=True
    )

    chunks = []

    points = results.points
    print("points:", len(results.points))

    for r in points:
        chunks.append({
            "score": r.score,
            "text": r.payload["text"],
            "file_id": r.payload["file_id"],
            "chunk_id": r.payload["chunk_id"]
        })
    
    return chunks