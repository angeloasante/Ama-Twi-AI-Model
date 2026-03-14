-- ============================================================
-- Supabase SQL: Memory System — pgvector + user_memory + summaries
-- Run this in your Supabase SQL Editor AFTER the conversations schema
-- ============================================================

-- 0. Enable pgvector extension
create extension if not exists vector with schema extensions;

-- ============================================================
-- 1. MESSAGE EMBEDDINGS — for RAG semantic search
-- ============================================================
create table if not exists message_embeddings (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  conversation_id uuid not null references conversations(id) on delete cascade,
  message_id      text not null,
  role            text not null check (role in ('user', 'assistant')),
  content         text not null,
  embedding       vector(384) not null,  -- sentence-transformers/all-MiniLM-L6-v2 = 384 dims
  created_at      timestamptz not null default now()
);

create index if not exists idx_embeddings_user_id on message_embeddings(user_id);
create index if not exists idx_embeddings_conversation_id on message_embeddings(conversation_id);

-- IVFFlat index for fast vector search (create AFTER you have some data, or use HNSW)
-- Using HNSW which works immediately without training data:
create index if not exists idx_embeddings_vector on message_embeddings
  using hnsw (embedding vector_cosine_ops);

-- RPC function: semantic search across a user's past messages
create or replace function match_messages(
  query_embedding vector(384),
  match_threshold float default 0.7,
  match_count int default 5,
  p_user_id uuid default null
)
returns table (
  id uuid,
  conversation_id uuid,
  message_id text,
  role text,
  content text,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    me.id,
    me.conversation_id,
    me.message_id,
    me.role,
    me.content,
    1 - (me.embedding <=> query_embedding) as similarity
  from message_embeddings me
  where
    (p_user_id is null or me.user_id = p_user_id)
    and 1 - (me.embedding <=> query_embedding) > match_threshold
  order by me.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- ============================================================
-- 2. USER MEMORY — long-term facts about the user
-- ============================================================
create table if not exists user_memory (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  facts       jsonb not null default '[]'::jsonb,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique(user_id)
);

create index if not exists idx_user_memory_user_id on user_memory(user_id);

-- ============================================================
-- 3. CONVERSATION SUMMARIES — compressed conversation context
-- ============================================================
alter table conversations
  add column if not exists summary text default null,
  add column if not exists message_count int default 0;

-- ============================================================
-- 4. ROW LEVEL SECURITY
-- ============================================================
alter table message_embeddings enable row level security;
alter table user_memory enable row level security;

-- message_embeddings policies
create policy "Users can view own embeddings"
  on message_embeddings for select
  using (auth.uid() = user_id);

create policy "Users can insert own embeddings"
  on message_embeddings for insert
  with check (auth.uid() = user_id);

create policy "Users can delete own embeddings"
  on message_embeddings for delete
  using (auth.uid() = user_id);

-- user_memory policies
create policy "Users can view own memory"
  on user_memory for select
  using (auth.uid() = user_id);

create policy "Users can insert own memory"
  on user_memory for insert
  with check (auth.uid() = user_id);

create policy "Users can update own memory"
  on user_memory for update
  using (auth.uid() = user_id);

create policy "Users can delete own memory"
  on user_memory for delete
  using (auth.uid() = user_id);
