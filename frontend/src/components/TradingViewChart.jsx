import React, { useState, useRef, useEffect, memo } from 'react';
import { BarChart2, Activity, Layers, Crosshair, Zap, ExternalLink, RefreshCw } from 'lucide-react';

// Subcomponente: Widget Oficial de TradingView en Tiempo Real
const TradingViewEmbedWidget = memo(function TradingViewEmbedWidget({ symbol }) {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.innerHTML = '';

    const widgetDiv = document.createElement('div');
    widgetDiv.className = 'tradingview-widget-container__widget';
    widgetDiv.style.height = '100%';
    widgetDiv.style.width = '100%';
    container.appendChild(widgetDiv);

    // Mapeo de exchange exacto para TradingView
    let tvSymbol = symbol;
    if (symbol === 'SPY') tvSymbol = 'AMEX:SPY';
    else if (symbol === 'QQQ') tvSymbol = 'NASDAQ:QQQ';
    else tvSymbol = `NASDAQ:${symbol}`;

    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.type = 'text/javascript';
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: true,
      symbol: tvSymbol,
      interval: '5',
      timezone: 'America/New_York',
      theme: 'dark',
      style: '1',
      locale: 'es',
      enable_publishing: false,
      backgroundColor: 'rgba(9, 13, 20, 1)',
      gridColor: 'rgba(30, 41, 59, 0.4)',
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: false,
      calendar: false,
      hide_volume: false,
      support_host: 'https://www.tradingview.com'
    });

    container.appendChild(script);

    return () => {
      if (container) container.innerHTML = '';
    };
  }, [symbol]);

  return (
    <div className="w-full h-[450px] relative bg-[#090D14] rounded-lg border border-slate-900 overflow-hidden">
      <div ref={containerRef} className="tradingview-widget-container h-full w-full" />
    </div>
  );
});

