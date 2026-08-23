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
| `POST` | `/api/auth/signup` | Public | Register new user account (default `layman`). |
| `POST` | `/api/auth/login` | Public | Authenticate credentials; returns access & refresh tokens. |
| `POST` | `/api/auth/refresh` | Public | Rotate refresh token and issue new access token. |
| `GET`  | `/api/auth/me` | Authenticated | Retrieve current user profile, role, and verification status. |
| `POST` | `/api/auth/verify-role`| Authenticated | Submit credentials (Bar ID / Student Card) for role upgrade. |

---

## 2. Document Ingestion & Management (`/api/documents`)

### `POST /api/documents/upload` (or `/api/upload-judgment`)
- **Access:** Student, Lawyer, Admin
- **Content-Type:** `multipart/form-data`
- **Body:** `file: Binary PDF`, `dry_run: boolean` (default: `true`), `court_type: "SC" | "HC"` (default: `"SC"`), `court_type_declared: "SC" | "HC"`
- **Response:** Streaming `application/x-ndjson`
  ```json
  {"type": "progress", "stage_index": 0, "stage_name": "Upload"}
  {"type": "progress", "stage_index": 1, "stage_name": "Parse & Extract"}
  {"type": "progress", "stage_index": 2, "stage_name": "Chunk & Embed"}
  {"type": "final", "success": true, "metadata": {"case_number": "SC-12/2022", "court": "SUPREME COURT OF PAKISTAN", "court_type": "SC", "court_type_declared": "SC"}, "total_chunks": 38, "json_saved_to": "..."}
  ```

### `GET /api/documents`
- **Access:** Student, Lawyer, Admin
- **Query Params:** `page=1`, `limit=20`, `court=Supreme+Court`, `search=tenancy`
- **Response:**
  ```json
  {
    "total": 120,
    "page": 1,
    "items": [
      {
        "id": "uuid",
        "title": "Muhammad vs. Federation of Pakistan",
        "case_number": "SC-490/2021",
        "court": "Supreme Court",
        "total_pages": 14,
        "status": "indexed",
        "created_at": "2026-08-23T10:00:00Z"
      }
    ]
  }
  ```

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
