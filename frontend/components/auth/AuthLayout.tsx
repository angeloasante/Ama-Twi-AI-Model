'use client';

interface AuthLayoutProps {
  children: React.ReactNode;
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="min-h-svh flex">
      {/* Left panel — branding */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-primary/5 flex-col justify-between p-12 overflow-hidden">
        {/* Decorative circles */}
        <div className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute -bottom-32 -right-32 w-[500px] h-[500px] rounded-full bg-primary/8 blur-3xl" />
        <div className="absolute top-1/2 left-1/3 w-64 h-64 rounded-full bg-primary/5 blur-2xl" />

        {/* Top — logo */}
        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-xl">
              🇬🇭
            </div>
            <span className="text-xl font-bold text-foreground tracking-tight">Ama</span>
          </div>
        </div>

        {/* Center — tagline */}
        <div className="relative z-10 space-y-6">
          <h1 className="text-4xl font-bold text-foreground leading-tight">
            Your bilingual<br />
            AI companion for<br />
            <span className="text-primary">Twi & English</span>
          </h1>
          <p className="text-muted-foreground text-lg max-w-md leading-relaxed">
            Learn Twi, explore Akan culture, and get intelligent answers — all in one place.
          </p>
          <div className="flex gap-6 pt-4">
            <div className="space-y-1">
              <p className="text-2xl font-bold text-foreground">10K+</p>
              <p className="text-sm text-muted-foreground">Twi phrases</p>
            </div>
            <div className="w-px bg-border" />
            <div className="space-y-1">
              <p className="text-2xl font-bold text-foreground">Bilingual</p>
              <p className="text-sm text-muted-foreground">Twi & English</p>
            </div>
            <div className="w-px bg-border" />
            <div className="space-y-1">
              <p className="text-2xl font-bold text-foreground">AI-Powered</p>
              <p className="text-sm text-muted-foreground">Smart responses</p>
            </div>
          </div>
        </div>

        {/* Bottom — testimonial */}
        <div className="relative z-10">
          <blockquote className="border-l-2 border-primary/40 pl-4">
            <p className="text-sm text-muted-foreground italic">
              &quot;Ama helped me reconnect with my Akan heritage. The Twi translations are incredibly natural.&quot;
            </p>
            <footer className="mt-2 text-sm font-medium text-foreground">
              — Kwame A., Accra
            </footer>
          </blockquote>
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6 md:p-12">
        <div className="w-full max-w-md">
          {children}
        </div>
      </div>
    </div>
  );
}
