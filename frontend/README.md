# Ama (Twi AI) - Frontend

The web frontend for **Ama**, a bilingual Twi-English AI assistant powered by a fine-tuned Qwen3.5-9B model. Built by [Angelo Asante](https://www.angeloasante.com).

## Tech Stack

- **Next.js 16** (App Router) + React 19 + TypeScript
- **Tailwind CSS 4** + shadcn/ui components
- **Supabase** — auth, conversation persistence, memory/embeddings storage
- **Zustand** — client-side state management
- **Framer Motion** — animations
- **react-markdown** — rendering markdown/code in chat messages

## Architecture

The frontend is a **thin proxy** — all AI inference, tool execution, and API keys live on the Modal backend. The frontend handles UI, auth, and conversation management only.

```
frontend/
├── app/
│   ├── api/
│   │   ├── chat/          # Proxy to Modal agentic endpoint
│   │   ├── embeddings/    # Proxy to HF embedding API (server-side)
│   │   ├── memory/        # Memory summarization (Claude)
│   │   └── title/         # AI-generated conversation titles
│   ├── auth/              # Supabase auth callback
│   ├── layout.tsx
│   └── page.tsx
├── components/
│   ├── chat/              # Chat UI (Message, Input, ToolsUsed, DocumentSheet)
│   ├── layout/            # Sidebar, EmptyState
│   ├── auth/              # AuthLayout
│   ├── settings/          # SettingsPanel, ProfileSheet
│   └── ui/                # shadcn primitives (button, card, sheet, etc.)
├── hooks/
│   ├── useChat.ts         # Core chat logic, sends messages, manages history
│   ├── useConversationSync.ts  # Syncs conversations with Supabase
│   ├── useVoice.ts        # Voice input
│   ├── useTheme.ts        # Dark/light mode
│   └── useSidebar.ts      # Sidebar state
├── lib/
│   ├── conversations.ts   # Supabase CRUD for conversations/messages
│   ├── memory.ts          # RAG context building, embeddings, user profiles
│   ├── embeddings.ts      # HF embedding API client (via /api/embeddings)
│   ├── generateTitle.ts   # AI title generation
│   ├── supabase.ts        # Supabase client setup
│   └── utils.ts           # Shared utilities
└── store/
    └── useStore.ts        # Zustand store (chats, settings, preferences)
```

## Features

- **Bilingual chat** — Twi/English code-switching with Ghanaian personality
- **Agentic tools** — web search, image search, time, Twi phrase teaching, document creation (all executed on Modal)
- **Conversation memory** — RAG-powered context using Supabase pgvector + HF embeddings
- **User profiles** — auto-generated from conversation history for personalized responses
- **Conversation persistence** — synced to Supabase, survives browser refresh
- **Auth** — Supabase email/OAuth sign-in
- **Dark/light mode** — theme toggle
- **Voice input** — browser speech recognition
- **Markdown rendering** — code blocks, headers, bold, lists in chat messages
- **Mobile responsive** — sidebar collapses, touch-friendly

## Setup

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment Variables

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key |
| `SUPABASE_SERVICE_KEY` | Supabase service role key (server-side only) |
| `ANTHROPIC_API_KEY` | For title generation and memory summarization |
| `HF_TOKEN` | HuggingFace token for embeddings (server-side only) |
| `MODAL_CHAT_ENDPOINT` | Modal agentic chat endpoint URL |
| `AMA_API_KEY` | API key for Modal endpoint auth |

All sensitive keys are **server-side only** (no `NEXT_PUBLIC_` prefix) and never reach the browser.

## Backend

The AI backend runs on [Modal](https://modal.com) with a fine-tuned Qwen3.5-9B model on an L4 GPU. See [`/modal`](../modal/) for the serving code.
