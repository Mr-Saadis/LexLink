# LexLink Rules

These rules apply to all agents working on the LexLink project.

## Architecture and Structure
- Maintain strict decoupling between the Python backend and Vite frontend.
- Do not mix package managers. `npm` is for frontend, `pip` (or `uv`/`poetry`) is for backend.
- The root `package.json` is strictly for development orchestration (using `concurrently`).

## Code Standards
- **Backend:** 
  - Always pin Python dependencies in `requirements.txt` to avoid unexpected breakages.
  - Write standard FastAPI endpoints and respect Python typings.
- **Frontend:**
  - Enforce modern UI standards (React 19+, Tailwind CSS v4, Vite).
  - Use TypeScript strictly. No `any` unless absolutely necessary.
  - Maintain a clean component structure within `frontend/src`.

## Best Practices
- Run `npm audit` periodically on the frontend.
- Ensure backend API URLs are handled through environment variables (`VITE_API_URL` in frontend).
