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
      <PolarGrid stroke="#1E293B" />
      <PolarAngleAxis
        dataKey="pillar"
        tick={{ fill: '#94A3B8', fontSize: 11, fontWeight: 600 }}
      />
      <PolarRadiusAxis
        angle={90}
        domain={[0, 100]}
        tick={false}
        axisLine={false}
      />
      <Tooltip
        contentStyle={{
          backgroundColor: '#151B28',
          border: '1px solid #1E293B',
          borderRadius: '8px',
          color: '#F1F5F9',
          fontSize: '12px',
          fontWeight: 600,
        }}
        formatter={(value) => [`${value}/100`, 'Score']}
      />
      <Radar
        name="Score"
        dataKey="score"
        stroke="#2820FF"
        fill="#2820FF"
        fillOpacity={0.2}
        strokeWidth={2}
      />
    </RadarChart>
  </ResponsiveContainer>
);
