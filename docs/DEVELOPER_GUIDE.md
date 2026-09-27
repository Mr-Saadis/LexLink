# LexLink Developer Guide

This guide is designed to help you understand the architecture of LexLink and where to put new code as you build out features. It also covers how to run the project locally.

---

## 1. How to Run the Project

Since LexLink has separate backend (Python) and frontend (Node.js) environments, you must run both simultaneously.

### Running Frontend
1. Open a terminal and navigate to the frontend: `cd frontend`
2. Install packages (if you haven't): `npm install`
3. Start the dev server: `npm run dev`
*(Your frontend will run at `http://localhost:5173`)*

### Running Backend
1. Open a terminal and navigate to the backend: `cd backend`
2. Create a virtual environment: `python -m venv venv` 
   *(Note: if `python` is not recognized on your system, use `py -m venv venv` or ensure Python is added to your Windows PATH).*
3. Activate the virtual environment:
   - Windows: `.\venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start the server: `uvicorn api_server:app --reload --port 8000`
*(Your backend API will run at `http://localhost:8000`)*

---

## 2. Unused Dependencies (Cleanup)

During our audit, we noticed the following about your `package.json` and `requirements.txt`:
- **Frontend**: The `tailwindcss` package is flagged as potentially unused by `depcheck`. However, since you are using `@tailwindcss/vite` (Tailwind v4), this is a false positive. **Do not delete it**. The rest of your frontend packages are clean.
- **Backend**: You have `batch_cli.py` and `judgement_pipeline.py`. If these are old scripts you no longer use, consider moving them to an `archive/` or `scripts/` folder so your root backend folder stays clean.

---

## 3. Where to Write New Code? (File Structuring)

To keep the project professional, avoid dumping all code into `App.tsx` (frontend) or `api_server.py` (backend). Follow these standard structures:

### Frontend Structure (`frontend/src/`)
When building the UI, organize your files into these folders inside `src/`:

- `components/` 
  - **What goes here:** Reusable UI elements (e.g., `Button.tsx`, `Navbar.tsx`, `Card.tsx`).
  - **Rule:** These should NOT fetch data. They just receive `props` and render HTML.
- `pages/` (or `views/`)
  - **What goes here:** Full screen views (e.g., `HomePage.tsx`, `Dashboard.tsx`).
  - **Rule:** These pages will use the components from `components/` and tie them together.
- `hooks/`
  - **What goes here:** Custom React hooks (e.g., `useFetch.ts`, `useAuth.ts`).
- `services/` or `api/`
  - **What goes here:** All your `fetch` or `axios` calls to the Python backend. E.g., `api.ts`.
- `assets/`
  - **What goes here:** Images, SVGs, and global CSS.

**Example Step-by-Step for a new "Login" feature:**
1. Create `src/pages/LoginPage.tsx`.
2. Create a reusable input field in `src/components/InputField.tsx`.
3. Use `<InputField />` inside `LoginPage.tsx`.
4. Create the API call in `src/api/auth.ts`.

### Backend Structure (`backend/`)
The backend is structured into clear Python service files:

- `api_server.py`: FastAPI server containing REST endpoints, streaming upload pipeline, and authentication middleware.
- `supabase_client.py`: Supabase database operations, JWT authentication, and bcrypt password verification.
- `judgement_pipeline.py`: PDF text block parsing, boilerplate cleanup, and bounding box chunking.
- `qdrant_manager.py`: BAAI/bge-m3 embedding calculations and Qdrant vector database indexing.
- `r2_client.py`: Cloudflare R2 object storage client for original PDF archiving.
- `seed_admin.py`: CLI tool for bootstrapping and provisioning Administrator accounts.
