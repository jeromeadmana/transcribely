# Transcribely - AI Video Transcription SaaS

A modern video transcription SaaS application that allows users to upload videos, automatically transcribe them using self-hosted Whisper AI, and manage their transcripts with team collaboration features.

## Tech Stack

- **Frontend**: Next.js 15 + TypeScript + Tailwind CSS
- **Backend**: FastAPI (Python 3.12+)
- **Transcription**: Self-hosted Whisper (faster-whisper)
- **Database**: PostgreSQL 16
- **Cache/Queue**: Redis + Celery
- **Storage**: MinIO (S3-compatible, local dev) / Cloudflare R2 (production)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.12+ (optional, for local backend development)

### 1. Clone and Setup

```bash
cd C:\sources\transcribely
cp .env.example .env
```

### 2. Start Backend Services

```bash
# Start all backend services (PostgreSQL, Redis, MinIO, FastAPI, Celery Worker)
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- Redis on port 6379
- MinIO on ports 9000 (API) and 9001 (Console)
- FastAPI backend on port 8000
- Celery worker for video processing

### 3. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at http://localhost:3000

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (login: minioadmin/minioadmin)

## Project Structure

```
transcribely/
├── frontend/                   # Next.js application
│   ├── app/                    # App router pages
│   ├── components/             # React components
│   └── lib/                    # Utilities and API client
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/routes/         # API endpoints
│   │   ├── core/               # Config, security, database
│   │   ├── models/             # SQLAlchemy models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── services/           # Business logic
│   │   └── tasks/              # Celery tasks
│   └── requirements.txt
├── docker-compose.yml
└── .env.example
```

## Features

- **User Authentication**: Email/password signup and login with JWT tokens
- **Organizations**: Multi-tenant support with team collaboration
- **Video Upload**: Drag-and-drop upload with presigned URLs (up to 2GB)
- **AI Transcription**: Self-hosted Whisper with automatic language detection
- **Real-time Progress**: SSE-based progress updates during processing
- **Transcript Viewer**: Timestamped segments with search and navigation
- **Export**: Download transcripts as TXT, JSON, SRT, or VTT

## API Endpoints

### Authentication
- `POST /api/auth/register` - Create new account
- `POST /api/auth/login` - Login and get tokens
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user

### Videos
- `POST /api/videos/upload-url` - Get presigned upload URL
- `POST /api/videos/complete` - Complete upload and start processing
- `GET /api/videos` - List videos
- `GET /api/videos/{id}` - Get video details
- `DELETE /api/videos/{id}` - Delete video

### Transcripts
- `GET /api/transcripts/{video_id}` - Get transcript
- `GET /api/transcripts/{video_id}/progress` - SSE progress stream
- `PATCH /api/transcripts/{video_id}` - Update transcript
- `GET /api/transcripts/{video_id}/export?format=srt` - Export transcript

## Configuration

### Whisper Model Options

In `.env` or `docker-compose.yml`:

```env
WHISPER_MODEL=base          # tiny, base, small, medium, large-v3
WHISPER_DEVICE=cpu          # cpu or cuda (for GPU)
WHISPER_COMPUTE_TYPE=int8   # int8 (CPU) or float16 (GPU)
```

| Model | Accuracy | Speed | VRAM |
|-------|----------|-------|------|
| tiny | 11.7% WER | Fastest | ~1GB |
| base | 9.2% WER | Fast | ~1GB |
| small | 7.6% WER | Medium | ~2GB |
| medium | 5.7% WER | Slow | ~5GB |
| large-v3 | 4.2% WER | Slowest | ~10GB |

### GPU Support

To enable GPU acceleration, uncomment the GPU section in `docker-compose.yml`:

```yaml
worker:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

## Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Running Celery Worker Locally

```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

## Production Deployment

For production:

1. Use Cloudflare R2 instead of MinIO for zero-egress video storage
2. Set `WHISPER_MODEL=large-v3` for best accuracy
3. Use GPU instances for faster transcription
4. Set up proper secrets in environment variables
5. Add rate limiting and monitoring

## License

MIT
