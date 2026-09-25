import React from 'react';
import { Filter, Sparkles, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';

export default function PreMarketScreener({ screenerStocks = [], selectedSymbol, onSelectSymbol }) {
  return (
    <div className="bg-[#121824] border border-slate-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-amber-400" />
          <h3 className="font-semibold text-sm text-slate-100">Capa 2: Escáner Pre-Market & Catalizadores</h3>
        </div>
        <span className="text-[10px] text-slate-400 uppercase font-medium">ETFs Core + RVOL &gt; 1.5</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="text-[10px] text-slate-400 uppercase bg-slate-900/40 border-b border-slate-800">
            <tr>
              <th className="p-2">Ticker</th>
              <th className="p-2">Precio</th>
              <th className="p-2">Cambio %</th>
              <th className="p-2">RVOL</th>
              <th className="p-2">Earnings Hoy</th>
              <th className="p-2">Catalizador / Motivo</th>
              <th className="p-2 text-right">Acción</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {screenerStocks.map((s, idx) => (
              <tr
                key={idx}
                className={`hover:bg-slate-800/40 transition cursor-pointer ${
                  selectedSymbol === s.symbol ? 'bg-slate-800/60 border-l-2 border-emerald-400' : ''
                }`}
                onClick={() => onSelectSymbol(s.symbol)}
              >
                <td className="p-2 font-bold text-white flex items-center gap-1.5 font-sans">
                  {s.symbol}
                  {s.symbol === 'SPY' || s.symbol === 'QQQ' ? (
                    <span className="text-[9px] bg-blue-500/20 text-blue-400 px-1 rounded font-mono font-semibold">CORE</span>
                  ) : null}
                </td>
                <td className="p-2 text-slate-200">${s.price?.toFixed(2)}</td>
                <td className={`p-2 font-bold ${s.change_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {s.change_pct >= 0 ? '+' : ''}{s.change_pct?.toFixed(2)}%
                </td>
                <td className="p-2">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                    s.rvol >= 2.0 ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-800 text-slate-300'
                  }`}>
                    {s.rvol}x
                  </span>
                </td>
                <td className="p-2 font-sans">
                  {s.has_earnings ? (
                    <span className="text-amber-400 flex items-center gap-1 font-semibold text-[10px]">
                      <AlertCircle className="w-3 h-3" /> Reporta Hoy
                    </span>
                  ) : (
                    <span className="text-slate-500 text-[10px]">No</span>
                  )}
                </td>
                <td className="p-2 text-slate-400 font-sans text-xs truncate max-w-xs">{s.catalyst}</td>
                <td className="p-2 text-right font-sans">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectSymbol(s.symbol);
                    }}
                    className={`px-2 py-1 text-[11px] rounded transition font-medium ${
                      selectedSymbol === s.symbol
                        ? 'bg-emerald-500 text-slate-950 font-bold'
                        : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    Ver Gráfico
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
