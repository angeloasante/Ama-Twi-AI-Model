'use client';

import { useState } from 'react';
import { cn, TOOL_LABELS } from '@/lib/utils';
import { ChevronDown, ExternalLink, Search, Globe, Clock, Image, FileText, FolderOpen, BookOpen, Wrench } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ToolsUsedProps {
  tools: string[];
  toolResults?: Record<string, any>;
}

const TOOL_ICONS: Record<string, React.ElementType> = {
  web_search: Search,
  web_fetch: Globe,
  get_current_time: Clock,
  image_search: Image,
  create_file: FileText,
  view_file: FileText,
  list_files: FolderOpen,
  search_knowledge_base: BookOpen,
};

// Internal tools that shouldn't be shown to the user
const HIDDEN_TOOLS = ['search_knowledge_base', 'knowledge_base', 'web_fetch', 'create_file'];

export default function ToolsUsed({ tools, toolResults }: ToolsUsedProps) {
  const [expanded, setExpanded] = useState(false);

  // Filter out internal tools
  const visibleTools = tools.filter(t => !HIDDEN_TOOLS.includes(t));
  const visibleResults = toolResults
    ? Object.fromEntries(Object.entries(toolResults).filter(([k]) => !HIDDEN_TOOLS.includes(k)))
    : undefined;

  if (!visibleTools || visibleTools.length === 0) return null;

  return (
    <div className="mt-2 animate-fade-in-up">
      {/* Clickable tools summary bar */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 rounded-lg bg-secondary/60 hover:bg-secondary px-3 py-1.5 transition-colors cursor-pointer w-fit group"
      >
        <div className="flex items-center gap-1.5">
          {visibleTools.map(tool => {
            const Icon = TOOL_ICONS[tool] || Wrench;
            const info = TOOL_LABELS[tool] || { label: tool, icon: '🔧' };
            return (
              <span
                key={tool}
                className="inline-flex items-center gap-1 text-xs text-secondary-foreground"
              >
                <Icon size={12} className="text-primary" />
                <span className="font-medium">{info.label}</span>
              </span>
            );
          })}
        </div>
        <ChevronDown
          size={14}
          className={cn(
            'text-muted-foreground transition-transform duration-200',
            expanded && 'rotate-180'
          )}
        />
      </button>

      {/* Collapsible results panel */}
      <div
        className={cn(
          'grid transition-all duration-300 ease-in-out',
          expanded ? 'grid-rows-[1fr] opacity-100 mt-2' : 'grid-rows-[0fr] opacity-0'
        )}
      >
        <div className="overflow-hidden">
          <div className="space-y-2">
            {visibleResults && Object.entries(visibleResults).map(([key, value]) => (
              <ToolResultPanel key={key} toolName={key} result={value} />
            ))}
            {/* If toolResults is empty/null but tools exist, show a minimal panel */}
            {(!visibleResults || Object.keys(visibleResults).length === 0) && (
              <div className="rounded-lg border border-border bg-muted/40 px-3 py-2">
                <p className="text-xs text-muted-foreground">
                  {visibleTools.length === 1 ? 'Tool' : 'Tools'} used to generate this response.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function ToolResultPanel({ toolName, result }: { toolName: string; result: any }) {
  const info = TOOL_LABELS[toolName] || { label: toolName, icon: '🔧' };
  const Icon = TOOL_ICONS[toolName] || Wrench;

  let content = '';
  let sources: { title: string; url: string }[] = [];

  if (typeof result === 'string') {
    content = result;
  } else if (result?.results) {
    content = typeof result.results === 'string'
      ? result.results
      : JSON.stringify(result.results, null, 2);
  } else if (result) {
    content = JSON.stringify(result, null, 2);
  }

  // Extract URLs from content
  const urlRegex = /(?:Source:\s*)?(https?:\/\/[^\s"'<>]+)/gi;
  const urlMatches = [...content.matchAll(urlRegex)];
  if (urlMatches.length > 0) {
    const seen = new Set<string>();
    sources = urlMatches
      .map(m => {
        const url = m[1];
        if (seen.has(url)) return null;
        seen.add(url);
        try {
          return { title: new URL(url).hostname.replace('www.', ''), url };
        } catch {
          return null;
        }
      })
      .filter(Boolean) as { title: string; url: string }[];
  }

  return (
    <div className="rounded-lg border border-border bg-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border bg-muted/50">
        <Icon size={14} className="text-primary flex-shrink-0" />
        <span className="text-xs font-medium text-foreground">{info.label}</span>
        {result?.query && (
          <span className="text-xs text-muted-foreground ml-auto truncate max-w-48 italic">
            &quot;{result.query}&quot;
          </span>
        )}
      </div>

      {/* Content */}
      <div className="px-3 py-2 max-h-48 overflow-y-auto">
        <pre className="text-xs text-muted-foreground whitespace-pre-wrap break-words font-sans leading-relaxed">
          {content.slice(0, 1000)}{content.length > 1000 ? '…' : ''}
        </pre>
      </div>

      {/* Source links */}
      {sources.length > 0 && (
        <div className="px-3 py-2 border-t border-border bg-muted/30">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5 font-medium">
            Sources
          </p>
          <div className="flex flex-wrap gap-2">
            {sources.slice(0, 5).map((src, i) => (
              <a
                key={i}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-primary hover:text-primary/80 hover:underline bg-primary/5 rounded-md px-2 py-0.5 transition-colors"
              >
                <ExternalLink size={10} className="flex-shrink-0" />
                {src.title}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
