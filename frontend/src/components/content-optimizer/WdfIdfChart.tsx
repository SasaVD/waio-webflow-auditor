import { useMemo } from 'react';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface ChartDataPoint {
  term: string;
  target: number;
  comp_max: number;
  comp_avg: number;
  classification: string;
}

interface WdfIdfChartProps {
  data: ChartDataPoint[];
}

const CLASSIFICATION_COLORS: Record<string, string> = {
  core: '#22C55E',
  semantic: '#3B82F6',
  auxiliary: '#94A3B8',
  filler: '#EF4444',
};

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;

  const point = payload[0]?.payload as ChartDataPoint | undefined;
  const classification = point?.classification || 'auxiliary';
  const classColor = CLASSIFICATION_COLORS[classification] || '#94A3B8';

  return (
    <div className="bg-surface-raised border border-border rounded-lg p-3 shadow-card text-xs">
      <div className="flex items-center gap-2 mb-2">
        <span
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: classColor }}
        />
        <span className="font-bold text-text">{label}</span>
        <span
          className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded"
          style={{ color: classColor, backgroundColor: classColor + '20' }}
        >
          {classification}
        </span>
      </div>
      {payload.map((entry: any) => (
        <div key={entry.name} className="flex justify-between gap-4 text-text-secondary">
          <span>{entry.name}</span>
          <span className="font-mono font-semibold" style={{ color: entry.color }}>
            {entry.value?.toFixed(4)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function WdfIdfChart({ data }: WdfIdfChartProps) {
  const chartData = useMemo(() => {
    return data.map((d) => ({
      ...d,
      // Truncate long terms for x-axis
      shortTerm: d.term.length > 18 ? d.term.slice(0, 16) + '\u2026' : d.term,
    }));
  }, [data]);

  if (!chartData.length) {
    return (
      <div className="h-[400px] flex items-center justify-center text-text-muted text-sm">
        No chart data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={420}>
      <ComposedChart data={chartData} margin={{ top: 10, right: 20, bottom: 120, left: 10 }}>
        <XAxis
          dataKey="shortTerm"
          angle={-45}
          textAnchor="end"
          height={120}
          tick={{ fontSize: 10, fill: '#94A3B8' }}
          interval={0}
        />
        <YAxis
          tick={{ fontSize: 10, fill: '#64748B' }}
          label={{
            value: 'WDF*IDF Score',
            angle: -90,
            position: 'insideLeft',
            style: { fontSize: 11, fill: '#64748B' },
          }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          verticalAlign="top"
          height={36}
          wrapperStyle={{ fontSize: 11, color: '#94A3B8' }}
        />
        <Area
          type="monotone"
          dataKey="comp_max"
          fill="#fecaca"
          fillOpacity={0.3}
          stroke="#ef4444"
          strokeWidth={1}
          name="Competitor Maximum"
        />
        <Area
          type="monotone"
          dataKey="comp_avg"
          fill="#fef08a"
          fillOpacity={0.3}
          stroke="#eab308"
          strokeWidth={1}
          name="Competitor Average"
        />
        {/* Render last so line draws on top of the Area layers */}
        <Line
          type="monotone"
          dataKey="target"
          stroke="#1f2937"
          strokeWidth={3}
          dot={{ r: 4, fill: '#1f2937', stroke: '#0f172a', strokeWidth: 1.5 }}
          activeDot={{ r: 6, fill: '#2820FF', stroke: '#fff', strokeWidth: 2 }}
          name="Your Page"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
