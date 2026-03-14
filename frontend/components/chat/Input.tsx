'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Mic, MicOff, Square, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useVoice } from '@/hooks/useVoice';
import { cn } from '@/lib/utils';

interface InputProps {
  onSend: (message: string) => void;
  onStop: () => void;
  isLoading: boolean;
  disabled?: boolean;
  embedded?: boolean;
}

export default function Input({ onSend, onStop, isLoading, disabled, embedded }: InputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleVoiceResult = useCallback((text: string) => {
    setValue(prev => (prev ? prev + ' ' + text : text));
  }, []);

  const { isListening, isSupported, toggleListening } = useVoice(handleVoiceResult);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    }
  }, [value]);

  // Focus on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSend = () => {
    if (!value.trim() || isLoading || disabled) return;
    onSend(value.trim());
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={cn(
      'px-4 pb-3 pt-2',
    )}>
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2 rounded-2xl bg-card/80 border border-border/50 px-3 py-2 shadow-sm focus-within:ring-1 focus-within:ring-ring/30 transition-all">
          {/* Plus / attach button */}
          <Button variant="ghost" size="icon-sm" className="flex-shrink-0 mb-0.5 text-muted-foreground hover:text-foreground">
            <Plus size={18} />
          </Button>

          {/* Textarea */}
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isListening ? 'Listening...' : 'Ask anything ...'}
            rows={1}
            disabled={disabled}
            className="flex-1 border-0 bg-transparent shadow-none resize-none focus-visible:ring-0 min-h-[36px] max-h-[200px] py-1.5 px-0 text-sm placeholder:text-muted-foreground/60"
          />

          {/* Voice button */}
          {isSupported && (
            <Button
              variant="ghost"
              size="icon-sm"
              className={cn(
                'flex-shrink-0 mb-0.5 text-muted-foreground hover:text-foreground',
                isListening && 'text-destructive bg-destructive/10 animate-pulse'
              )}
              onClick={toggleListening}
            >
              {isListening ? <MicOff size={18} /> : <Mic size={18} />}
            </Button>
          )}

          {/* Send / Stop */}
          {isLoading ? (
            <Button
              variant="destructive"
              size="icon-sm"
              className="flex-shrink-0 mb-0.5 rounded-full h-8 w-8"
              onClick={onStop}
            >
              <Square size={14} fill="currentColor" />
            </Button>
          ) : (
            <Button
              variant="default"
              size="icon-sm"
              className="flex-shrink-0 mb-0.5 rounded-full h-8 w-8"
              onClick={handleSend}
              disabled={!value.trim() || disabled}
            >
              <Send size={16} />
            </Button>
          )}
        </div>
        <p className="text-[11px] text-muted-foreground/50 text-center mt-1.5">Ama can make mistakes. Please double-check responses.</p>
      </div>
    </div>
  );
}
