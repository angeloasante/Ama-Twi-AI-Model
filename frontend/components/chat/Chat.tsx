'use client';

import { useRef, useEffect } from 'react';
import { useStore } from '@/store/useStore';
import { useChat } from '@/hooks/useChat';
import Message from './Message';
import Input from './Input';
import TypingIndicator from './TypingIndicator';
import EmptyState from '@/components/layout/EmptyState';

export default function Chat() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { messages, isLoading, sendMessage, regenerate, stopGeneration, activeChat } = useChat();
  const { updateMessageReaction, deleteMessage, activeChatId } = useStore();

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages.length, isLoading]);

  const handlePromptClick = (prompt: string) => {
    sendMessage(prompt);
  };

  if (messages.length === 0) {
    return (
      <div className="flex flex-col flex-1 min-h-0">
        <EmptyState
          onSendPrompt={handlePromptClick}
          onSend={sendMessage}
          onStop={stopGeneration}
          isLoading={isLoading}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto py-4">
          {messages.map((msg, i) => (
            <div key={msg.id} className="group">
              <Message
                message={msg}
                chatId={activeChatId!}
                isLast={i === messages.length - 1}
                onReact={(reaction) =>
                  updateMessageReaction(activeChatId!, msg.id, reaction)
                }
                onDelete={() => deleteMessage(activeChatId!, msg.id)}
                onRegenerate={regenerate}
              />
            </div>
          ))}
          {isLoading && <TypingIndicator />}
        </div>
      </div>

      {/* Input pinned to bottom */}
      <div className="shrink-0 sticky bottom-0 bg-background">
        <Input
          onSend={sendMessage}
          onStop={stopGeneration}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}
