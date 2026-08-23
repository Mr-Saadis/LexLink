# LexLink Database Schema Specification (Supabase / PostgreSQL)

This document represents the active database schema configured in Supabase / PostgreSQL for the **LexLink** platform.

---

## 📊 Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    AUTH_USERS ||--|| PROFILES : has
    PROFILES ||--o| LAWYER_STUDENT_DETAILS : has_details
    PROFILES ||--o{ DOCUMENTS : uploaded_by
    PROFILES ||--o{ SAVED_DOCUMENTS : saves
    PROFILES ||--o{ RECENT_DOCUMENTS : views
    PROFILES ||--o{ HIGHLIGHTS : creates
    PROFILES ||--o{ NOTES : writes
    PROFILES ||--o{ CHAT_SESSIONS : owns
    PROFILES ||--o{ TOKEN_USAGE : consumes
    PROFILES ||--o{ CASE_PREDICTIONS : generates

    DOCUMENTS ||--|{ CHUNKS : has
    DOCUMENTS ||--o{ SAVED_DOCUMENTS : saved_in
    DOCUMENTS ||--o{ RECENT_DOCUMENTS : viewed_in
    DOCUMENTS ||--o{ HIGHLIGHTS : contains
    DOCUMENTS ||--o{ NOTES : annotated_in
    DOCUMENTS ||--o{ CHAT_SESSIONS : contextualizes

    CHUNKS ||--o{ HIGHLIGHTS : targets
    CHUNKS ||--o{ NOTES : targets

    CHAT_SESSIONS ||--|{ CHAT_MESSAGES : contains
```

---

## 🗄️ Database DDL (Production Supabase Schema)

```sql
-- ============================================
-- Enable UUID generation
-- ============================================
create extension if not exists "pgcrypto";

-- ============================================
-- Profiles (Tied to Supabase auth.users)
-- ============================================
create table public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    name text,
    role text not null
        check (role in ('layman', 'lawyer', 'student', 'admin')),
    verification_status text
        default 'not_required'
        check (
            verification_status in (
                'not_required',
                'pending',
                'approved',
                'rejected'
            )
        ),
    created_at timestamptz default now()
);

-- ============================================
-- Lawyer / Student Details
-- ============================================
create table public.lawyer_student_details (
    id uuid primary key default gen_random_uuid(),
    user_id uuid
        references public.profiles(id)
        on delete cascade,
    license_no text,
    cnic text,
    student_id text,
    created_at timestamptz default now()
);

-- ============================================
-- Documents
-- ============================================
create table public.documents (
    id uuid primary key default gen_random_uuid(),
    title text,
    court text,
    court_type text not null
        check (court_type in ('SC', 'HC')),
    court_type_declared text
        check (court_type_declared in ('SC', 'HC')),
    case_number text,
    parties text,
    judge text,
    judgment_date text,
    dates_of_hearing text,
    source_file text,
    pdf_url text,
    total_lines integer default 0,
    total_chunks integer default 0,
    metadata jsonb default '{}'::jsonb,
    uploaded_by uuid
        references public.profiles(id)
        on delete set null,
    created_at timestamptz default now()
);

-- ============================================
-- Chunks
-- ============================================
create table public.chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null
        references public.documents(id)
        on delete cascade,
    chunk_index integer not null,
    text text not null,
    word_count integer,
    page_start integer not null,
    page_end integer not null,
    bbox jsonb,
    qdrant_point_id uuid,
    source_file text,
    created_at timestamptz default now()
);

-- ============================================
-- Ingestion Failures
-- ============================================
create table public.ingestion_failures (
    id uuid primary key default gen_random_uuid(),
    source_file text,
    court_type text,
    reason text,
    created_at timestamptz default now()
);

-- ============================================
-- Saved Documents
-- ============================================
create table public.saved_documents (
    id uuid primary key default gen_random_uuid(),
    user_id uuid
        references public.profiles(id)
        on delete cascade,
    document_id uuid
        references public.documents(id)
        on delete cascade,
    saved_at timestamptz default now(),
    unique(user_id, document_id)
);

-- ============================================
-- Recent Documents
-- ============================================
create table public.recent_documents (
    id uuid primary key default gen_random_uuid(),
    user_id uuid
        references public.profiles(id)
        on delete cascade,
    document_id uuid
        references public.documents(id)
        on delete cascade,
    last_opened_at timestamptz default now(),
    unique(user_id, document_id)
);

-- ============================================
-- Highlights
-- ============================================
create table public.highlights (
    id uuid primary key default gen_random_uuid(),
    user_id uuid
        references public.profiles(id)
        on delete cascade,
    document_id uuid
        references public.documents(id)
        on delete cascade,
    chunk_id uuid
        references public.chunks(id)
        on delete cascade,
    bbox jsonb,
    created_at timestamptz default now()
);

-- ============================================
-- Notes
-- ============================================
create table public.notes (
    id uuid primary key default gen_random_uuid(),
    user_id uuid
        references public.profiles(id)
        on delete cascade,
    document_id uuid
        references public.documents(id)
        on delete cascade,
    chunk_id uuid
        references public.chunks(id)
        on delete cascade,
    content text,
    created_at timestamptz default now()
);

-- ============================================
-- Chat Sessions
-- ============================================
create table public.chat_sessions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid
        references public.profiles(id)
        on delete cascade,
    document_id uuid
        references public.documents(id)
        on delete set null,
    session_type text
        check (
            session_type in (
                'general',
                'document',
                'layman'
            )
        ),
    created_at timestamptz default now()
);

-- ============================================
-- Chat Messages
-- ============================================
create table public.chat_messages (
    id uuid primary key default gen_random_uuid(),
    session_id uuid
        references public.chat_sessions(id)
        on delete cascade,
    sender text
        check (sender in ('user', 'ai')),
    content text,
    created_at timestamptz default now()
);

-- ============================================
-- Token Usage
-- ============================================
create table public.token_usage (
    id uuid primary key default gen_random_uuid(),
    user_id uuid
        references public.profiles(id)
        on delete cascade,
    tokens_used integer,
    request_type text,
    usage_date date default current_date
);

-- ============================================
-- Case Predictions
-- ============================================
create table public.case_predictions (
    id uuid primary key default gen_random_uuid(),
    user_id uuid
        references public.profiles(id)
        on delete cascade,
    case_description text,
    win_probability numeric(5,2),
    reference_document_ids uuid[],
    strengths text,
    weaknesses text,
    created_at timestamptz default now()
);

-- ============================================
-- Legal Dictionary
-- ============================================
create table public.legal_dictionary (
    id uuid primary key default gen_random_uuid(),
    term text not null,
    language text
        check (
            language in (
                'en',
                'ur',
                'roman_ur'
            )
        ),
    definition text,
    created_at timestamptz default now()
);

-- ============================================
-- Performance Indexes
-- ============================================
create index idx_documents_title on public.documents(title);
create index idx_documents_case_number on public.documents(case_number);
create index idx_documents_court on public.documents(court);
-- NOTE: doc_type index removed — column does not exist in documents table
create index idx_documents_metadata on public.documents using gin(metadata);

create index idx_chunks_document on public.chunks(document_id);
create index idx_chunks_qdrant on public.chunks(qdrant_point_id);

create index idx_saved_documents_user on public.saved_documents(user_id);
create index idx_recent_documents_user on public.recent_documents(user_id);

create index idx_highlights_user on public.highlights(user_id);
create index idx_notes_user on public.notes(user_id);

create index idx_chat_sessions_user on public.chat_sessions(user_id);
create index idx_chat_messages_session on public.chat_messages(session_id);

create index idx_token_usage_user on public.token_usage(user_id);
create index idx_case_predictions_user on public.case_predictions(user_id);
create index idx_dictionary_term on public.legal_dictionary(term);
```

---

## 📝 Document Table Notes & Observational Review

> [!NOTE]
> **User Observation Regarding `documents` table:**
> The `documents` table currently contains fields for court categorization (`court_type in ('SC', 'HC')`), `parties`, `judges` (jsonb), and `judgment_date` (text). If fine-tuning is required later (such as splitting date into standard `DATE` type or adding full-text search tsvectors), it will be handled in a dedicated migration.
