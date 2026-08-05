# LexLink

LexLink is a monorepo project comprising a Python (FastAPI) backend and a Node.js (React/Vite) frontend.

## Project Structure

```text
LexLink/
├── backend/            # Python FastAPI application
│   ├── requirements.txt
│   └── ...
├── frontend/           # React + Vite application
│   ├── package.json
│   └── ...
├── .gitignore          
├── .agents/AGENTS.md   # Rules for agents working on this project
├── package.json        # Root script runner for concurrent execution
└── README.md
```

## Getting Started

### Prerequisites
- Node.js & npm (for frontend and root orchestrator)
- Python 3.9+ (for backend)

### Installation

1. **Install Root Orchestrator (Optional but recommended):**
   ```bash
   npm install
   ```

2. **Install Frontend Dependencies:**
   ```bash
   cd frontend
   npm install
   ```

3. **Install Backend Dependencies:**
   Create a virtual environment and install dependencies:
   ```bash
   cd backend
   python -m venv venv
   # Activate venv based on your OS (e.g., .\venv\Scripts\activate on Windows)
   pip install -r requirements.txt
   ```

### Running Locally

To run both the frontend and backend servers concurrently, from the root directory:
```bash
npm run dev
```

Alternatively, you can run them in separate terminals:
- **Frontend**: `cd frontend && npm run dev`
- **Backend**: `cd backend && uvicorn api_server:app --reload --port 8000`
