import React, { useState } from 'react';
import { Layers, Clock, TrendingUp, TrendingDown, CheckCircle2 } from 'lucide-react';

export default function ActivePositionsTable({ positions = [], tradeHistory = [] }) {
  const [activeSubTab, setActiveSubTab] = useState('positions');

  return (
    <div className="bg-[#121824] border border-slate-800 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-4 border-b border-slate-800/80 pb-3">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-emerald-400" />
          <h3 className="font-semibold text-sm text-slate-100">Posiciones & Órdenes Bracket</h3>
        </div>

        <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-xs">
          <button
            onClick={() => setActiveSubTab('positions')}
            className={`px-3 py-1 font-semibold rounded-md transition ${
              activeSubTab === 'positions' ? 'bg-slate-800 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            Posiciones Abiertas ({positions.length})
          </button>
          <button
            onClick={() => setActiveSubTab('history')}
            className={`px-3 py-1 font-semibold rounded-md transition ${
              activeSubTab === 'history' ? 'bg-slate-800 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            Historial de Trades ({tradeHistory.length})
          </button>
        </div>
      </div>

      {/* OPEN POSITIONS TAB */}
      {activeSubTab === 'positions' && (
        <div className="overflow-x-auto">
          {positions.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-xs">
              No hay posiciones abiertas en este momento. El bot está buscando confluencias Top-Down.
            </div>
          ) : (
            <table className="w-full text-left text-xs">
              <thead className="text-[10px] text-slate-400 uppercase bg-slate-900/40 border-b border-slate-800">
                <tr>
                  <th className="p-2">Símbolo</th>
                  <th className="p-2">Lado</th>
                  <th className="p-2">Acciones</th>
                  <th className="p-2">Entrada</th>
                  <th className="p-2">Precio Actual</th>
                  <th className="p-2">Stop Loss</th>
                  <th className="p-2">Take Profit</th>
                  <th className="p-2">P&L No Realizado</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {positions.map((p, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition">
                    <td className="p-2 font-bold text-white flex items-center gap-1.5 font-sans">
                      {p.symbol}
                    </td>
                    <td className="p-2">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        p.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                      }`}>
                        {p.side}
                      </span>
                    </td>
                    <td className="p-2 text-slate-300">{p.qty}</td>
                    <td className="p-2 text-slate-300">${p.avg_entry_price?.toFixed(2)}</td>
                    <td className="p-2 font-bold text-white">${p.current_price?.toFixed(2)}</td>
                    <td className="p-2 text-rose-400">${p.stop_loss || (p.avg_entry_price * 0.99).toFixed(2)}</td>
                    <td className="p-2 text-emerald-400">${p.take_profit || (p.avg_entry_price * 1.025).toFixed(2)}</td>
                    <td className={`p-2 font-bold ${p.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {p.unrealized_pnl >= 0 ? '+' : ''}${p.unrealized_pnl?.toFixed(2)} ({p.unrealized_pnl_pct >= 0 ? '+' : ''}{p.unrealized_pnl_pct?.toFixed(2)}%)
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* TRADE HISTORY TAB */}
      {activeSubTab === 'history' && (
        <div className="overflow-x-auto max-h-60 overflow-y-auto">
          {tradeHistory.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-xs">
              No hay historial registrado aún en la base de datos SQLite.
            </div>
          ) : (
            <table className="w-full text-left text-xs">
              <thead className="text-[10px] text-slate-400 uppercase bg-slate-900/40 border-b border-slate-800">
                <tr>
                  <th className="p-2">Hora</th>
                  <th className="p-2">Símbolo</th>
                  <th className="p-2">Estrategia</th>
                  <th className="p-2">Entrada</th>
                  <th className="p-2">Salida</th>
                  <th className="p-2">Ratio R:R</th>
                  <th className="p-2">P&L</th>
                  <th className="p-2">Motivo Salida</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {tradeHistory.map((t, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition">
                    <td className="p-2 text-slate-400 text-[10px] font-sans">
                      {new Date(t.entry_time).toLocaleTimeString()}
                    </td>
                    <td className="p-2 font-bold text-white font-sans">{t.symbol}</td>
                    <td className="p-2 text-slate-400 font-sans">{t.strategy}</td>
                    <td className="p-2 text-slate-300">${t.entry_price?.toFixed(2)}</td>
                    <td className="p-2 text-slate-300">${t.exit_price ? t.exit_price.toFixed(2) : '-'}</td>
                    <td className="p-2 text-blue-400">1:{t.risk_reward_ratio}</td>
                    <td className={`p-2 font-bold ${t.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {t.pnl >= 0 ? '+' : ''}${t.pnl?.toFixed(2)}
                    </td>
                    <td className="p-2 text-slate-400 font-sans text-[10px]">{t.exit_reason || t.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
