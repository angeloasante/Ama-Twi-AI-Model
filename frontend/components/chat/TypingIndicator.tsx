'use client';

export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-3 px-4 py-3 animate-fade-in-up justify-start">
      <div className="flex items-center gap-1 rounded-2xl bg-card px-4 py-3">
        <div className="typing-dot h-2 w-2 rounded-full bg-muted-foreground" />
        <div className="typing-dot h-2 w-2 rounded-full bg-muted-foreground" />
        <div className="typing-dot h-2 w-2 rounded-full bg-muted-foreground" />
      </div>
    </div>
  );
}
