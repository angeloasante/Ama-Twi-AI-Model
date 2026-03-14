'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { FileText, Download, Copy, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';

interface DocumentSheetProps {
  filename: string;
  content: string;
  trigger?: React.ReactNode;
}

export default function DocumentSheet({ filename, content, trigger }: DocumentSheetProps) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Clean display name
  const displayName = filename
    .replace(/\.md$/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());

  return (
    <>
      {/* Inline document card trigger */}
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-3 mt-3 w-full rounded-xl border border-border bg-card hover:bg-accent/50 px-4 py-3 transition-colors cursor-pointer group text-left"
      >
        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10 text-primary shrink-0">
          <FileText size={20} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground truncate">{displayName}</p>
          <p className="text-xs text-muted-foreground">{filename} · {(content.length / 1024).toFixed(1)} KB</p>
        </div>
        <span className="text-xs text-primary opacity-0 group-hover:opacity-100 transition-opacity font-medium">
          Open →
        </span>
      </button>

      {/* Sheet overlay with document content */}
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full sm:max-w-xl md:max-w-2xl p-0 flex flex-col" showCloseButton={false}>
          {/* Header */}
          <SheetHeader className="px-6 pt-5 pb-4 border-b border-border shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3 min-w-0">
                <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-primary/10 text-primary shrink-0">
                  <FileText size={18} />
                </div>
                <div className="min-w-0">
                  <SheetTitle className="text-base truncate">{displayName}</SheetTitle>
                  <p className="text-xs text-muted-foreground mt-0.5">{filename}</p>
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={handleCopy}
                  title="Copy content"
                >
                  {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={handleDownload}
                  title="Download"
                >
                  <Download size={14} />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setOpen(false)}
                  title="Close"
                >
                  <X size={14} />
                </Button>
              </div>
            </div>
          </SheetHeader>

          {/* Document content with markdown rendering */}
          <div className="flex-1 overflow-y-auto px-6 py-5">
            <div className="prose prose-sm dark:prose-invert max-w-none text-foreground [&_h1]:text-xl [&_h1]:font-bold [&_h1]:mb-3 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mb-2 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:mb-2 [&_p]:my-2 [&_p]:leading-relaxed [&_ul]:my-2 [&_ol]:my-2 [&_li]:my-1 [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_pre]:bg-muted [&_pre]:rounded-lg [&_pre]:p-4 [&_pre]:overflow-x-auto [&_blockquote]:border-l-3 [&_blockquote]:border-primary [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:text-muted-foreground [&_strong]:text-foreground [&_hr]:my-4 [&_hr]:border-border">
              <ReactMarkdown>{content}</ReactMarkdown>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
