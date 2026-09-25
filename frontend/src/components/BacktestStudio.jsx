import React, { useState, useRef, useEffect } from 'react';
import { History, Play, Award, TrendingUp, TrendingDown, Target, Shield, AlertTriangle, BarChart, CheckCircle2 } from 'lucide-react';
import { runBacktest } from '../services/api';

export default function BacktestStudio() {
  const [daysBack, setDaysBack] = useState(30);
  const [capital, setCapital] = useState(100000);
  const [riskPct, setRiskPct] = useState(1.0);
  const [minRr, setMinRr] = useState(2.0);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);

  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [mousePos, setMousePos] = useState(null);

  const handleRun = async () => {
    setLoading(true);
    try {
      const res = await runBacktest({
        symbols: ['SPY', 'QQQ'],
        days_back: Number(daysBack),
        initial_capital: Number(capital),
        risk_per_trade_pct: Number(riskPct),
        min_rr_ratio: Number(minRr)
      });
      setResults(res);
    } catch (err) {
      console.error('Error running backtest:', err);
    } finally {
      setLoading(false);
    }
  };

  // Dibujar curva de equidad con canvas de alta definición (High-DPI)
  useEffect(() => {
    if (!results || !results.equity_curve || results.equity_curve.length === 0) return;
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = container.getBoundingClientRect();
    const width = rect.width;
    const height = 280;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    ctx.resetTransform?.();
    ctx.scale(dpr, dpr);

    const curve = results.equity_curve;
    ctx.clearRect(0, 0, width, height);

    const marginLeft = 20;
    const marginRight = 75;
    const marginTop = 20;
    const marginBottom = 25;
    const plotWidth = width - marginLeft - marginRight;
    const plotHeight = height - marginTop - marginBottom;

    let minEq = Infinity;
    let maxEq = -Infinity;
    curve.forEach(pt => {
      if (pt.equity < minEq) minEq = pt.equity;
      if (pt.equity > maxEq) maxEq = pt.equity;
    });

    const padding = (maxEq - minEq) * 0.1 || 500;
    minEq -= padding;
    maxEq += padding;
    const range = maxEq - minEq;

    const getY = eq => marginTop + (1 - (eq - minEq) / range) * plotHeight;
    const getX = idx => marginLeft + (idx / (curve.length - 1)) * plotWidth;

    // Cuadrícula y etiquetas de precios en el eje Y
    ctx.strokeStyle = '#1E293B';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = marginTop + (plotHeight / 4) * i;
      ctx.beginPath();
      ctx.setLineDash([2, 4]);
      ctx.moveTo(marginLeft, y);
      ctx.lineTo(width - marginRight, y);
      ctx.stroke();
      ctx.setLineDash([]);

      const val = maxEq - (i / 4) * range;
      ctx.fillStyle = '#64748B';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`$${Math.round(val).toLocaleString()}`, width - marginRight + 6, y + 3);
    }

    // Dibujar degradado bajo la curva
    const gradient = ctx.createLinearGradient(0, marginTop, 0, marginTop + plotHeight);
    gradient.addColorStop(0, 'rgba(16, 185, 129, 0.25)');
    gradient.addColorStop(1, 'rgba(16, 185, 129, 0.0)');

    ctx.beginPath();
    curve.forEach((pt, i) => {
      const x = getX(i);
      const y = getY(pt.equity);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.lineTo(getX(curve.length - 1), marginTop + plotHeight);
    ctx.lineTo(getX(0), marginTop + plotHeight);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Dibujar línea principal de equidad
    ctx.strokeStyle = '#10B981';
    ctx.lineWidth = 2.5;
    ctx.beginPath();
    curve.forEach((pt, i) => {
      const x = getX(i);
      const y = getY(pt.equity);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Dibujar puntos clave en cada trade
    curve.forEach((pt, i) => {
      const x = getX(i);
      const y = getY(pt.equity);
      ctx.fillStyle = i === 0 ? '#64748B' : pt.equity >= curve[i - 1].equity ? '#10B981' : '#EF4444';
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    });

    // Crosshair interactivo
    if (mousePos && hoveredPoint) {
      const hX = getX(hoveredPoint.index);
      const hY = getY(hoveredPoint.equity);

      ctx.strokeStyle = 'rgba(148, 163, 184, 0.5)';
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);

      ctx.beginPath();
      ctx.moveTo(hX, marginTop);
      ctx.lineTo(hX, marginTop + plotHeight);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(marginLeft, hY);
      ctx.lineTo(width - marginRight, hY);
      ctx.stroke();
      ctx.setLineDash([]);

      // Círculo destacado en el punto activo
      ctx.fillStyle = '#38BDF8';
      ctx.beginPath();
      ctx.arc(hX, hY, 5, 0, Math.PI * 2);
      ctx.fill();

      // Indicador en eje Y
      ctx.fillStyle = '#38BDF8';
      ctx.fillRect(width - marginRight, hY - 9, marginRight - 5, 18);
      ctx.fillStyle = '#090D14';
      ctx.font = 'bold 10px monospace';
      ctx.fillText(`$${Math.round(hoveredPoint.equity).toLocaleString()}`, width - marginRight + 4, hY + 4);
    }

  }, [results, mousePos, hoveredPoint]);

  const handleMouseMove = e => {
    if (!results?.equity_curve || results.equity_curve.length === 0) return;
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const marginLeft = 20;
    const marginRight = 75;
    const plotWidth = rect.width - marginLeft - marginRight;
    const curve = results.equity_curve;

    const ratio = (x - marginLeft) / plotWidth;
    const idx = Math.max(0, Math.min(curve.length - 1, Math.round(ratio * (curve.length - 1))));

    setHoveredPoint({ ...curve[idx], index: idx });
    setMousePos({ x, y });
  };

  const handleMouseLeave = () => {
    setHoveredPoint(null);
    setMousePos(null);
  };

  return (
    <div className="space-y-6">
      {/* Studio Header & Controls */}
      <div className="bg-[#121824] border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-emerald-400" />
            <div>
              <h2 className="font-bold text-base text-white">Backtesting Studio Institucional</h2>
              <p className="text-xs text-slate-400">Simulación cuantitativa multi-temporal (SPY / QQQ) con R:R y sizing al 1%</p>
            </div>
          </div>

          <button
            onClick={handleRun}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold text-xs rounded-lg transition shadow-lg shadow-emerald-500/20 cursor-pointer"
          >
            <Play className="w-4 h-4 fill-current" />
            {loading ? 'Calculando Simulación...' : 'EJECUTAR BACKTEST'}
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Días Históricos</label>
            <select
              value={daysBack}
              onChange={e => setDaysBack(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 text-white text-xs rounded-lg p-2.5"
            >
              <option value="15">Últimos 15 días</option>
              <option value="30">Últimos 30 días</option>
              <option value="60">Últimos 60 días</option>
              <option value="90">Últimos 90 días</option>
            </select>
          </div>

          <div>
            <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Capital Inicial ($)</label>
            <input
              type="number"
              value={capital}
              onChange={e => setCapital(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 text-white text-xs rounded-lg p-2 font-mono"
            />
          </div>

          <div>
            <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Riesgo por Trade (%)</label>
            <input
              type="number"
              step="0.25"
              value={riskPct}
              onChange={e => setRiskPct(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 text-white text-xs rounded-lg p-2 font-mono"
            />
          </div>

          <div>
            <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Ratio R:R Mínimo</label>
            <input
              type="number"
              step="0.5"
              value={minRr}
              onChange={e => setMinRr(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 text-white text-xs rounded-lg p-2 font-mono"
            />
          </div>
        </div>
      </div>

      {/* Results View or Welcome Banner */}
      {results ? (
        <div className="space-y-6">
          {/* Key Metrics Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
            <div className="bg-[#121824] border border-slate-800 p-4 rounded-xl">
              <span className="text-[10px] text-slate-400 uppercase block font-medium">Ganancia Neta</span>
              <span className={`text-base font-bold font-mono ${results.total_net_profit >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                ${results.total_net_profit?.toLocaleString()}
              </span>
              <span className="text-[10px] text-slate-400 block mt-0.5">({results.total_return_pct}%)</span>
            </div>

            <div className="bg-[#121824] border border-slate-800 p-4 rounded-xl">
              <span className="text-[10px] text-slate-400 uppercase block font-medium">Win Rate</span>
              <span className="text-base font-bold text-white font-mono">{results.win_rate_pct}%</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">{results.total_trades} operaciones</span>
            </div>

            <div className="bg-[#121824] border border-slate-800 p-4 rounded-xl">
              <span className="text-[10px] text-slate-400 uppercase block font-medium">Profit Factor</span>
              <span className="text-base font-bold text-emerald-400 font-mono">{results.profit_factor}</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">&gt; 1.5 Saludable</span>
            </div>

            <div className="bg-[#121824] border border-slate-800 p-4 rounded-xl">
              <span className="text-[10px] text-slate-400 uppercase block font-medium">Max Drawdown</span>
              <span className="text-base font-bold text-rose-400 font-mono">-{results.max_drawdown_pct}%</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Control de riesgo</span>
            </div>

            <div className="bg-[#121824] border border-slate-800 p-4 rounded-xl">
              <span className="text-[10px] text-slate-400 uppercase block font-medium">Ratio de Sharpe</span>
              <span className="text-base font-bold text-blue-400 font-mono">{results.sharpe_ratio}</span>
              <span className="text-[10px] text-slate-400 block mt-0.5">Retorno ajustado</span>
            </div>

            <div className="bg-[#121824] border border-slate-800 p-4 rounded-xl">
              <span className="text-[10px] text-slate-400 uppercase block font-medium">Capital Final</span>
              <span className="text-base font-bold text-white font-mono">${results.final_capital?.toLocaleString()}</span>
              <span className="text-[10px] text-emerald-400 block mt-0.5">Saldo Proyectado</span>
            </div>
          </div>

          {/* Equity Curve Canvas */}
          <div className="bg-[#121824] border border-slate-800 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-sm text-slate-100 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                Curva de Capital (Equity Growth Curve)
              </h3>
              {hoveredPoint && (
                <div className="text-xs font-mono bg-slate-900 px-3 py-1 rounded border border-slate-800 flex items-center gap-3">
                  <span className="text-slate-400">Punto #{hoveredPoint.index}</span>
                  <span className="text-emerald-400 font-bold">Capital: ${Math.round(hoveredPoint.equity).toLocaleString()}</span>
                </div>
              )}
            </div>

            <div ref={containerRef} className="w-full h-72 bg-[#090D14] rounded-lg border border-slate-900 overflow-hidden relative">
              <canvas
                ref={canvasRef}
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
                className="w-full h-full block cursor-crosshair"
              />
            </div>
          </div>

          {/* Simulated Trades Table */}
          <div className="bg-[#121824] border border-slate-800 rounded-xl p-5 shadow-sm">
            <h3 className="font-semibold text-sm text-slate-100 mb-3">Operaciones Ejecutadas en la Simulación</h3>
            <div className="overflow-x-auto max-h-72 overflow-y-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="text-[10px] text-slate-400 uppercase bg-slate-900 border-b border-slate-800 font-sans">
                  <tr>
                    <th className="p-2">Fecha / Hora</th>
                    <th className="p-2">Símbolo</th>
                    <th className="p-2">Lado</th>
                    <th className="p-2">Entrada</th>
                    <th className="p-2">Salida</th>
                    <th className="p-2">R:R</th>
                    <th className="p-2">P&L ($)</th>
                    <th className="p-2">Motivo Salida</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {results.trades?.slice(0, 30).map((t, i) => (
                    <tr key={i} className="hover:bg-slate-800/30">
                      <td className="p-2 text-slate-400 font-sans text-[11px]">{t.entry_time}</td>
                      <td className="p-2 font-bold text-white font-sans">{t.symbol}</td>
                      <td className="p-2">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          t.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                        }`}>
                          {t.side}
                        </span>
                      </td>
                      <td className="p-2">${t.entry_price}</td>
                      <td className="p-2">${t.exit_price}</td>
                      <td className="p-2 text-blue-400">1:{t.risk_reward_ratio}</td>
                      <td className={`p-2 font-bold ${t.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {t.pnl >= 0 ? '+' : ''}${t.pnl}
                      </td>
                      <td className="p-2 text-slate-400 font-sans text-[10px]">
                        <span className={`px-1.5 py-0.5 rounded ${
                          t.exit_reason === 'TAKE_PROFIT' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                        }`}>
                          {t.exit_reason}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* Estado inicial claro antes de ejecutar backtest */
        <div className="bg-[#121824] border border-slate-800/80 rounded-xl p-8 text-center space-y-4">
          <div className="w-14 h-14 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl flex items-center justify-center mx-auto text-emerald-400 shadow-lg shadow-emerald-500/10">
            <BarChart className="w-7 h-7" />
          </div>
          <div className="max-w-md mx-auto">
            <h3 className="text-base font-bold text-white mb-1">Simulación Cuantitativa Histórica</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Evalúa la eficacia de la estrategia de confluencia Top-Down (Macro + Sentimiento + VWAP + Liquidez) sobre datos históricos intraday de SPY y QQQ.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-slate-400 pt-2">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Cálculo de Win Rate</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Profit Factor y Drawdown</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Curva de Crecimiento de Capital</span>
            </div>
          </div>
          <div className="pt-2">
            <button
              onClick={handleRun}
              disabled={loading}
              className="px-6 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold text-xs rounded-lg transition shadow-lg shadow-emerald-500/20 cursor-pointer inline-flex items-center gap-2"
            >
              <Play className="w-4 h-4 fill-current" />
              {loading ? 'Calculando Simulación...' : 'Iniciar Simulación de Backtest'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
