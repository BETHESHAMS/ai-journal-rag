-- ==============================================================================
-- Codeacious AI Engineering Intern: Personalized AI Journal (RAG MVP)
-- Database Schema for Supabase (PostgreSQL + pgvector)
-- ==============================================================================

-- 1. Enable the pgvector extension for dense vector similarity operations
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Users Table
-- Stores user credentials for multi-tenancy authentication.
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Index for fast user lookup during login
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);


-- 3. Journal Entries (Relational Data)
-- Stores the original journal entries submitted by users.
CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    entry_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Index for listing a user's past entries chronologically
CREATE INDEX IF NOT EXISTS idx_journal_entries_user_date ON journal_entries(user_id, entry_date DESC);


-- 4. Journal Chunks & Vector Store
-- Stores the chunked representation of journal entries along with dense embeddings.
-- Dimension 384 corresponds to standard lightweight embedding models (e.g. all-MiniLM-L6-v2 / BAAI/bge-small-en-v1.5).
-- If using OpenAI text-embedding-3-small (1536 dims), change vector(384) to vector(1536).
CREATE TABLE IF NOT EXISTS journal_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entry_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INT NOT NULL DEFAULT 0,
    entry_date DATE NOT NULL,
    embedding vector(384),
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Crucial multi-tenant index on user_id
CREATE INDEX IF NOT EXISTS idx_journal_chunks_user_id ON journal_chunks(user_id);
CREATE INDEX IF NOT EXISTS idx_journal_chunks_entry_id ON journal_chunks(entry_id);

-- HNSW (Hierarchical Navigable Small World) index for fast approximate nearest neighbor (ANN) search
-- Uses cosine distance operator (vector_cosine_ops)
CREATE INDEX IF NOT EXISTS idx_journal_chunks_embedding 
ON journal_chunks USING hnsw (embedding vector_cosine_ops);


-- 5. Strict Multi-Tenant Similarity Search Function
-- Executes semantic search strictly scoped to the authenticated user's ID.
-- Cosine similarity = 1 - (embedding <=> query_embedding)
CREATE OR REPLACE FUNCTION match_journal_chunks (
    query_embedding vector,
    match_count int,
    filter_user_id uuid
)
RETURNS TABLE (
    id uuid,
    entry_id uuid,
    chunk_text text,
    entry_date date,
    similarity float
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        jc.id,
        jc.entry_id,
        jc.chunk_text,
        jc.entry_date,
        (1 - (jc.embedding <=> query_embedding))::float AS similarity
    FROM journal_chunks jc
    WHERE jc.user_id = filter_user_id
    ORDER BY jc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
