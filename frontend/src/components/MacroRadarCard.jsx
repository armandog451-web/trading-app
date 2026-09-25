import React from 'react';
import { Globe, TrendingUp, TrendingDown, Minus, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function MacroRadarCard({ macroData }) {
  if (!macroData) return null;

  const bias = macroData.macro_bias || 'NEUTRAL';
  const isBull = bias === 'BULLISH';
  const isBear = bias === 'BEARISH';

  return (
    <div className="bg-[#121824] border border-slate-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Globe className="w-4 h-4 text-blue-400" />
          <h3 className="font-semibold text-sm text-slate-100">Capa 1: Macro & Política Monetaria</h3>
        </div>
        <span
          className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider flex items-center gap-1 border ${
            isBull
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : isBear
              ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
              : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
          }`}
        >
          {isBull ? <TrendingUp className="w-3 h-3" /> : isBear ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
          {bias}
        </span>
      </div>

      <p className="text-xs text-slate-400 mb-4 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60 leading-relaxed">
        {macroData.summary}
      </p>

      {/* Grid of Key Macro Variables */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-slate-900/40 p-2 rounded-lg border border-slate-800/40">
          <span className="text-[10px] text-slate-400 uppercase block font-medium">Bono Tesoro 10Y</span>
          <span className="text-sm font-bold text-slate-100 font-mono">{macroData.yield_10y}%</span>
        </div>

        <div className="bg-slate-900/40 p-2 rounded-lg border border-slate-800/40">
          <span className="text-[10px] text-slate-400 uppercase block font-medium">Bono Tesoro 2Y</span>
          <span className="text-sm font-bold text-slate-100 font-mono">{macroData.yield_2y}%</span>
        </div>

        <div className="bg-slate-900/40 p-2 rounded-lg border border-slate-800/40">
          <span className="text-[10px] text-slate-400 uppercase block font-medium">Curva 10Y - 2Y</span>
          <span className={`text-sm font-bold font-mono flex items-center gap-1 ${macroData.is_inverted ? 'text-rose-400' : 'text-emerald-400'}`}>
            {macroData.yield_spread_10y2y}%
            {macroData.is_inverted && <AlertTriangle className="w-3 h-3 text-rose-400" title="Curva invertida" />}
          </span>
        </div>

        <div className="bg-slate-900/40 p-2 rounded-lg border border-slate-800/40">
          <span className="text-[10px] text-slate-400 uppercase block font-medium">Índice Dólar (DXY)</span>
          <span className="text-sm font-bold text-slate-100 font-mono">{macroData.dxy_index}</span>
        </div>
      </div>
    </div>
  );
}
