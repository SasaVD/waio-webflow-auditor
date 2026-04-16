import { TrendingUp, Target } from 'lucide-react';
import { motion } from 'framer-motion';

interface ZeroMentionsCardProps {
  brandName: string;
  industryLeaf?: string;
}

export function ZeroMentionsCard({ brandName, industryLeaf }: ZeroMentionsCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface-raised border border-border rounded-xl p-6"
    >
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
          <Target size={20} className="text-amber-400" />
        </div>
        <div className="space-y-3">
          <div>
            <h3 className="text-sm font-bold text-text font-heading">
              AI Visibility Opportunity
            </h3>
            <p className="text-sm text-text-secondary mt-1 leading-relaxed">
              <strong className="text-text">{brandName}</strong> is not yet appearing in
              AI-generated responses for{' '}
              {industryLeaf ? (
                <>{industryLeaf.toLowerCase()} category searches</>
              ) : (
                <>category searches</>
              )}
              . This represents an untapped channel — competitors who establish AI
              visibility now build compounding advantage.
            </p>
          </div>
          <div className="flex items-start gap-3 p-3 bg-accent/5 border border-accent/10 rounded-lg">
            <TrendingUp size={14} className="text-accent mt-0.5 flex-shrink-0" />
            <p className="text-xs text-text-muted leading-relaxed">
              The pre-indexed AI mention database (Google AI Overview + ChatGPT)
              currently shows zero mentions for your brand. This means no AI search
              queries are returning your content in their responses. Improving content
              structure, authority signals, and topical coverage can change this.
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
