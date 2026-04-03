import { motion } from 'framer-motion';

interface KpiCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  color?: string;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  label,
  value,
  subtitle,
  icon: Icon,
  color = 'text-accent',
}) => (
  <motion.div
    initial={{ opacity: 0, y: 16 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.4 }}
    className="bg-surface-raised border border-border rounded-xl p-5"
  >
    <div className="flex items-start justify-between mb-3">
      <span className="text-xs font-bold text-text-muted uppercase tracking-widest">
        {label}
      </span>
      <div
        className={`w-8 h-8 rounded-lg bg-surface-overlay flex items-center justify-center ${color}`}
      >
        <Icon size={16} />
      </div>
    </div>
    <div className="text-3xl font-extrabold text-text font-heading">{value}</div>
    {subtitle && (
      <div className="text-xs text-text-muted mt-1">{subtitle}</div>
    )}
  </motion.div>
);
