'use client';

import ReactMarkdown from 'react-markdown';
import { ThumbsUp, ThumbsDown, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import ToolsUsed from './ToolsUsed';
import DocumentSheet from './DocumentSheet';
import { cn, formatTime } from '@/lib/utils';
import type { Message as MessageType } from '@/store/useStore';

interface MessageProps {
  message: MessageType;
  chatId: string;
  isLast: boolean;
  onReact: (reaction: 'up' | 'down' | null) => void;
  onDelete: () => void;
  onRegenerate?: () => void;
}

export default function Message({
  message, chatId, isLast, onReact, onDelete, onRegenerate
}: MessageProps) {
  const isAssistant = message.role === 'assistant';

  return (
    <div
      className={cn(
        'flex w-full animate-fade-in-up mb-4 px-4',
        isAssistant ? 'justify-start' : 'justify-end'
      )}
    >
      <div className={cn('max-w-[80%] space-y-1', isAssistant ? 'items-start' : 'items-end')}>
        {/* Bubble */}
        <div
          className={cn(
            'rounded-2xl px-4 py-3 text-sm',
            isAssistant
              ? 'bg-card text-card-foreground rounded-tl-sm'
              : 'bg-primary text-primary-foreground rounded-tr-sm'
          )}
        >
          {isAssistant ? (
            <div className="prose prose-sm dark:prose-invert max-w-none text-card-foreground [&_p]:my-1 [&_ul]:my-1 [&_ol]:my-1 [&_li]:my-0.5 [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_code]:font-mono [&_pre]:bg-muted [&_pre]:rounded-lg [&_pre]:p-3 [&_pre]:overflow-x-auto [&_a]:text-primary [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:border-primary [&_blockquote]:pl-3 [&_blockquote]:italic">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          ) : (
            <p className="whitespace-pre-wrap">{message.content}</p>
          )}
        </div>

        {/* Document viewer (when create_file was used) */}
        {isAssistant && message.tool_results?.create_file && (
          <DocumentSheet
            filename={message.tool_results.create_file.filename || 'document.md'}
            content={message.tool_results.create_file.content || message.content}
          />
        )}

        {/* Tools Used (AI only) — only show user-facing tools */}
        {isAssistant && message.tools_used && message.tools_used.filter(t => ['web_search', 'web_fetch', 'image_search', 'create_file', 'list_files', 'view_file'].includes(t)).length > 0 && (
          <ToolsUsed tools={message.tools_used.filter(t => ['web_search', 'web_fetch', 'image_search', 'create_file', 'list_files', 'view_file'].includes(t))} toolResults={message.tool_results} />
        )}

        {/* Timestamp + Actions row */}
        <div className={cn(
          'flex items-center gap-2 px-1',
          isAssistant ? 'justify-start' : 'justify-end'
        )}>
          <span className="text-[10px] text-muted-foreground">
            {formatTime(message.timestamp)}
          </span>

          {/* AI-only actions: like, dislike, retry */}
          {isAssistant && (
            <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="icon-xs"
                className={cn(
                  message.reaction === 'up' && 'text-primary bg-primary/10'
                )}
                onClick={() => onReact(message.reaction === 'up' ? null : 'up')}
              >
                <ThumbsUp size={12} />
              </Button>
              <Button
                variant="ghost"
                size="icon-xs"
                className={cn(
                  message.reaction === 'down' && 'text-destructive bg-destructive/10'
                )}
                onClick={() => onReact(message.reaction === 'down' ? null : 'down')}
              >
                <ThumbsDown size={12} />
              </Button>
              {isLast && onRegenerate && (
                <Button variant="ghost" size="icon-xs" onClick={onRegenerate}>
                  <RefreshCw size={12} />
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
