# LexLink Local Development & Setup Guide

This guide provides step-by-step instructions for getting the **LexLink** development environment running locally on Windows, macOS, or Linux.

---

## 🛠️ 1. Prerequisites

- **Python:** `3.10` or higher (`python --version`)
- **Node.js:** `v18.0.0` or higher (`node --version`)
- **Package Managers:** `pip` (Python) and `npm` (Node.js)
- **Optional / Recommended:** Docker Desktop (for running PostgreSQL & Qdrant locally)

---

## 🚀 2. Quick Start (Concurrently)

The root `package.json` includes orchestration scripts to start both backend and frontend simultaneously:

```bash
# 1. Install root dependencies (concurrently)
npm install

# 2. Run both Backend & Frontend in parallel
npm run dev
```

---

## 🐍 3. Manual Backend Setup (`backend/`)

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create Python virtual environment
python -m venv venv

# 3. Activate virtual environment
# On Windows (PowerShell):
.\venv\Scripts\activate
# On macOS / Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Copy environment template
cp .env.example .env

# 6. Start the FastAPI development server
uvicorn api_server:app --reload --port 8000
```

Backend API docs (Swagger UI) will be live at: **`http://localhost:8000/docs`**

---

## ⚛️ 4. Manual Frontend Setup (`frontend/`)

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Copy environment template
cp .env.example .env

# 4. Start Vite development server
npm run dev
```

Frontend application will be live at: **`http://localhost:5173`**

---

## 🔐 5. Environment Variables Reference

### Backend `.env` (`backend/.env`)
```env
# Server
PORT=8000
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Database (PostgreSQL / Supabase)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/lexlink

# Qdrant Vector DB
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# Security & JWT
JWT_SECRET_KEY=super_secret_jwt_key_change_in_production_min_32_chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI & LLM Providers
ANTHROPIC_API_KEY=your_claude_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### Frontend `.env` (`frontend/.env`)
```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME="LexLink Legal Intelligence"
```

---

## 🐳 6. Running Local Databases via Docker

```bash
# Start PostgreSQL
docker run -d --name lexlink-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=lexlink -p 5432:5432 postgres:15

# Start Qdrant Vector Database
docker run -d --name lexlink-qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest
```