// Subcomponente: Gráfico Cuantitativo con Canvas Adaptativo (High-DPI)
function QuantitativeEngineCanvas({ candles, levels, symbol }) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const [hoveredCandle, setHoveredCandle] = useState(null);
  const [mousePos, setMousePos] = useState(null);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas || candles.length === 0) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    const rect = container.getBoundingClientRect();
    const width = rect.width;
    const height = 450;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    ctx.resetTransform?.();
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);

    // Márgenes
    const marginTop = 25;
    const marginBottom = 30;
    const marginLeft = 15;
    const marginRight = 65;
    const volumeHeight = 65;

    const chartWidth = width - marginLeft - marginRight;
    const mainChartHeight = height - marginTop - marginBottom - volumeHeight - 15;
    const mainChartBottom = marginTop + mainChartHeight;
    const volumeBottom = height - marginBottom;

    // Calcular límites de precio
    let minPrice = Infinity;
    let maxPrice = -Infinity;
    let maxVol = 1;

    candles.forEach(c => {
      if (c.low < minPrice) minPrice = c.low;
      if (c.high > maxPrice) maxPrice = c.high;
      if (c.vwap_upper && c.vwap_upper > maxPrice) maxPrice = c.vwap_upper;
      if (c.vwap_lower && c.vwap_lower < minPrice) minPrice = c.vwap_lower;
      if (c.volume > maxVol) maxVol = c.volume;
    });

    if (levels.pdh && levels.pdh > maxPrice) maxPrice = levels.pdh;
    if (levels.pdl && levels.pdl < minPrice) minPrice = levels.pdl;

    const pricePadding = (maxPrice - minPrice) * 0.08 || 1.0;
    minPrice -= pricePadding;
    maxPrice += pricePadding;
    const priceRange = maxPrice - minPrice;

    const getY = price => marginTop + (1 - (price - minPrice) / priceRange) * mainChartHeight;
    const getVolY = vol => volumeBottom - (vol / maxVol) * volumeHeight;

    // Cuadrícula horizontal y escala de precios
    ctx.strokeStyle = '#1E293B';
    ctx.lineWidth = 1;
    const gridSteps = 5;
    for (let i = 0; i <= gridSteps; i++) {
      const y = marginTop + (mainChartHeight / gridSteps) * i;
      ctx.beginPath();
      ctx.setLineDash([2, 4]);
      ctx.moveTo(marginLeft, y);
      ctx.lineTo(width - marginRight, y);
      ctx.stroke();
      ctx.setLineDash([]);

      const price = maxPrice - (i / gridSteps) * priceRange;
      ctx.fillStyle = '#64748B';
      ctx.font = '11px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`$${price.toFixed(2)}`, width - marginRight + 6, y + 4);
    }

    const candleCount = candles.length;
    const slotWidth = chartWidth / candleCount;
    const candleWidth = Math.max(3, slotWidth * 0.65);

    // Dibujar barras de volumen
    candles.forEach((c, idx) => {
      const x = marginLeft + idx * slotWidth + (slotWidth - candleWidth) / 2;
      const volY = getVolY(c.volume);
      const isUp = c.close >= c.open;

      ctx.fillStyle = isUp ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)';
      ctx.fillRect(x, volY, candleWidth, volumeBottom - volY);
    });

    // Separador visual de volumen
    ctx.strokeStyle = '#1E293B';
    ctx.beginPath();
    ctx.moveTo(marginLeft, volumeBottom - volumeHeight - 5);
    ctx.lineTo(width - marginRight, volumeBottom - volumeHeight - 5);
    ctx.stroke();

    ctx.fillStyle = '#475569';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('VOLUMEN', marginLeft + 5, volumeBottom - volumeHeight + 10);

    // Dibujar velas japonesas
    candles.forEach((c, idx) => {
      const centerX = marginLeft + idx * slotWidth + slotWidth / 2;
      const x = centerX - candleWidth / 2;
      const isUp = c.close >= c.open;

      const openY = getY(c.open);
      const closeY = getY(c.close);
      const highY = getY(c.high);
      const lowY = getY(c.low);

      // Mecha (Wick)
      ctx.strokeStyle = isUp ? '#10B981' : '#EF4444';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(centerX, highY);
      ctx.lineTo(centerX, lowY);
      ctx.stroke();

      // Cuerpo (Body)
      ctx.fillStyle = isUp ? '#10B981' : '#EF4444';
      const bodyTop = Math.min(openY, closeY);
      const bodyHeight = Math.max(2, Math.abs(closeY - openY));
      ctx.fillRect(x, bodyTop, candleWidth, bodyHeight);
    });

    // Dibujar Bandas de Desviación VWAP (±1σ en Cyan, ±2σ en Púrpura)
    if (candles[0]?.vwap_upper) {
      ctx.strokeStyle = 'rgba(6, 182, 212, 0.5)';
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      candles.forEach((c, idx) => {
        const x = marginLeft + idx * slotWidth + slotWidth / 2;
        const y = getY(c.vwap_upper);
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();

      ctx.beginPath();
      candles.forEach((c, idx) => {
        const x = marginLeft + idx * slotWidth + slotWidth / 2;
        const y = getY(c.vwap_lower);
        if (idx === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Dibujar línea principal de VWAP (dorado institucional)
    ctx.strokeStyle = '#F59E0B';
    ctx.lineWidth = 2;
    ctx.beginPath();
    candles.forEach((c, idx) => {
      const x = marginLeft + idx * slotWidth + slotWidth / 2;
      const y = getY(c.vwap);
      if (idx === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Dibujar Nivel de Liquidez PDH (Rojo discontinuo)
    if (levels.pdh) {
      const yPdh = getY(levels.pdh);
      ctx.strokeStyle = '#F43F5E';
      ctx.setLineDash([6, 4]);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(marginLeft, yPdh);
      ctx.lineTo(width - marginRight, yPdh);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = '#F43F5E';
      ctx.font = 'bold 10px monospace';
      ctx.fillText(`PDH $${levels.pdh}`, marginLeft + 5, yPdh - 5);
    }

    // Dibujar Nivel de Liquidez PDL (Verde discontinuo)
    if (levels.pdl) {
      const yPdl = getY(levels.pdl);
      ctx.strokeStyle = '#10B981';
      ctx.setLineDash([6, 4]);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(marginLeft, yPdl);
      ctx.lineTo(width - marginRight, yPdl);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = '#10B981';
      ctx.font = 'bold 10px monospace';
      ctx.fillText(`PDL $${levels.pdl}`, marginLeft + 5, yPdl - 5);
    }

    // Escala de tiempo inferior (Eje X)
    ctx.fillStyle = '#64748B';
    ctx.font = '10px monospace';
    ctx.textAlign = 'center';
    const timeStep = Math.max(1, Math.floor(candleCount / 6));
    for (let i = 0; i < candleCount; i += timeStep) {
      const x = marginLeft + i * slotWidth + slotWidth / 2;
      const timeLabel = candles[i]?.time_str || `T-${candleCount - i}`;
      ctx.fillText(timeLabel, x, height - 10);
    }

    // Crosshair interactivo si el mouse está encima
    if (mousePos && hoveredCandle) {
      const hoverX = mousePos.x;
      const hoverY = mousePos.y;

      ctx.strokeStyle = 'rgba(148, 163, 184, 0.4)';
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 2]);

      // Línea vertical
      ctx.beginPath();
      ctx.moveTo(hoverX, marginTop);
      ctx.lineTo(hoverX, volumeBottom);
      ctx.stroke();

      // Línea horizontal
      if (hoverY >= marginTop && hoverY <= mainChartBottom) {
        ctx.beginPath();
        ctx.moveTo(marginLeft, hoverY);
        ctx.lineTo(width - marginRight, hoverY);
        ctx.stroke();

        const hoveredPrice = maxPrice - ((hoverY - marginTop) / mainChartHeight) * priceRange;
        ctx.fillStyle = '#38BDF8';
        ctx.fillRect(width - marginRight, hoverY - 9, marginRight - 5, 18);
        ctx.fillStyle = '#090D14';
        ctx.font = 'bold 10px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(`$${hoveredPrice.toFixed(2)}`, width - marginRight + 4, hoverY + 3);
      }

      ctx.setLineDash([]);
    }

  }, [candles, levels, mousePos, hoveredCandle]);

  const handleMouseMove = e => {
    const canvas = canvasRef.current;
    if (!canvas || candles.length === 0) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const marginLeft = 15;
    const marginRight = 65;
    const chartWidth = rect.width - marginLeft - marginRight;
    const slotWidth = chartWidth / candles.length;

    const candleIdx = Math.floor((x - marginLeft) / slotWidth);
    if (candleIdx >= 0 && candleIdx < candles.length) {
      setHoveredCandle(candles[candleIdx]);
      setMousePos({ x, y });
    } else {
      setHoveredCandle(null);
      setMousePos(null);
    }
  };

  const handleMouseLeave = () => {
    setHoveredCandle(null);
    setMousePos(null);
  };

  const activeCandle = hoveredCandle || candles[candles.length - 1];

  return (
    <div ref={containerRef} className="w-full relative bg-[#090D14] rounded-lg border border-slate-900 overflow-hidden">
      {/* HUD Info Header */}
      {activeCandle && (
        <div className="absolute top-2 left-4 z-10 flex flex-wrap items-center gap-3 text-[11px] font-mono bg-slate-950/80 px-2.5 py-1 rounded-md border border-slate-800/80 backdrop-blur-sm">
          <span className="text-slate-400 font-sans">{activeCandle.time_str ? `${activeCandle.time_str} EST` : symbol}</span>
          <span className="text-slate-400">O: <strong className="text-white">${activeCandle.open?.toFixed(2)}</strong></span>
          <span className="text-slate-400">H: <strong className="text-emerald-400">${activeCandle.high?.toFixed(2)}</strong></span>
          <span className="text-slate-400">L: <strong className="text-rose-400">${activeCandle.low?.toFixed(2)}</strong></span>
          <span className="text-slate-400">C: <strong className={activeCandle.close >= activeCandle.open ? 'text-emerald-400' : 'text-rose-400'}>${activeCandle.close?.toFixed(2)}</strong></span>
          <span className="text-amber-400 font-semibold">VWAP: ${activeCandle.vwap?.toFixed(2)}</span>
          <span className="text-slate-400">Vol: <strong className="text-slate-200">{activeCandle.volume?.toLocaleString()}</strong></span>
        </div>
      )}

      <canvas
        ref={canvasRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        className="w-full h-[450px] block cursor-crosshair"
      />
    </div>
  );
}

// Componente Principal
export default function TradingViewChart({
  symbol,
  onSelectSymbol,
  technicalData,
  availableSymbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AMD', 'AAPL']
}) {
  const [chartMode, setChartMode] = useState('tradingview'); // 'tradingview' | 'quant'

  const candles = technicalData?.candles || [];
  const levels = technicalData?.levels || {};
  const setup = technicalData?.setup || {};
  const currentPrice = technicalData?.current_price || (candles.length > 0 ? candles[candles.length - 1].close : null);

  return (
    <div className="bg-[#121824] border border-slate-800 rounded-xl p-4 shadow-sm">
      {/* Barra superior de navegación del gráfico */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-emerald-400" />
            <span className="font-bold text-lg text-white">{symbol}</span>
            {currentPrice && (
              <span className="text-sm font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                ${currentPrice.toFixed(2)}
              </span>
            )}
          </div>

          {/* Selector de Símbolos */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-0.5">
            {availableSymbols.map(sym => (
              <button
                key={sym}
                onClick={() => onSelectSymbol(sym)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition ${
                  symbol === sym
                    ? 'bg-slate-800 text-emerald-400 shadow font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {sym}
              </button>
            ))}
          </div>
        </div>

        {/* Selector de Modo: TradingView Pro vs Motor Cuantitativo */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-slate-900/90 border border-slate-700/80 rounded-lg p-0.5 shadow-inner">
            <button
              onClick={() => setChartMode('tradingview')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition ${
                chartMode === 'tradingview'
                  ? 'bg-emerald-500 text-slate-950 shadow-md font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>TradingView Pro (En Vivo)</span>
            </button>

            <button
              onClick={() => setChartMode('quant')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md transition ${
                chartMode === 'quant'
                  ? 'bg-emerald-500 text-slate-950 shadow-md font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Motor Cuantitativo (VWAP & Liquidez)</span>
            </button>
          </div>
        </div>
      </div>

      {/* Leyenda activa cuando está en modo Motor Cuantitativo */}
      {chartMode === 'quant' && (
        <div className="flex flex-wrap items-center justify-between gap-2 mb-3 px-2 py-1.5 bg-slate-900/50 rounded-lg border border-slate-800/60 text-xs">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-1 bg-amber-500 rounded" />
              <span className="text-slate-400">VWAP Institucional</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 border-b border-cyan-400 border-dashed" />
              <span className="text-slate-400">Bandas Desv. (±1σ)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 border-b-2 border-rose-500 border-dashed" />
              <span className="text-slate-400">PDH (Máx previo)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 border-b-2 border-emerald-500 border-dashed" />
              <span className="text-slate-400">PDL (Mín previo)</span>
            </div>
          </div>
          <div className="text-[11px] text-slate-500">
            Pasa el mouse sobre el gráfico para ver crosshair y métricas
          </div>
        </div>
      )}

      {/* Setup notification banner if active */}
      {setup?.signal && setup.signal !== 'NONE' && (
        <div className="mb-3 bg-emerald-500/10 border border-emerald-500/30 p-2.5 rounded-lg flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <Crosshair className="w-4 h-4 text-emerald-400 animate-spin" />
            <span className="font-semibold text-emerald-300">SETUP DETECTADO: {setup.setup_type} ({setup.signal})</span>
            <span className="text-slate-400 hidden sm:inline">| {setup.reason}</span>
          </div>
          <div className="flex items-center gap-3 font-mono font-bold">
            <span className="text-emerald-400">Entrada: ${setup.entry_price?.toFixed(2)}</span>
            <span className="text-rose-400">SL: ${setup.stop_loss?.toFixed(2)}</span>
            <span className="text-blue-400">TP: ${setup.take_profit?.toFixed(2)}</span>
            <span className="bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded">R:R 1:{setup.target_rr}</span>
          </div>
        </div>
      )}

      {/* Contenedor del Gráfico */}
      {chartMode === 'tradingview' ? (
        <TradingViewEmbedWidget symbol={symbol} />
      ) : candles.length > 0 ? (
        <QuantitativeEngineCanvas candles={candles} levels={levels} symbol={symbol} />
      ) : (
        <div className="w-full h-[450px] flex flex-col items-center justify-center bg-[#090D14] rounded-lg border border-slate-900 text-slate-400 gap-2">
          <RefreshCw className="w-6 h-6 animate-spin text-emerald-400" />
          <span className="text-xs">Cargando datos cuantitativos de {symbol}...</span>
        </div>
      )}
    </div>
  );
}
