-- ============================================================
-- Migration: Add user profile summary to user_memory
-- Run this in Supabase SQL Editor
-- ============================================================

-- Add profile summary column — a natural-language summary of the user
alter table user_memory
  add column if not exists profile_summary text default null;

-- Track when we last summarized so we don't redo it constantly
alter table user_memory
  add column if not exists last_summarized_at timestamptz default null;

-- Track how many messages were included in the last summary
alter table user_memory
  add column if not exists messages_at_last_summary int default 0;

-- ============================================================
-- RPC: Fetch all conversations + messages for a user (for Claude summarization)
-- ============================================================
create or replace function get_user_conversations_with_messages(p_user_id uuid)
returns json
language plpgsql
security definer  -- uses service role to bypass RLS
as $$
declare
  result json;
begin
  select json_agg(conv_data) into result
  from (
    select
      c.id as conversation_id,
      c.title,
      c.created_at,
      (
        select json_agg(
          json_build_object(
            'role', m.role,
            'content', m.content,
            'created_at', m.created_at
          )
          order by m.created_at asc
        )
        from messages m
        where m.conversation_id = c.id
      ) as messages
    from conversations c
    where c.user_id = p_user_id
    order by c.created_at desc
    limit 50  -- last 50 conversations max
  ) conv_data;

  return coalesce(result, '[]'::json);
end;
$$;
