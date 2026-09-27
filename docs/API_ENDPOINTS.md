# LexLink API Endpoints Specification

This document is the complete REST and Streaming API reference for the LexLink backend.

---

## 🔐 Global Authentication & Headers

All authenticated requests must include the JWT bearer token in the `Authorization` header:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## 1. Authentication & User Profile (`/api/auth`)

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/signup` | Public | Register new user account (default `layman` or `lawyer`). Passwords hashed with bcrypt. |
| `POST` | `/api/auth/login` | Public | Authenticate credentials; returns signed JWT bearer token and user profile. |
| `GET`  | `/api/auth/me` | Authenticated | Retrieve current user profile, role, and verification status via Bearer JWT. |

---

## 2. Document Ingestion & Management (`/api/documents`)

### `POST /api/upload-judgment` (or `/api/documents/upload`)
- **Access:** Authenticated (Student, Lawyer, Admin) — `Authorization: Bearer <token>` required.
- **Content-Type:** `multipart/form-data`
- **Body:**
  - `file: Binary PDF` (Required)
  - `dry_run: boolean` (default: `true`)
  - `declared_court_type: "SC" | "HC"` (default: `"SC"`)
  - `embed_qdrant: boolean` (default: `true`)
- **Security:** Uploader identity is derived strictly from the verified JWT session token. Spoofing is prevented.
- **Response:** Streaming `application/x-ndjson`
  ```json
  {"type": "progress", "stage_index": 1, "stage_name": "parsing"}
  {"type": "progress", "stage_index": 2, "stage_name": "chunking"}
  {"type": "progress", "stage_index": 3, "stage_name": "verifying"}
  {"type": "final", "success": true, "metadata": {"case_number": "SC-12/2022", "court": "SUPREME COURT OF PAKISTAN", "declared_court_type": "SC"}, "total_chunks": 38, "json_saved_to": "...", "db_persisted": true, "qdrant_embedded": true}
  ```

### `GET /api/documents`
- **Access:** Authenticated Users (`Authorization: Bearer <token>`)
- **Query Params:** `limit=50`, `offset=0`
- **Response:**
  ```json
  {
    "documents": [
      {
        "id": "uuid",
        "title": "SC-12/2022 - Federation of Pakistan vs. Tariq",
        "court_type": "SC",
        "total_lines": 350,
        "total_chunks": 38,
        "source_file": "judgment_12_2022.pdf",
        "pdf_url": "https://r2.lexlink.pk/judgments/...",
        "created_at": "2026-09-27T10:00:00Z",
        "uploaded_by": "00000000-0000-0000-0000-000000000001"
      }
    ]
  }
  ```

### `GET /api/stats`
- **Access:** Public / Authenticated
- **Response:**
  ```json
  {
    "status": "online",
    "documents_count": 42,
    "chunks_count": 890,
    "qdrant_points_count": 890,
    "qdrant_status": "online",
    "qdrant_connected": true,
    "supabase_connected": true,
    "cloudflare_r2_connected": true,
    "vector_dimension": 1024,
    "embedding_model": "BAAI/bge-m3",
    "recent_documents": [...]
  }
  ```

---

## 3. Qdrant Vector Engine & Verification (`/api/qdrant`)

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET`  | `/api/qdrant/status` | Public / Authenticated | Returns Qdrant cluster status, vector dimension, and indexed point count. |
| `GET`  | `/api/qdrant/export` | **Admin Only** | Generates and returns structured JSON dump of points in `qdrant_output/`. |
| `POST` | `/api/qdrant/search` | Authenticated | Executes 1024-dim dense semantic vector similarity search via BAAI/bge-m3. |

---

## 3. Bounding-Box Chunks (`/api/documents/{id}/chunks`)

### `GET /api/documents/{id}/chunks`
- **Access:** Student, Lawyer, Admin
- **Query Params:** `page_number=3` (optional)
- **Response:**
  ```json
  {
    "document_id": "uuid",
    "chunks": [
      {
        "id": "uuid",
        "page_number": 3,
        "chunk_index": 12,
        "text": "The high court erred in holding that...",
        "bbox": [72.0, 140.5, 520.0, 210.2],
        "chunk_type": "holding"
      }
    ]
  }
  ```

