import React from 'react';
import { Gauge, Flame, PieChart, Users } from 'lucide-react';

export default function SentimentGauge({ sentimentData }) {
  if (!sentimentData) return null;

  const fngScore = sentimentData.fear_and_greed_score || 50;

  return (
    <div className="bg-[#121824] border border-slate-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Gauge className="w-4 h-4 text-purple-400" />
          <h3 className="font-semibold text-sm text-slate-100">Capa 3: Sentimiento, Opciones & COT</h3>
        </div>
        <span className="text-xs bg-purple-500/10 text-purple-400 border border-purple-500/30 px-2 py-0.5 rounded-full font-bold">
          {sentimentData.fear_and_greed_sentiment} ({fngScore}/100)
        </span>
      </div>

      {/* Progress bar for Fear & Greed */}
      <div className="mb-4">
        <div className="flex justify-between text-[10px] text-slate-400 mb-1">
          <span>Miedo Extremo (0)</span>
          <span>Neutral (50)</span>
          <span>Codicia Extrema (100)</span>
        </div>
        <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden flex">
          <div
            className={`h-full transition-all duration-500 rounded-full ${
              fngScore < 30 ? 'bg-rose-500' : fngScore > 70 ? 'bg-emerald-500' : 'bg-amber-500'
            }`}
            style={{ width: `${fngScore}%` }}
          />
        </div>
      </div>

      {/* Factor cards */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/40">
          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] uppercase font-medium mb-1">
            <Flame className="w-3 h-3 text-amber-400" />
            <span>Índice VIX</span>
          </div>
          <span className="text-sm font-bold text-white font-mono block">{sentimentData.vix}</span>
          <span className="text-[10px] text-slate-400">{sentimentData.vix_regime}</span>
        </div>

        <div className="bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/40">
          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] uppercase font-medium mb-1">
            <PieChart className="w-3 h-3 text-blue-400" />
            <span>Put/Call CBOE</span>
          </div>
          <span className="text-sm font-bold text-white font-mono block">{sentimentData.cboe_put_call_ratio}</span>
          <span className="text-[10px] text-slate-400 truncate block">{sentimentData.put_call_sentiment}</span>
        </div>

        <div className="bg-slate-900/40 p-2.5 rounded-lg border border-slate-800/40">
          <div className="flex items-center gap-1.5 text-slate-400 text-[10px] uppercase font-medium mb-1">
            <Users className="w-3 h-3 text-emerald-400" />
            <span>Posición COT (CFTC)</span>
          </div>
          <span className="text-xs font-bold text-emerald-400 truncate block mt-0.5">
            {sentimentData.institutional_sentiment}
          </span>
          <span className="text-[10px] text-slate-400">Smart Money</span>
        </div>
      </div>
    </div>
  );
}
