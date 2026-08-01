from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, MatchAny
from app.core.config import COLLECTION_NAME

from app.core.qdrant import async_client

async def init_qdrant():
    try:
        collections = await async_client.get_collections()
        existing = [c.name for c in collections.collections]

        if COLLECTION_NAME not in existing:
            await async_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=384,
                    distance=Distance.COSINE
                )
            )
            print(f"Created collection {COLLECTION_NAME}")
        else:
            print(f"Collection {COLLECTION_NAME} already exists")
    except Exception as e:
        print(f"[WARN] Init Qdrant failed: {e}")


async def search(query_embed, file_ids, top_k):
    if not file_ids:
        query_filter = None
    else:
        print("file_ids", file_ids)
        file_ids = [str(x) for x in file_ids]

        query_filter = Filter(
            must=[
                FieldCondition(
                    key="file_id",
                    match=MatchAny(any=file_ids)
                )
            ]
        )

    results = await async_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embed,
        limit=top_k,
        query_filter=query_filter,
        with_payload=True
    )

    chunks = []
    points = results.points
    print("points:", len(points))

    for r in points:
        chunks.append({
            "score": r.score,
            "text": r.payload.get("text", ""),
            "file_id": r.payload.get("file_id", ""),
            "chunk_id": r.payload.get("chunk_id", "")
        })
    
    return chunks