import React from 'react';
import { Activity, Play, Pause, AlertOctagon, Settings as SettingsIcon, ShieldCheck, Zap, Bell, HelpCircle, GitBranch, Network } from 'lucide-react';

export default function TopNavbar({
  status,
  onToggleBot,
  onPanic,
  onOpenSettings,
  onOpenNotifications,
  onOpenHelp,
  unreadCount = 0,
  onOpenBacktest,
  onTriggerTestTrade,
  activeTab,
  setActiveTab,
  onSyncGitHub,
  isSyncing = false,
  onAuditLatency
}) {
  const isRunning = status?.is_running || false;
  const equity = status?.account_equity || 100000;
  const dailyPnl = status?.daily_pnl || 0;
  const dailyPnlPct = status?.daily_pnl_pct || 0;
  const circuitBreaker = status?.circuit_breaker_tripped || false;

  const latency = status?.latency;
  const moomooLat = latency?.opend_latency_ms || 0;
  const alpacaLat = latency?.alpaca_latency_ms || 0;
  const isHighLatency = latency?.high_latency_mode || false;

  return (
    <header className="border-b border-slate-800 bg-[#0E131F]/95 backdrop-blur sticky top-0 z-40 w-full max-w-full">
      {/* TIER 1: BRAND + NAVEGACIÓN + ACCIONES */}
      <div className="px-3 sm:px-6 py-2.5 flex items-center justify-between gap-3 w-full border-b border-slate-800/60">
        
        {/* Brand & Tabs */}
        <div className="flex items-center gap-3 sm:gap-5 shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold shrink-0">
              <Activity className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-base sm:text-lg tracking-tight text-white">TradePulse</span>
                <span className="text-[9px] uppercase tracking-wider bg-blue-500/20 text-blue-400 px-1 py-0.5 rounded border border-blue-500/30 font-semibold hidden sm:inline-block">TOP-DOWN</span>
              </div>
              <p className="text-[10px] text-slate-400 hidden lg:block leading-none">Motor Cuantitativo Intraday</p>
            </div>
          </div>

          <nav className="flex items-center bg-slate-900/90 p-0.5 rounded-lg border border-slate-800 shrink-0">
            <button
              onClick={() => setActiveTab('cockpit')}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                activeTab === 'cockpit'
                  ? 'bg-emerald-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Cockpit & Gráfico
            </button>
            <button
              onClick={() => setActiveTab('backtest')}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-all ${
                activeTab === 'backtest'
                  ? 'bg-emerald-500 text-slate-950 font-bold shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Backtest
            </button>
          </nav>
        </div>

        {/* Action Controls & Bot Toggle */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {circuitBreaker && (
            <div className="bg-rose-500/20 text-rose-400 border border-rose-500/40 px-2 py-1 rounded text-[11px] font-bold flex items-center gap-1 animate-pulse">
              <AlertOctagon className="w-3.5 h-3.5 shrink-0" />
              <span className="hidden sm:inline">CIRCUIT BREAKER</span>
            </div>
          )}

          {/* Test Order Button */}
          <button
            onClick={onTriggerTestTrade}
            title="Enviar Bracket Order de prueba para verificar ejecución"
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 transition cursor-pointer"
          >
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden md:inline">Test Trade</span>
          </button>

          {/* Bot Start / Stop Switch */}
          <button
            onClick={onToggleBot}
            disabled={circuitBreaker}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-bold text-xs tracking-wide transition shadow-lg cursor-pointer ${
              isRunning
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30'
                : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold shadow-emerald-500/20'
            }`}
          >
            {isRunning ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <Pause className="w-3.5 h-3.5" /> <span>PAUSAR</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" /> <span>ACTIVAR</span>
              </>
            )}
          </button>

          {/* PANIC BUTTON */}
          <button
            onClick={onPanic}
            title="Botón de Pánico: Cancelar todas las órdenes y cerrar todas las posiciones inmediatamente"
            className="flex items-center gap-1 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-lg transition shadow-lg shadow-rose-600/30 active:scale-95 cursor-pointer"
          >
            <AlertOctagon className="w-3.5 h-3.5" />
            <span>PÁNICO</span>
          </button>

          {/* Help Center Button */}
          <button
            onClick={onOpenHelp}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 transition border border-emerald-500/30 font-semibold text-xs cursor-pointer"
            title="Centro de Ayuda y Guía del Sistema"
          >
            <HelpCircle className="w-3.5 h-3.5 text-emerald-400" />
            <span className="hidden md:inline">Ayuda</span>
          </button>

          {/* Notifications Center Bell Button */}
          <button
            onClick={onOpenNotifications}
            className="relative p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition border border-slate-700 cursor-pointer"
            title="Centro de Recomendaciones y Alertas (App & Telegram)"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[16px] h-[16px] px-1 rounded-full bg-rose-500 text-white text-[9px] font-bold flex items-center justify-center animate-bounce">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* GitHub Sync Button */}
          <button
            onClick={onSyncGitHub}
            disabled={isSyncing}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 hover:text-white transition border border-slate-700 font-semibold text-xs cursor-pointer"
            title="Sincronizar y Subir Cambios a GitHub (armandog451-web/trading-app)"
          >
            <GitBranch className={`w-3.5 h-3.5 text-emerald-400 ${isSyncing ? 'animate-pulse' : ''}`} />
            <span className="hidden lg:inline">{isSyncing ? 'Sync...' : 'GitHub'}</span>
          </button>

          {/* Settings Modal Button */}
          <button
            onClick={onOpenSettings}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition border border-slate-700 cursor-pointer"
            title="Configuración de Riesgo, Broker y Telegram"
          >
            <SettingsIcon className="w-4 h-4 text-emerald-400" />
          </button>
        </div>
      </div>

      {/* TIER 2: FINANCIAL METRICS TICKER STRIP */}
      <div className="bg-[#0B0F19]/90 px-3 sm:px-6 py-1.5 flex items-center justify-between gap-4 overflow-x-auto text-xs font-mono">
        <div className="flex items-center gap-4 sm:gap-6 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase text-slate-400 font-sans font-semibold">BALANCE:</span>
            <span className="font-bold text-white">
              ${equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>

          <div className="h-3.5 w-[1px] bg-slate-800" />

          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase text-slate-400 font-sans font-semibold">P&L DIARIO:</span>
            <span className={`font-bold ${dailyPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {dailyPnl >= 0 ? '+' : ''}${dailyPnl.toFixed(2)} ({dailyPnlPct >= 0 ? '+' : ''}{dailyPnlPct.toFixed(2)}%)
            </span>
          </div>

          <div className="h-3.5 w-[1px] bg-slate-800" />

          <div className="flex items-center gap-1.5">
            <span className="text-[10px] uppercase text-slate-400 font-sans font-semibold">BROKER:</span>
            <span className="font-sans font-bold text-emerald-400 flex items-center gap-1 text-[11px]">
              <ShieldCheck className="w-3.5 h-3.5" />
              {status?.mode || 'ALPACAPAPER'}
            </span>
          </div>
        </div>

        {/* Latencia Moomoo / Alpaca */}
        <div 
          onClick={onAuditLatency}
          title="Motor Maestro: Latencia en tiempo real (Umbral 50ms). Clic para auditar ahora."
          className="flex items-center gap-2 cursor-pointer group shrink-0"
        >
          <span className="text-[10px] uppercase text-slate-400 font-sans font-semibold flex items-center gap-1 group-hover:text-cyan-300 transition">
            <Network className="w-3 h-3 text-cyan-400" />
            LATENCIA:
          </span>
          <div className="flex items-center gap-1.5 text-[11px] font-bold">
            <span className={`px-1.5 py-0.2 rounded text-[10px] ${moomooLat <= 50 ? 'text-emerald-400 bg-emerald-500/10' : 'text-rose-400 bg-rose-500/10'}`}>
              M:{moomooLat > 0 ? `${moomooLat}ms` : '--'}
            </span>
            <span className={`px-1.5 py-0.2 rounded text-[10px] ${alpacaLat <= 50 ? 'text-emerald-400 bg-emerald-500/10' : 'text-amber-400 bg-amber-500/10'}`}>
              A:{alpacaLat > 0 ? `${alpacaLat}ms` : '--'}
            </span>
            {isHighLatency && (
              <span className="text-[9px] font-sans font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 px-1 rounded" title="Protocolo de Alta Latencia Activo">
                WS
              </span>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
