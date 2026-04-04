import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

interface PillarScore {
  pillar: string;
  score: number;
  fullMark: number;
}

interface PillarRadarChartProps {
  data: PillarScore[];
}

export const PillarRadarChart: React.FC<PillarRadarChartProps> = ({ data }) => (
  <ResponsiveContainer width="100%" height={320}>
    <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
      <PolarGrid stroke="#E2E8F0" />
      <PolarAngleAxis
        dataKey="pillar"
        tick={{ fill: '#475569', fontSize: 11, fontWeight: 600 }}
      />
      <PolarRadiusAxis
        angle={90}
        domain={[0, 100]}
        tick={false}
        axisLine={false}
      />
      <Tooltip
        contentStyle={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '8px',
          color: '#0F172A',
          fontSize: '12px',
          fontWeight: 600,
          boxShadow: '0 4px 6px -1px rgba(0,0,0,0.07)',
        }}
        formatter={(value) => [`${value}/100`, 'Score']}
      />
      <Radar
        name="Score"
        dataKey="score"
        stroke="#2820FF"
        fill="#2820FF"
        fillOpacity={0.15}
        strokeWidth={2}
      />
    </RadarChart>
  </ResponsiveContainer>
);
