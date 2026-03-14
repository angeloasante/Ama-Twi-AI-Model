'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { useStore } from '@/store/useStore';

const STEPS = [
  {
    emoji: '🇬🇭',
    title: 'Akwaaba! Welcome!',
    subtitle: 'Meet Ama — your bilingual Twi-English AI assistant',
    description: 'Ama speaks both English and Twi, helping you learn, translate, and explore Ghanaian culture.',
  },
  {
    emoji: '🧠',
    title: 'Smart & Connected',
    subtitle: 'Real-time info at your fingertips',
    description: 'Ama can search the web, tell you the time, find images, and access a knowledge base — all in your conversation.',
  },
  {
    emoji: '🎙️',
    title: 'Talk to Ama',
    subtitle: 'Voice input supported',
    description: 'Press the microphone button to speak your question. Ama understands both English and Twi speech.',
  },
];

export default function Onboarding() {
  const [step, setStep] = useState(0);
  const { onboardingSeen, completeOnboarding } = useStore();

  if (onboardingSeen) return null;

  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md mx-4 rounded-2xl bg-[var(--color-background)] border border-[var(--color-border)] shadow-2xl overflow-hidden"
      >
        {/* Progress dots */}
        <div className="flex justify-center gap-2 pt-6">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                i === step ? 'w-8 bg-[var(--color-primary)]' : 'w-1.5 bg-[var(--color-border)]'
              }`}
            />
          ))}
        </div>

        {/* Content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2 }}
            className="px-8 py-8 text-center"
          >
            <div className="text-6xl mb-4">{current.emoji}</div>
            <h2 className="text-2xl font-bold text-[var(--color-foreground)] mb-1">
              {current.title}
            </h2>
            <p className="text-sm font-medium text-[var(--color-primary)] mb-3">
              {current.subtitle}
            </p>
            <p className="text-sm text-[var(--color-muted)] leading-relaxed">
              {current.description}
            </p>
          </motion.div>
        </AnimatePresence>

        {/* Actions */}
        <div className="flex items-center justify-between px-8 pb-6">
          <button
            onClick={completeOnboarding}
            className="text-xs text-[var(--color-muted)] hover:text-[var(--color-foreground)] transition-colors"
          >
            Skip
          </button>
          <div className="flex gap-2">
            {step > 0 && (
              <Button variant="outline" size="sm" onClick={() => setStep(s => s - 1)}>
                Back
              </Button>
            )}
            {isLast ? (
              <Button variant="default" size="sm" onClick={completeOnboarding}>
                Get Started
              </Button>
            ) : (
              <Button variant="default" size="sm" onClick={() => setStep(s => s + 1)}>
                Next
              </Button>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
