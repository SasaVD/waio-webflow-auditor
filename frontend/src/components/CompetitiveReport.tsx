import React from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Trophy, Target, Zap, AlertTriangle, ExternalLink, BarChart3, Medal } from 'lucide-react';

interface CompetitiveReportProps {
  report: any;
  onNewAudit: () => void;
}

const scoreColor = (score: number): string => {
  if (score >= 90) return '#22C55E'; // green-500
  if (score >= 80) return '#84CC16'; // lime-500
  if (score >= 60) return '#EAB308'; // yellow-500
  if (score >= 40) return '#F97316'; // orange-500
  return '#EF4444'; // red-500
};

export const CompetitiveReport: React.FC<CompetitiveReportProps> = ({ report, onNewAudit }) => {
  const { primary_url, primary, rankings, pillar_averages, pillar_labels, advantages, weaknesses } = report;

  return (
    <div className="bg-surface-secondary min-h-screen pb-20">
      {/* Header */}
      <div className="bg-white border-b border-border sticky top-16 z-40 backdrop-blur-md bg-white/90">
        <div className="max-w-6xl mx-auto px-6 py-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <div className="bg-primary/10 text-primary text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
                Competitive Benchmark
              </div>
              <div className="text-text-muted text-xs">AI-Readiness Rank: #{primary.rank} of {rankings.length}</div>
            </div>
            <h1 className="text-xl font-bold text-text-primary truncate max-w-2xl flex items-center gap-2">
              {primary_url}
              <a href={primary_url} target="_blank" rel="noopener noreferrer" className="text-text-muted hover:text-primary transition-colors">
                <ExternalLink size={14} />
              </a>
            </h1>
          </div>
          <button
            onClick={onNewAudit}
            className="flex items-center gap-2 bg-white hover:bg-surface-secondary border border-border text-text-primary font-semibold px-4 py-2.5 rounded-xl transition-all text-sm self-start md:self-center"
          >
            <ArrowLeft size={16} /> New Audit
          </button>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-8">
        {/* Podium / Rankings */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
          <div className="lg:col-span-1 space-y-6">
            <h3 className="text-sm font-bold text-text-primary flex items-center gap-2">
              <Trophy size={16} className="text-accent" /> Leaderboard
            </h3>
            <div className="space-y-3">
              {rankings.map((r: any, idx: number) => (
                <motion.div
                  key={r.url}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  className={`relative p-4 rounded-2xl border transition-all ${
                    r.url === primary_url 
                      ? 'bg-primary/5 border-primary/20 shadow-sm ring-1 ring-primary/10' 
                      : 'bg-white border-border-light'
                  }`}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                        idx === 0 ? 'bg-accent text-white' : 
                        idx === 1 ? 'bg-gray-300 text-text-primary' :
                        idx === 2 ? 'bg-orange-200 text-text-primary' :
                        'bg-surface-secondary text-text-muted'
                      }`}>
                        {idx + 1}
                      </div>
                      <div className="truncate">
                        <div className={`text-sm font-bold truncate ${r.url === primary_url ? 'text-primary' : 'text-text-primary'}`}>
                          {r.url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                        </div>
                        {r.url === primary_url && <span className="text-[10px] font-bold text-primary uppercase tracking-tighter">Your Site</span>}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-black" style={{ color: scoreColor(r.overall_score) }}>{r.overall_score}</div>
                      <div className="text-[10px] text-text-muted font-bold uppercase tracking-widest">{r.overall_label}</div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* Advantages & Weaknesses */}
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white border border-border-light rounded-2xl p-6 shadow-sm">
              <h3 className="text-sm font-bold text-text-primary mb-6 flex items-center gap-2">
                <Zap size={16} className="text-green-500" /> Competitive Advantages
              </h3>
              {advantages.length > 0 ? (
                <div className="space-y-4">
                  {advantages.map((adv: any) => (
                    <div key={adv.key} className="flex flex-col gap-1">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold text-text-primary">{adv.pillar}</span>
                        <span className="text-xs font-bold text-green-600">+{adv.diff} pts vs avg</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-full bg-green-500 rounded-full" style={{ width: `${adv.score}%` }} />
                        </div>
                        <span className="text-[10px] font-bold text-text-muted w-6 text-right">{adv.score}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-text-muted text-xs italic">
                  No significant score advantages detected yet.
                </div>
              )}
            </div>

            <div className="bg-white border border-border-light rounded-2xl p-6 shadow-sm">
              <h3 className="text-sm font-bold text-text-primary mb-6 flex items-center gap-2 text-severity-critical">
                <AlertTriangle size={16} className="text-severity-critical" /> Critical Gaps
              </h3>
              {weaknesses.length > 0 ? (
                <div className="space-y-4">
                  {weaknesses.map((weak: any) => (
                    <div key={weak.key} className="flex flex-col gap-1">
                      <div className="flex justify-between items-center">
                        <span className="text-xs font-bold text-text-primary">{weak.pillar}</span>
                        <span className="text-xs font-bold text-severity-critical">{weak.diff} pts vs avg</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-full bg-severity-critical rounded-full" style={{ width: `${weak.score}%` }} />
                        </div>
                        <span className="text-[10px] font-bold text-text-muted w-6 text-right">{weak.score}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-text-muted text-xs italic">
                  No critical gaps relative to competitors!
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Pillar Comparison - Clustered Bar Chart */}
        <div className="bg-white border border-border-light rounded-3xl p-8 shadow-sm overflow-hidden">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-10">
            <div>
              <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
                <BarChart3 size={20} className="text-primary" /> Pillar Comparison
              </h3>
              <p className="text-xs text-text-muted mt-1 uppercase tracking-widest font-bold">Side-by-side performance audit</p>
            </div>
            
            <div className="flex flex-wrap gap-4">
              {rankings.map((r: any) => (
                <div key={r.url} className="flex items-center gap-2">
                  {/* use a consistent color or index based color but without the unused idx if possible or just use a fixed secondary color */}
                  <div className={`w-3 h-3 rounded-sm ${r.url === primary_url ? 'bg-primary' : `bg-gray-300`}`} />
                  <span className="text-[10px] font-bold text-text-muted truncate max-w-[120px]">
                    {r.url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-8">
            {Object.keys(pillar_labels).map((key) => {
              const label = pillar_labels[key];
              const average = pillar_averages[key];
              
              return (
                <div key={key} className="relative">
                  <div className="flex justify-between items-baseline mb-3">
                    <span className="text-xs font-black text-text-primary uppercase tracking-wider">{label}</span>
                    <span className="text-[10px] font-bold text-text-muted">AVG: {average}</span>
                  </div>
                  
                  <div className="flex flex-col gap-2">
                    {/* Clustered Bars */}
                    <div className="flex flex-col gap-1.5">
                      {rankings.map((r: any) => (
                        <div key={r.url} className="flex items-center gap-3">
                          <div className="flex-1 h-3 bg-gray-50 rounded-full overflow-hidden relative">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${r.pillar_scores[key]}%` }}
                              transition={{ duration: 1, delay: 0.2 }}
                              className={`h-full rounded-full ${
                                r.url === primary_url 
                                  ? 'bg-primary shadow-[0_0_8px_rgba(40,32,255,0.3)]' 
                                  : 'bg-gray-300'
                              }`}
                            />
                            {/* Average Line Overlay */}
                            <div 
                              className="absolute top-0 bottom-0 w-px bg-white/40 z-10" 
                              style={{ left: `${average}%` }}
                            />
                          </div>
                          <span className={`text-[10px] font-black w-6 text-right ${r.url === primary_url ? 'text-primary' : 'text-text-muted'}`}>
                            {r.pillar_scores[key]}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Next Steps Card */}
        <div className="mt-12 bg-primary text-white rounded-3xl p-8 shadow-[0_20px_40px_rgba(40,32,255,0.15)] relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-10">
            <Target size={120} />
          </div>
          <div className="relative z-10 max-w-2xl">
            <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
              <Medal size={24} /> AI-Readiness Strategy
            </h3>
            <p className="text-primary-lighter text-sm mb-6 leading-relaxed">
              To outperform {rankings[0].url === primary_url ? 'the market' : rankings[0].url}, prioritize fixing your 
              <span className="font-bold text-white px-1.5">{weaknesses.length > 0 ? weaknesses[0].pillar : 'remaining gaps'}</span>. 
              {primary.overall_score < 80 ? " Aim for an overall score above 85 to ensure reliable AI agent crawling and context extraction." : " You're in a strong position for the AI era."}
            </p>
            <div className="flex flex-wrap gap-4">
              <button 
                onClick={onNewAudit}
                className="bg-white text-primary font-bold px-6 py-3 rounded-xl text-sm hover:bg-primary-lighter transition-colors"
              >
                Create Improvement Roadmap
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