---

## 4. Highlights & Annotations (`/api/documents/{id}/highlights`)

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET`  | `/api/documents/{id}/highlights` | Student, Lawyer, Admin | List all highlights in the document. |
| `POST` | `/api/documents/{id}/highlights` | Student, Lawyer, Admin | Create a new visual bounding-box highlight. |
| `DELETE` | `/api/highlights/{highlight_id}` | Owner, Admin | Delete an existing highlight. |

---

## 5. Sticky Notes (`/api/documents/{id}/notes`)

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET`  | `/api/documents/{id}/notes` | Student, Lawyer, Admin | Retrieve sticky notes for document. |
| `POST` | `/api/documents/{id}/notes` | Student, Lawyer, Admin | Create a sticky note with `(x, y)` coordinates. |
| `PUT`  | `/api/notes/{note_id}` | Owner | Update content or privacy of sticky note. |
| `DELETE` | `/api/notes/{note_id}` | Owner, Admin | Remove sticky note. |

---

## 6. Vector Search & RAG (`/api/search`)

### `POST /api/search/vector`
- **Access:** Student, Lawyer, Admin
- **Request Body:**
  ```json
  {
    "query": "bail cancellation ground post-arrest under Section 497(5)",
    "filters": {
      "court": "Supreme Court",
      "year_from": 2019
    },
    "top_k": 10
  }
  ```
- **Response:**
  ```json
  {
    "query": "...",
    "results": [
      {
        "document_id": "uuid",
        "case_title": "State vs. Tariq",
        "citation": "2023 SCMR 45",
        "score": 0.912,
        "matched_chunk": "Bail once granted cannot be cancelled casually...",
        "page_number": 6,
        "bbox": [72.0, 310.0, 515.0, 390.0]
      }
    ]
  }
  ```

---

## 7. AI Legal Assistant & Chat Sessions (`/api/chat`)

### `POST /api/chat/sessions`
- **Access:** Student, Lawyer, Admin
- **Body:** `{ "document_id": "uuid", "title": "Bail Precedents Query" }`
- **Response:** `{ "session_id": "uuid", "title": "Bail Precedents Query", "created_at": "..." }`

### `POST /api/chat/sessions/{session_id}/message`
- **Access:** Student, Lawyer, Admin
- **Headers:** `Accept: text/event-stream`
- **Body:** `{ "message": "Summarize the legal ratio in paragraph 4." }`
- **Streaming Response (SSE):**
  ```
  event: chunk
  data: {"delta": "The court established that..."}

  event: citation
  data: {"citation": "Page 4, Para 12", "chunk_id": "uuid", "bbox": [72, 100, 520, 180]}

  event: done
  data: {"total_tokens": 620}
  ```

---

## 8. Layman Case Predictions & Dictionary (`/api/predictions`, `/api/dictionary`)

### `POST /api/predictions/outcome`
- **Access:** All Roles (Rate-limited for Layman)
- **Body:** `{ "matter_type": "Service Law", "facts_summary": "Termination without show-cause notice...", "province": "Sindh" }`
- **Response:**
  ```json
  {
    "favorable_probability": 0.82,
    "confidence": "High",
    "plain_summary": "Termination without due process violates principles of natural justice...",
    "disclaimer": "This is an automated legal estimate."
  }
  ```

---

## 9. Admin Platform Telemetry & Verification (`/api/admin`)

| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET`  | `/api/admin/analytics/overview` | Admin Only | System stats (active users, vectors, errors). |
| `GET`  | `/api/admin/verifications/pending`| Admin Only | List pending Lawyer/Student verification proofs. |
| `POST` | `/api/admin/verifications/{id}/review` | Admin Only | Approve or reject verification (`status`, `reason`). |
| `GET`  | `/api/admin/tokens/usage` | Admin Only | Token consumption breakdown by model and role. |
| `GET`  | `/api/admin/audit-logs` | Admin Only | Query immutable security audit log trail. |
