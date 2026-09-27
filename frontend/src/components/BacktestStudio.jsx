import React, { useState, useRef, useEffect } from 'react';
import { 
  History, Play, Award, TrendingUp, TrendingDown, Target, Shield, 
  AlertTriangle, BarChart, CheckCircle2, Database, Layers, Send, Check, Cpu 
} from 'lucide-react';
import { runBacktest, runMT5Backtest, fetchMT5Status, sendMT5TelegramReport } from '../services/api';

export default function BacktestStudio() {
  // Motor y fuente de datos
  const [dataSource, setDataSource] = useState('MT5'); // 'MT5' o 'TOP_DOWN'
  const [mt5Status, setMt5Status] = useState(null);

  // Parámetros MT5 & Order Blocks
  const [symbol, setSymbol] = useState('EURUSD');
  const [timeframe, setTimeframe] = useState('M5');
  const [barsCount, setBarsCount] = useState(1000);
  const [rvolThreshold, setRvolThreshold] = useState(1.4);
  const [tp1Ratio, setTp1Ratio] = useState(1.5);
  const [tp2Ratio, setTp2Ratio] = useState(3.0);

  // Parámetros Globales de Cuenta y Riesgo
  const [capital, setCapital] = useState(100000);
  const [riskPct, setRiskPct] = useState(1.0);
  const [daysBack, setDaysBack] = useState(30);

  // Estado de ejecución y resultados
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [telegramSending, setTelegramSending] = useState(false);
  const [telegramSent, setTelegramSent] = useState(false);

  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [mousePos, setMousePos] = useState(null);

  // Cargar estado de MT5 al montar
  useEffect(() => {
    fetchMT5Status().then(st => {
      if (st) setMt5Status(st);
    }).catch(console.error);
  }, []);

  const handleRun = async () => {
    setLoading(true);
    setTelegramSent(false);
    try {
      if (dataSource === 'MT5') {
        const res = await runMT5Backtest({
          symbols: [symbol],
          timeframe: timeframe,
          bars_count: Number(barsCount),
          initial_capital: Number(capital),
          risk_per_trade_pct: Number(riskPct),
          rvol_threshold: Number(rvolThreshold),
          tp1_rr: Number(tp1Ratio),
          tp2_rr: Number(tp2Ratio),
          send_telegram: false
        });
        setResults(res);
      } else {
        const res = await runBacktest({
          symbols: ['SPY', 'QQQ'],
          days_back: Number(daysBack),
          initial_capital: Number(capital),
          risk_per_trade_pct: Number(riskPct),
          min_rr_ratio: 2.0
        });
        setResults(res);
      }
    } catch (err) {
      console.error('Error running backtest:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSendTelegram = async () => {
    if (!results) return;
    setTelegramSending(true);
    try {
      const res = await sendMT5TelegramReport(results);
      if (res?.success) {
        setTelegramSent(true);
        setTimeout(() => setTelegramSent(false), 5000);
      }
    } catch (err) {
      console.error('Error enviando reporte a Telegram:', err);
    } finally {
      setTelegramSending(false);
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
    const getX = idx => marginLeft + (idx / Math.max(1, curve.length - 1)) * plotWidth;

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

      ctx.fillStyle = '#38BDF8';
      ctx.beginPath();
      ctx.arc(hX, hY, 5, 0, Math.PI * 2);
      ctx.fill();

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
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-bold text-base text-white">Backtesting Studio Cuantitativo</h2>
                {mt5Status?.connected && (
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded font-mono font-bold flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    MT5 Conectado (Build {mt5Status.terminal_info?.build || '6231'})
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">
                Extracción histórica nativa en MetaTrader 5 y validación de Order Blocks (OB) + RVOL + EMA 50/200
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRun}
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold text-xs rounded-lg transition shadow-lg shadow-emerald-500/20 cursor-pointer"
            >
              <Play className="w-4 h-4 fill-current" />
              {loading ? 'Ejecutando Simulación...' : 'EJECUTAR BACKTEST'}
            </button>
          </div>
        </div>

        {/* Source Selector Tabs */}
        <div className="flex items-center gap-2 mb-4 bg-slate-900/60 p-1 rounded-lg border border-slate-800 w-fit">
          <button
            onClick={() => setDataSource('MT5')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition ${
              dataSource === 'MT5' ? 'bg-emerald-500 text-slate-950 shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            MetaTrader 5 (Datos Oficiales)
          </button>
          <button
            onClick={() => setDataSource('TOP_DOWN')}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition ${
              dataSource === 'TOP_DOWN' ? 'bg-emerald-500 text-slate-950 shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            Top-Down Intraday (Simulador)
          </button>
        </div>

        {/* Dynamic Controls Grid */}
        {dataSource === 'MT5' ? (
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
            <div>
              <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Activo / Símbolo</label>
              <select
                value={symbol}
                onChange={e => setSymbol(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 text-white text-xs rounded-lg p-2 font-mono font-bold"
              >
                <option value="EURUSD">EURUSD (Forex)</option>
                <option value="GBPUSD">GBPUSD (Forex)</option>
                <option value="SPY">SPY (S&P 500 ETF)</option>
                <option value="QQQ">QQQ (Nasdaq 100 ETF)</option>
                <option value="AAPL">AAPL (Apple Inc.)</option>
                <option value="TSLA">TSLA (Tesla Inc.)</option>
                <option value="US500">US500 (Índice)</option>
                <option value="USTEC">USTEC (Tecnológico)</option>
              </select>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Temporalidad</label>
              <select
                value={timeframe}
                onChange={e => setTimeframe(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 text-white text-xs rounded-lg p-2 font-mono"
              >
                <option value="M1">1 Minuto (M1)</option>
                <option value="M5">5 Minutos (M5)</option>
                <option value="M15">15 Minutos (M15)</option>
                <option value="H1">1 Hora (H1)</option>
                <option value="D1">Diario (D1)</option>
              </select>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Velas a Analizar</label>
              <select
                value={barsCount}
                onChange={e => setBarsCount(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 text-white text-xs rounded-lg p-2 font-mono"
              >
                <option value="500">500 velas</option>
                <option value="1000">1,000 velas</option>
                <option value="2000">2,000 velas</option>
                <option value="5000">5,000 velas</option>
              </select>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Filtro RVOL Mín</label>
              <input
                type="number"
                step="0.1"
                value={rvolThreshold}
                onChange={e => setRvolThreshold(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 text-white text-xs rounded-lg p-2 font-mono"
              />
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
              <label className="text-[10px] text-slate-400 uppercase font-semibold block mb-1">Riesgo / Trade (%)</label>
              <input
                type="number"
                step="0.25"
                value={riskPct}
                onChange={e => setRiskPct(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 text-white text-xs rounded-lg p-2 font-mono"
              />
            </div>
          </div>
        ) : (
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
                value={tp2Ratio}
                onChange={e => setTp2Ratio(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 text-white text-xs rounded-lg p-2 font-mono"
              />
            </div>
          </div>
        )}
      </div>

      {/* Results View or Welcome Banner */}
      {results ? (
        <div className="space-y-6">
          {/* Header Action Strip */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-[#121824] border border-slate-800 p-3.5 rounded-xl">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                {results.strategy || 'Estrategia Institucional'}
              </span>
              <span className="text-[11px] bg-blue-500/10 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded font-mono">
                {results.data_source || 'MetaTrader 5'}
              </span>
            </div>

            <button
              onClick={handleSendTelegram}
              disabled={telegramSending}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-bold rounded-lg transition border cursor-pointer ${
                telegramSent
                  ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                  : 'bg-blue-600 hover:bg-blue-500 text-white border-blue-500 shadow-md shadow-blue-500/20'
              }`}
            >
              {telegramSent ? <Check className="w-3.5 h-3.5" /> : <Send className="w-3.5 h-3.5" />}
              <span>{telegramSending ? 'Enviando...' : telegramSent ? '¡Reporte Enviado a Telegram!' : 'Enviar Reporte a Telegram'}</span>
            </button>
          </div>

          {/* Key Metrics Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
            <div className="bg-[#121824] border border-slate-800 p-4 rounded-xl">
              <span className="text-[10px] text-slate-400 uppercase block font-medium">Ganancia Neta</span>
              <span className={`text-base font-bold font-mono ${(results.net_profit ?? results.total_net_profit) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                ${(results.net_profit ?? results.total_net_profit)?.toLocaleString()}
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
              <span className="text-base font-bold text-white font-mono">${(results.final_equity ?? results.final_capital)?.toLocaleString()}</span>
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
                  <span className="text-slate-400">Trade #{hoveredPoint.index}</span>
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
                    <th className="p-2">Stop Loss</th>
                    <th className="p-2">Take Profit</th>
                    <th className="p-2">P&L ($)</th>
                    <th className="p-2">Motivo Salida</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {results.trades?.slice(0, 40).map((t, i) => (
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
                      <td className="p-2 text-rose-400">${t.stop_loss}</td>
                      <td className="p-2 text-emerald-400">${t.take_profit_2 || t.take_profit}</td>
                      <td className={`p-2 font-bold ${t.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {t.pnl >= 0 ? '+' : ''}${t.pnl}
                      </td>
                      <td className="p-2 text-slate-400 font-sans text-[10px]">
                        <span className={`px-1.5 py-0.5 rounded ${
                          t.exit_reason?.includes('PROFIT') ? 'bg-emerald-500/10 text-emerald-400' : 
                          t.exit_reason?.includes('BREAKEVEN') ? 'bg-blue-500/10 text-blue-400' : 'bg-rose-500/10 text-rose-400'
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
            <h3 className="text-base font-bold text-white mb-1">Simulación Cuantitativa con MetaTrader 5</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Evalúa la eficacia de la estrategia de Order Blocks (OB) con filtro RVOL y EMA 50/200 directamente sobre velas históricas reales extraídas del terminal MetaTrader 5.
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-slate-400 pt-2">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Conexión Nativa MT5 (12,000+ Símbolos)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Estrategia Order Blocks & SMC</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Alertas y Reportes por Telegram</span>
            </div>
          </div>
          <div className="pt-2">
            <button
              onClick={handleRun}
              disabled={loading}
              className="px-6 py-2.5 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold text-xs rounded-lg transition shadow-lg shadow-emerald-500/20 cursor-pointer inline-flex items-center gap-2"
            >
              <Play className="w-4 h-4 fill-current" />
              {loading ? 'Calculando Simulación...' : 'Iniciar Simulación con MetaTrader 5'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
