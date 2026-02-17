from typing import List, Dict, Any
from uuid import uuid4
from qdrant_client.http import models
from app.core.database import qdrant_client
from app.models.schemas import SubmissionCreate, AutofillRequest

COLLECTION_NAME = "user_form_data"

async def ensure_collection():
    if not await qdrant_client.collection_exists(COLLECTION_NAME):
        await qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qdrant_client.get_fastembed_vector_params(),
        )
    
    # ensure index exists for filtering
    await qdrant_client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="user_id",
        field_schema="keyword"
    )

async def ingest_submission(user_id: str, submission: SubmissionCreate):
    await ensure_collection()
    
    documents = []
    metadata = []
    ids = []

    for key, value in submission.data.items():
        # embed the key and store the value
        if not isinstance(value, (str, int, float, bool)):
            continue # skip complex nested structures
            
        documents.append(key)
        metadata.append({
            "value": str(value),
            "original_key": key,
            "website": submission.website,
            "user_id": user_id,
            "type": "form_entry"
        })
        ids.append(str(uuid4()))

    if documents:
        # use upsert with fastembed integration
        points = [
            models.Document(
                page_content=doc,
                metadata=meta,
                id=id_
            ) for id_, doc, meta in zip(ids, documents, metadata)
        ]

        await qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )

async def search_autofill(user_id: str, request: AutofillRequest) -> Dict[str, Any]:
    # ensure collection exists
    if not await qdrant_client.collection_exists(COLLECTION_NAME):
        return {key: None for key in request.keys}

    results = {}
    
    for key in request.keys:
        # embed the search key locally using fastembed
        embeddings = list(qdrant_client._embed_documents(
            documents=[key],
            embedding_model_name=qdrant_client.embedding_model_name,
        ))
        if not embeddings or not embeddings[0]:
            results[key] = [] if request.multiple else None
            continue

        query_vector = embeddings[0][1]

        search_result = await qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            using="fast-bge-small-en",
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id)
                    )
                ]
            ),
            limit=request.limit,
        )

        hits = search_result.points
        for h in hits:
            print(f"  '{key}' -> '{h.payload.get('original_key')}' = {h.score:.4f}")
        
        # filter manually since score_threshold is ignored by fastembed client
        hits = [h for h in hits if h.score >= request.threshold]

        if not hits:
            results[key] = [] if request.multiple else None
            continue

        if request.multiple:
            suggestions = [hit.payload["value"] for hit in hits]
            results[key] = suggestions
        else:
            results[key] = hits[0].payload["value"]
            
    return results
