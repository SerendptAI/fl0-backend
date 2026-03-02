import hashlib
import logging
from typing import List, Dict, Any, Optional
from qdrant_client.http import models
from app.core.database import qdrant_client
from app.models.schemas import SubmissionCreate, AutofillRequest

logger = logging.getLogger(__name__)

COLLECTION_NAME = "user_form_data"
EMBEDDING_MODEL = "BAAI/bge-small-en"


def _point_id(user_id: str, website: str, path: str, form_id: str | None, key: str) -> str:
    """deterministic id so re-ingesting the same field overwrites instead of duplicating."""
    raw = f"{user_id}:{website}:{path}:{form_id}:{key}"
    return hashlib.md5(raw.encode()).hexdigest()


async def ensure_collection():
    if await qdrant_client.collection_exists(COLLECTION_NAME):
        # check if collection has the correct (unnamed) vector config
        info = await qdrant_client.get_collection(COLLECTION_NAME)
        if isinstance(info.config.params.vectors, dict):
            # old collection uses named vectors, recreate with unnamed
            logger.info("Recreating qdrant collection with correct vector config")
            await qdrant_client.delete_collection(COLLECTION_NAME)

    if not await qdrant_client.collection_exists(COLLECTION_NAME):
        await qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=384,
                distance=models.Distance.COSINE,
            ),
        )

    # ensure indexes exist for filtering
    for field in ("user_id", "website", "path", "form_id"):
        await qdrant_client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema="keyword",
        )


async def ingest_submission(user_id: str, submission: SubmissionCreate):
    try:
        await ensure_collection()

        documents = []
        metadata = []
        ids = []

        for key, value in submission.data.items():
            if not isinstance(value, (str, int, float, bool)):
                continue

            documents.append(key)
            metadata.append({
                "value": str(value),
                "original_key": key,
                "website": submission.website,
                "path": submission.path,
                "form_id": submission.form_id,
                "user_id": user_id,
                "type": "form_entry"
            })
            ids.append(_point_id(user_id, submission.website, submission.path, submission.form_id, key))

        if documents:
            points = [
                models.PointStruct(
                    id=pid,
                    vector=models.Document(text=doc, model=EMBEDDING_MODEL),
                    payload=meta,
                )
                for pid, doc, meta in zip(ids, documents, metadata)
            ]
            await qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
            )
    except Exception as e:
        logger.warning(f"[vector] ingestion failed (qdrant may be unreachable): {e}")


async def search_autofill(user_id: str, request: AutofillRequest) -> List[Dict[str, Any]]:
    try:
        if not await qdrant_client.collection_exists(COLLECTION_NAME):
            return []
    except Exception as e:
        logger.warning(f"[vector] qdrant unreachable, returning empty: {e}")
        return []

    # build filter conditions
    must_conditions = [
        models.FieldCondition(
            key="user_id",
            match=models.MatchValue(value=user_id)
        )
    ]

    if request.website:
        must_conditions.append(
            models.FieldCondition(
                key="website",
                match=models.MatchValue(value=request.website)
            )
        )
    if request.path:
        must_conditions.append(
            models.FieldCondition(
                key="path",
                match=models.MatchValue(value=request.path)
            )
        )
    if request.form_id:
        must_conditions.append(
            models.FieldCondition(
                key="form_id",
                match=models.MatchValue(value=request.form_id)
            )
        )

    query_filter = models.Filter(must=must_conditions)

    # collect all hits across keys, grouped by website
    # structure: { website: { key: [ (score, value), ... ] } }
    website_hits: Dict[str, Dict[str, list]] = {}

    for key in request.keys:
        try:
            search_result = await qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=models.Document(text=key, model=EMBEDDING_MODEL),
                query_filter=query_filter,
                limit=request.limit * 5,  # fetch extra to cover multiple websites
            )

            for h in search_result.points:
                print(f"  '{key}' -> '{h.payload.get('original_key')}' = {h.score:.4f}")

            # filter by threshold
            hits = [h for h in search_result.points if h.score >= request.threshold]

            for hit in hits:
                website = hit.payload.get("website", "unknown")
                if website not in website_hits:
                    website_hits[website] = {}
                if key not in website_hits[website]:
                    website_hits[website][key] = []
                website_hits[website][key].append((hit.score, hit.payload["value"]))

        except Exception as e:
            logger.warning(f"[vector] search failed for key '{key}': {e}")

    # sort websites by number of matched keys (descending), then build response
    sorted_websites = sorted(website_hits.keys(), key=lambda w: len(website_hits[w]), reverse=True)

    # cap number of websites
    sorted_websites = sorted_websites[:request.limit]

    suggestions = []
    for website in sorted_websites:
        fields: Dict[str, Any] = {}
        for key in request.keys:
            key_hits = website_hits[website].get(key)
            if not key_hits:
                fields[key] = [] if request.multiple else None
                continue

            # sort by score descending
            key_hits.sort(key=lambda x: x[0], reverse=True)

            if request.multiple:
                fields[key] = [val for _, val in key_hits]
            else:
                fields[key] = key_hits[0][1]

        suggestions.append({"website": website, "fields": fields})

    return suggestions

