'use client';

import { BookOpen, Globe, Sparkles } from 'lucide-react';
import Input from '@/components/chat/Input';

interface EmptyStateProps {
  onSendPrompt: (text: string) => void;
  onSend: (message: string) => void;
  onStop: () => void;
  isLoading: boolean;
}

const FEATURE_CARDS = [
  {
    icon: BookOpen,
    title: 'Twi Learning',
    example: '"Teach me basic Twi greetings and how to introduce myself"',
    prompt: 'Teach me basic Twi greetings and how to introduce myself',
  },
  {
    icon: Sparkles,
    title: 'Cultural Guide',
    example: '"Tell me about Ghanaian naming traditions and Akan day names"',
    prompt: 'Tell me about Ghanaian naming traditions and Akan day names',
  },
  {
    icon: Globe,
    title: 'Translation',
    example: '"How do you say \'I love you\' in Twi?"',
    prompt: 'How do you say "I love you" in Twi?',
  },
];

export default function EmptyState({ onSendPrompt, onSend, onStop, isLoading }: EmptyStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 animate-fade-in-up min-h-full">
      {/* Logo + greeting */}
      <div className="mb-8 flex flex-col items-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 text-3xl mb-6">
          🇬🇭
        </div>
        <h2 className="text-2xl md:text-3xl font-semibold text-foreground/80 text-center">
          Good to See You!
        </h2>
        <h1 className="text-2xl md:text-3xl font-bold text-foreground text-center mt-1">
          How Can I Help Today?
        </h1>
        <p className="text-muted-foreground text-sm mt-3 text-center">
          Ama is here to support your ideas, your pace, and your learning.
        </p>
      </div>

      {/* Embedded input */}
      <div className="w-full max-w-2xl">
        <Input
          onSend={onSend}
          onStop={onStop}
          isLoading={isLoading}
          embedded
        />
      </div>

      {/* Feature/suggestion cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-10 max-w-3xl w-full">
        {FEATURE_CARDS.map((card) => (
          <button
            key={card.title}
            onClick={() => onSendPrompt(card.prompt)}
            className="flex flex-col items-center gap-3 rounded-xl border border-border bg-card/60 p-6 text-center hover:bg-accent hover:border-primary/30 transition-all cursor-pointer group"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary group-hover:bg-primary/20 transition-colors">
              <card.icon size={20} />
            </div>
            <span className="text-sm font-medium text-foreground">{card.title}</span>
            <span className="text-xs text-muted-foreground leading-relaxed">
              {card.example}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
