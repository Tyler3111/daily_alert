# Backend Setup

## Prerequisites
- Python 3.11+
- Docker and Docker Compose

## Quick Start

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run with docker-compose
docker-compose up -d

# Run the app
python -m src.main
```

## Endpoints
- `GET /health`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{id}`
- `POST /api/v1/refresh`
- `GET /api/v1/stats`
