import React from 'react';
import { Activity, Play, Pause, AlertOctagon, Settings as SettingsIcon, ShieldCheck, Zap, Bell, HelpCircle, GitBranch } from 'lucide-react';

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
  isSyncing = false
}) {
  const isRunning = status?.is_running || false;
  const equity = status?.account_equity || 100000;
  const dailyPnl = status?.daily_pnl || 0;
  const dailyPnlPct = status?.daily_pnl_pct || 0;
  const circuitBreaker = status?.circuit_breaker_tripped || false;

  return (
    <header className="border-b border-slate-800 bg-[#0E131F]/90 backdrop-blur sticky top-0 z-40 px-6 py-3">
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand & Tabs */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <span className="font-bold text-lg tracking-tight text-white flex items-center gap-2">
                TradePulse <span className="text-[10px] uppercase tracking-wider bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/30 font-semibold">Top-Down Day Trader</span>
              </span>
              <p className="text-xs text-slate-400">Motor Cuantitativo Intraday & Bracket Orders</p>
            </div>
          </div>

          <nav className="flex items-center bg-slate-900/80 p-1 rounded-lg border border-slate-800">
            <button
              onClick={() => setActiveTab('cockpit')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${activeTab === 'cockpit' ? 'bg-emerald-500 text-slate-950 font-semibold shadow' : 'text-slate-400 hover:text-white'}`}
            >
              Cockpit & Gráfico
            </button>
            <button
              onClick={() => setActiveTab('backtest')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${activeTab === 'backtest' ? 'bg-emerald-500 text-slate-950 font-semibold shadow' : 'text-slate-400 hover:text-white'}`}
            >
              Backtest Studio
            </button>
          </nav>
        </div>

        {/* Financial Metrics Strip */}
        <div className="flex items-center gap-6 bg-slate-900/60 border border-slate-800/80 px-4 py-1.5 rounded-lg">
          <div>
            <span className="text-[10px] uppercase text-slate-400 block font-medium">Balance Total (Equity)</span>
            <span className="text-sm font-bold text-white font-mono">
              ${equity.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>

          <div className="h-6 w-[1px] bg-slate-800" />

          <div>
            <span className="text-[10px] uppercase text-slate-400 block font-medium">P&L Diario (Intraday)</span>
            <span className={`text-sm font-bold font-mono ${dailyPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {dailyPnl >= 0 ? '+' : ''}${dailyPnl.toFixed(2)} ({dailyPnlPct >= 0 ? '+' : ''}{dailyPnlPct.toFixed(2)}%)
            </span>
          </div>

          <div className="h-6 w-[1px] bg-slate-800" />

          <div>
            <span className="text-[10px] uppercase text-slate-400 block font-medium">Modo Broker</span>
            <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" />
              {status?.mode || 'Alpaca Paper'}
            </span>
          </div>
        </div>

        {/* Action Controls & Bot Toggle */}
        <div className="flex items-center gap-3">
          {circuitBreaker && (
            <div className="bg-rose-500/20 text-rose-400 border border-rose-500/40 px-2.5 py-1 rounded text-xs font-semibold flex items-center gap-1.5 animate-pulse">
              <AlertOctagon className="w-4 h-4" />
              CIRCUIT BREAKER ACTIVO
            </div>
          )}

          {/* Test Order Button */}
          <button
            onClick={onTriggerTestTrade}
            title="Enviar Bracket Order de prueba para verificar ejecución"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 transition"
          >
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden sm:inline">Test Trade</span>
          </button>

          {/* Bot Start / Stop Switch */}
          <button
            onClick={onToggleBot}
            disabled={circuitBreaker}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-xs tracking-wide transition shadow-lg ${
              isRunning
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30'
                : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold shadow-emerald-500/20'
            }`}
          >
            {isRunning ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                <Pause className="w-4 h-4" /> PAUSAR BOT
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" /> ACTIVAR BOT
              </>
            )}
          </button>

          {/* PANIC BUTTON */}
          <button
            onClick={onPanic}
            title="Botón de Pánico: Cancelar todas las órdenes y cerrar todas las posiciones inmediatamente"
            className="flex items-center gap-1.5 px-3.5 py-2 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-lg transition shadow-lg shadow-rose-600/30 active:scale-95 cursor-pointer"
          >
            <AlertOctagon className="w-4 h-4" />
            <span className="hidden sm:inline">PÁNICO</span>
          </button>

          {/* Help Center Button */}
          <button
            onClick={onOpenHelp}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 transition border border-emerald-500/30 font-semibold text-xs cursor-pointer"
            title="Centro de Ayuda y Guía del Sistema"
          >
            <HelpCircle className="w-4 h-4 text-emerald-400" />
            <span className="hidden sm:inline">Ayuda</span>
          </button>

          {/* Notifications Center Bell Button */}
          <button
            onClick={onOpenNotifications}
            className="relative p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition border border-slate-700 cursor-pointer"
            title="Centro de Recomendaciones y Alertas (App & Telegram)"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center animate-bounce">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* GitHub Sync Button */}
          <button
            onClick={onSyncGitHub}
            disabled={isSyncing}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 hover:text-white transition border border-slate-700 font-semibold text-xs cursor-pointer"
            title="Sincronizar y Subir Cambios a GitHub (armandog451-web/trading-app)"
          >
            <GitBranch className={`w-4 h-4 text-emerald-400 ${isSyncing ? 'animate-pulse' : ''}`} />
            <span className="hidden lg:inline">{isSyncing ? 'Sincronizando...' : 'GitHub'}</span>
          </button>

          {/* Settings Modal Button */}
          <button
            onClick={onOpenSettings}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition border border-slate-700 cursor-pointer"
            title="Configuración de Riesgo, Broker y Telegram"
          >
            <SettingsIcon className="w-4 h-4" />
          </button>
        </div>

      </div>
    </header>
  );
}

