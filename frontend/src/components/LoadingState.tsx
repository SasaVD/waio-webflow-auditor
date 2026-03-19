import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, Loader2 } from 'lucide-react';

const steps = [
  { label: 'Fetching page content', duration: 2500 },
  { label: 'Launching browser engine', duration: 2500 },
  { label: 'Analyzing semantic HTML structure', duration: 3000 },
  { label: 'Extracting JSON-LD & Microdata', duration: 2500 },
  { label: 'Analyzing AEO content structure', duration: 3000 },
  { label: 'Scanning CSS frameworks & JS bloat', duration: 2500 },
  { label: 'Running WCAG accessibility checks', duration: 3500 },
  { label: 'Checking RAG & chunking readiness', duration: 2500 },
  { label: 'Verifying agentic protocols (llms.txt, robots.txt)', duration: 2500 },
  { label: 'Detecting data conflicts & integrity issues', duration: 2500 },
  { label: 'Compiling audit report', duration: 2000 },
];

interface LoadingStateProps {
  url: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({ url }) => {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>;
    const advance = (step: number) => {
      if (step < steps.length - 1) {
        timeout = setTimeout(() => {
          setCurrentStep(step + 1);
          advance(step + 1);
        }, steps[step].duration);
      }
    };
    advance(0);
    return () => clearTimeout(timeout);
  }, []);

  const progress = Math.min(((currentStep + 1) / steps.length) * 100, 95);

  return (
    <div className="max-w-2xl mx-auto px-6 py-24">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-primary/5 border border-primary/10 flex items-center justify-center">
          <Loader2 size={28} className="text-primary animate-spin" />
        </div>
        <h2 className="text-2xl font-bold text-text-primary mb-2">Analyzing your site</h2>
        <p className="text-sm text-text-muted font-medium truncate max-w-md mx-auto">{url}</p>
      </motion.div>

      {/* Progress bar */}
      <div className="mb-10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-text-secondary">Progress</span>
          <span className="text-xs font-bold text-primary">{Math.round(progress)}%</span>
        </div>
        <div className="h-1.5 bg-surface-secondary rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-primary rounded-full"
            initial={{ width: '0%' }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-1">
        <AnimatePresence>
          {steps.map((step, i) => (
            <motion.div
              key={step.label}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors ${
                i === currentStep
                  ? 'bg-primary/5 border border-primary/10'
                  : i < currentStep
                  ? 'opacity-60'
                  : 'opacity-30'
              }`}
            >
              {i < currentStep ? (
                <CheckCircle2 size={16} className="text-accent flex-shrink-0" />
              ) : i === currentStep ? (
                <Loader2 size={16} className="text-primary animate-spin flex-shrink-0" />
              ) : (
                <div className="w-4 h-4 rounded-full border-2 border-gray-200 flex-shrink-0" />
              )}
              <span className={`text-sm font-medium ${
                i === currentStep ? 'text-text-primary' : 'text-text-secondary'
              }`}>
                {step.label}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <p className="text-center text-xs text-text-muted mt-8">
        This typically takes 15–30 seconds depending on site complexity.
      </p>
    </div>
  );
};
