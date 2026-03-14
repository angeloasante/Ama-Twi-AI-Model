-- ============================================================
-- Supabase SQL: Conversations & Messages tables
-- Run this in your Supabase SQL Editor (Dashboard → SQL Editor)
-- ============================================================

-- 1. Conversations table
create table if not exists conversations (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  title       text not null default 'New Chat',
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- 2. Messages table
create table if not exists messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references conversations(id) on delete cascade,
  role            text not null check (role in ('user', 'assistant')),
  content         text not null,
  language        text,
  tools_used      jsonb default '[]'::jsonb,
  tool_results    jsonb default '{}'::jsonb,
  reaction        text check (reaction in ('up', 'down', null)),
  created_at      timestamptz not null default now()
);

-- 3. Indexes for fast lookups
create index if not exists idx_conversations_user_id on conversations(user_id);
create index if not exists idx_conversations_updated_at on conversations(updated_at desc);
create index if not exists idx_messages_conversation_id on messages(conversation_id);
create index if not exists idx_messages_created_at on messages(created_at);

-- 4. Auto-update updated_at on conversations
create or replace function update_conversation_timestamp()
returns trigger as $$
begin
  update conversations set updated_at = now() where id = new.conversation_id;
  return new;
end;
$$ language plpgsql;

create or replace trigger trigger_update_conversation_timestamp
after insert on messages
for each row execute function update_conversation_timestamp();

-- 5. Row Level Security — users can only access their own data
alter table conversations enable row level security;
alter table messages enable row level security;

-- Conversations policies
create policy "Users can view own conversations"
  on conversations for select
  using (auth.uid() = user_id);

create policy "Users can insert own conversations"
  on conversations for insert
  with check (auth.uid() = user_id);

create policy "Users can update own conversations"
  on conversations for update
  using (auth.uid() = user_id);

create policy "Users can delete own conversations"
  on conversations for delete
  using (auth.uid() = user_id);

-- Messages policies (via conversation ownership)
create policy "Users can view own messages"
  on messages for select
  using (
    exists (
      select 1 from conversations
      where conversations.id = messages.conversation_id
      and conversations.user_id = auth.uid()
    )
  );

create policy "Users can insert own messages"
  on messages for insert
  with check (
    exists (
      select 1 from conversations
      where conversations.id = messages.conversation_id
      and conversations.user_id = auth.uid()
    )
  );

create policy "Users can update own messages"
  on messages for update
  using (
    exists (
      select 1 from conversations
      where conversations.id = messages.conversation_id
      and conversations.user_id = auth.uid()
    )
  );

create policy "Users can delete own messages"
  on messages for delete
  using (
    exists (
      select 1 from conversations
      where conversations.id = messages.conversation_id
      and conversations.user_id = auth.uid()
    )
  );
