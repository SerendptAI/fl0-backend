# FL0 API

This repository contains the backend API for the FL0 application.

## Prerequisites

- Python 3.12 or higher
- uv (for dependency management)
- Docker (optional, for containerized deployment)

## Environment Configuration

Copy the `.env.example` file to `.env` and fill in the required values:

```bash
cp .env.example .env
```

### Required Variables

- `MONGO_URI`: Connection string for MongoDB.
- `MONGO_DB_NAME`: Name of the MongoDB database.
- `QDRANT_URL`: URL for the Qdrant vector database.
- `QDRANT_API_KEY`: API key for Qdrant.
- `GOOGLE_CLIENT_ID`: OAuth client ID from Google Cloud Console.
- `GOOGLE_CLIENT_SECRET`: OAuth client secret from Google Cloud Console.
- `SECRET_KEY`: Secret key for JWT encoding/decoding.
- `ALGORITHM`: Algorithm used for JWT (e.g., HS256).
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Expiration time for access tokens in minutes.
- `ACCESS_TOKEN_EXPIRES_MINUTE`: (Deprecated in favor of above, check implementation).
- `API_BASE_URL`: Base URL of the API (e.g., http://localhost:8001).

## Local Development

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Run the application:
   ```bash
   uv run uvicorn main:app --reload --port 8001
   ```

The API will be available at `http://localhost:8001`.

## Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t fl0-api .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 --env-file .env fl0-api
   ```

The API will be available at `http://localhost:8000`.

## API Documentation

Once the application is running, you can access the interactive API documentation at:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
