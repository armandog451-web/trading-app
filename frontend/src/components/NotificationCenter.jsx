import React, { useState } from 'react';
import { 
  Bell, 
  X, 
  CheckCheck, 
  Send, 
  TrendingUp, 
  Zap, 
  ShieldCheck, 
  Clock, 
  Copy, 
  Check, 
  ExternalLink,
  MessageSquareShare,
  Layers,
  Play
} from 'lucide-react';
import { markNotificationRead, markAllNotificationsRead, triggerDemoSignal, executeNotificationTrade } from '../services/api';

export default function NotificationCenter({
  isOpen,
  onClose,
  notifications = [],
  unreadCount = 0,
  onRefresh,
  selectedSymbol = 'SPY',
  onShowToast
}) {
  const [filterTab, setFilterTab] = useState('ALL'); // 'ALL' | 'STOCK' | 'OPTION'
  const [generating, setGenerating] = useState(false);
  const [executingId, setExecutingId] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  if (!isOpen) return null;

  const handleExecuteMoomoo = async (item, e) => {
    e.stopPropagation();
    setExecutingId(item.id);
    try {
      const res = await executeNotificationTrade(item.id);
      if (res.success) {
        if (onShowToast) {
          onShowToast(`🚀 ¡Orden enviada a ${res.broker}! ID: ${res.order_result?.order_id || 'OK'}`, 'success');
        }
        if (onRefresh) onRefresh();
      } else {
        if (onShowToast) onShowToast(res.error || 'Error al ejecutar orden en broker', 'error');
      }
    } catch (err) {
      if (onShowToast) onShowToast('Error de red enviando orden a Moomoo', 'error');
    } finally {
      setExecutingId(null);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      onRefresh?.();
      onShowToast?.('Todas las notificaciones marcadas como leídas', 'info');
    } catch (err) {
      console.error(err);
    }
  };

  const handleMarkOneRead = async (id, e) => {
    e.stopPropagation();
    try {
      await markNotificationRead(id);
      onRefresh?.();
    } catch (err) {
      console.error(err);
    }
  };

  const handleTriggerDemo = async (assetType) => {
    setGenerating(true);
    try {
      const res = await triggerDemoSignal(assetType, selectedSymbol);
      if (res.success) {
        const typeLabel = assetType === 'OPTION' ? 'Opciones (CALL/PUT)' : 'Acciones';
        onShowToast?.(`Recomendación de compra de ${typeLabel} generada y enviada a la App y Telegram`, 'success');
        onRefresh?.();
      }
    } catch (err) {
      onShowToast?.('Error al generar recomendación', 'error');
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = (item, e) => {
    e.stopPropagation();
    let text = '';
    if (item.asset_type === 'OPTION') {
      text = `[SEÑAL OPCIÓN] ${item.symbol} ${item.option_type} Strike $${item.strike_price} Exp: ${item.expiration_date} | Prima: $${item.premium_est} | SL: $${item.premium_stop_loss} | TP: $${item.premium_take_profit} | R:R 1:${item.risk_reward}`;
    } else {
      text = `[SEÑAL ACCIÓN] ${item.symbol} BUY @ $${item.entry_target} | SL: $${item.stop_loss} | TP: $${item.take_profit} | R:R 1:${item.risk_reward}`;
    }
    navigator.clipboard.writeText(text);
    setCopiedId(item.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredItems = notifications.filter(item => {
    if (filterTab === 'STOCK') return item.asset_type === 'STOCK';
    if (filterTab === 'OPTION') return item.asset_type === 'OPTION';
    return true;
  });

  const stockCount = notifications.filter(i => i.asset_type === 'STOCK').length;
  const optionCount = notifications.filter(i => i.asset_type === 'OPTION').length;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="w-full max-w-md bg-[#0F1420] border-l border-slate-800 h-full shadow-2xl flex flex-col animate-in slide-in-from-right duration-300"
        onClick={e => e.stopPropagation()}
      >
        {/* Panel Header */}
        <div className="p-4 border-b border-slate-800 bg-slate-900/70 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="relative p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20 text-emerald-400">
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center">
                  {unreadCount > 9 ? '9+' : unreadCount}
                </span>
              )}
            </div>
            <div>
              <h2 className="font-bold text-sm text-white flex items-center gap-2">
                Centro de Recomendaciones
                <span className="text-[10px] bg-blue-500/20 text-blue-300 border border-blue-500/30 px-1.5 py-0.5 rounded font-semibold uppercase">
                  App & Telegram
                </span>
              </h2>
              <p className="text-[11px] text-slate-400">Señales cuantitativas de compra para Acciones y Opciones</p>
            </div>
          </div>

          <div className="flex items-center gap-1">
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                title="Marcar todas como leídas"
                className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded-lg transition text-xs flex items-center gap-1"
              >
                <CheckCheck className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Quick Action Bar: Generate Demo Alerts */}
        <div className="p-3 bg-slate-950/60 border-b border-slate-800/80">
          <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
            Disparar Recomendación en Vivo ({selectedSymbol}):
          </span>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleTriggerDemo('STOCK')}
              disabled={generating}
              className="flex items-center justify-center gap-1.5 py-2 px-3 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg text-xs font-semibold transition active:scale-95 disabled:opacity-50"
            >
              <TrendingUp className="w-3.5 h-3.5" />
              <span>+ Comprar Acción</span>
            </button>

            <button
              onClick={() => handleTriggerDemo('OPTION')}
              disabled={generating}
              className="flex items-center justify-center gap-1.5 py-2 px-3 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-lg text-xs font-semibold transition active:scale-95 disabled:opacity-50"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>+ Opción (CALL/PUT)</span>
            </button>
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex border-b border-slate-800 bg-slate-900/40 px-3 pt-2 gap-1 text-xs">
          <button
            onClick={() => setFilterTab('ALL')}
            className={`pb-2 px-3 font-semibold border-b-2 transition ${
              filterTab === 'ALL'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Todas ({notifications.length})
          </button>
          <button
            onClick={() => setFilterTab('STOCK')}
            className={`pb-2 px-3 font-semibold border-b-2 transition ${
              filterTab === 'STOCK'
                ? 'border-emerald-400 text-emerald-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Acciones 📈 ({stockCount})
          </button>
          <button
            onClick={() => setFilterTab('OPTION')}
            className={`pb-2 px-3 font-semibold border-b-2 transition ${
              filterTab === 'OPTION'
                ? 'border-cyan-400 text-cyan-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Opciones ⚡ ({optionCount})
          </button>
        </div>

        {/* Notification Feed List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {filteredItems.length === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center text-center text-slate-500 p-6">
              <div className="w-12 h-12 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center mb-3 text-slate-600">
                <Bell className="w-6 h-6" />
              </div>
              <p className="text-sm font-semibold text-slate-400">Sin recomendaciones activas</p>
              <p className="text-xs text-slate-500 mt-1">
                Usa los botones superiores para emitir una recomendación de prueba o activa el Bot Runner para que las detecte automáticamente.
              </p>
            </div>
          ) : (
            filteredItems.map(item => {
              const isOption = item.asset_type === 'OPTION';
              const isUnread = !item.is_read;

              return (
                <div
                  key={item.id}
                  className={`p-3.5 rounded-xl border transition relative ${
                    isUnread
                      ? 'bg-slate-900/90 border-emerald-500/40 shadow-lg shadow-emerald-500/5'
                      : 'bg-[#121824]/60 border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  {/* Top Badge & Asset Info */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {isOption ? (
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-bold tracking-wider uppercase bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 flex items-center gap-1">
                          <Zap className="w-3 h-3" />
                          OPCIÓN {item.option_type}
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-bold tracking-wider uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                          <TrendingUp className="w-3 h-3" />
                          ACCIÓN {item.symbol}
                        </span>
                      )}

                      <span className="text-sm font-black text-white font-mono">{item.symbol}</span>

                      {isUnread && (
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" title="No leída" />
                      )}
                    </div>

                    <div className="flex items-center gap-2 text-xs">
                      {item.sent_to_telegram && (
                        <span 
                          title="Enviado al canal de Telegram"
                          className="flex items-center gap-1 text-[10px] text-blue-400 bg-blue-500/10 border border-blue-500/20 px-1.5 py-0.5 rounded font-mono"
                        >
                          <MessageSquareShare className="w-3 h-3" />
                          TG
                        </span>
                      )}
                      <span className="text-[10px] text-slate-500 font-mono">
                        {item.created_at ? new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Reciente'}
                      </span>
                    </div>
                  </div>

                  {/* Option Specific Details */}
                  {isOption ? (
                    <div className="space-y-2">
                      <div className="bg-slate-950/80 rounded-lg p-2.5 border border-slate-800/80 grid grid-cols-3 gap-2 text-center text-xs font-mono">
                        <div>
                          <span className="text-[9px] uppercase text-slate-400 block font-sans">Strike</span>
                          <span className="text-white font-bold">${item.strike_price}</span>
                        </div>
                        <div>
                          <span className="text-[9px] uppercase text-slate-400 block font-sans">Vence</span>
                          <span className="text-cyan-300 font-semibold">{item.expiration_date}</span>
                        </div>
                        <div>
                          <span className="text-[9px] uppercase text-slate-400 block font-sans">Prima Est.</span>
                          <span className="text-emerald-400 font-bold">${item.premium_est}</span>
                        </div>
                      </div>

                      <div className="grid grid-cols-3 gap-2 text-[11px] font-mono bg-slate-900/40 p-2 rounded-md border border-slate-800/40">
                        <div>
                          <span className="text-[9px] text-slate-400 block">SL Prima (-28%):</span>
                          <span className="text-rose-400 font-bold">${item.premium_stop_loss}</span>
                        </div>
                        <div>
                          <span className="text-[9px] text-slate-400 block">TP1 Prima (+50%):</span>
                          <span className="text-emerald-400 font-bold">${item.premium_take_profit}</span>
                        </div>
                        <div>
                          <span className="text-[9px] text-slate-400 block">Contratos:</span>
                          <span className="text-blue-400 font-bold">{item.contracts_or_shares} cont.</span>
                        </div>
                      </div>

                      {/* Griegas & Volatilidad Implícita Strip */}
                      <div className="grid grid-cols-4 gap-1 text-[10px] font-mono bg-cyan-950/20 p-2 rounded-md border border-cyan-500/20 text-center">
                        <div>
                          <span className="text-[8px] uppercase text-cyan-400 block font-sans">Delta (Δ)</span>
                          <span className="text-white font-bold">{item.option_type === 'CALL' ? '+0.48' : '-0.48'}</span>
                        </div>
                        <div>
                          <span className="text-[8px] uppercase text-cyan-400 block font-sans">Gamma (Γ)</span>
                          <span className="text-white font-bold">0.035</span>
                        </div>
                        <div>
                          <span className="text-[8px] uppercase text-cyan-400 block font-sans">Theta (Θ)</span>
                          <span className="text-rose-300 font-bold">-0.12</span>
                        </div>
                        <div>
                          <span className="text-[8px] uppercase text-cyan-400 block font-sans">IV Vol.</span>
                          <span className="text-amber-300 font-bold">16.8%</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* Stock Specific Details */
                    <div className="space-y-2">
                      <div className="bg-slate-950/80 rounded-lg p-2.5 border border-slate-800/80 grid grid-cols-3 gap-2 text-center text-xs font-mono">
                        <div>
                          <span className="text-[9px] uppercase text-slate-400 block font-sans">Entrada</span>
                          <span className="text-emerald-400 font-bold">${item.entry_target?.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-[9px] uppercase text-slate-400 block font-sans">Stop Loss</span>
                          <span className="text-rose-400 font-bold">${item.stop_loss?.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-[9px] uppercase text-slate-400 block font-sans">Take Profit</span>
                          <span className="text-blue-400 font-bold">${item.take_profit?.toFixed(2)}</span>
                        </div>
                      </div>

                      <div className="flex items-center justify-between text-[11px] font-mono bg-slate-900/40 p-2 rounded-md border border-slate-800/40">
                        <span className="text-slate-400">Ratio R:R: <strong className="text-emerald-400">1:{item.risk_reward}</strong></span>
                        <span className="text-slate-400">Tamaño (1%): <strong className="text-white">{item.contracts_or_shares} acc.</strong></span>
                        <span className="text-slate-400">Confluencia: <strong className="text-blue-400">{item.confluence_score}%</strong></span>
                      </div>
                    </div>
                  )}

                  {/* Rationale description */}
                  <p className="text-[11px] text-slate-400 mt-2 line-clamp-2 leading-relaxed italic bg-slate-950/40 p-1.5 rounded">
                    "{item.rationale}"
                  </p>

                  {/* Footer actions */}
                  <div className="flex items-center justify-between mt-2.5 pt-2 border-t border-slate-800/60 text-xs">
                    <span className="text-[10px] text-slate-500 font-mono">
                      {item.setup_type}
                    </span>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={(e) => handleExecuteMoomoo(item, e)}
                        disabled={executingId === item.id}
                        className="p-1 px-2.5 text-[11px] font-bold bg-emerald-500 hover:bg-emerald-400 text-slate-950 rounded transition flex items-center gap-1 shadow-md shadow-emerald-500/20 active:scale-95 disabled:opacity-50 cursor-pointer"
                        title="Enviar e ingresar esta orden directamente en Moomoo"
                      >
                        <Play className="w-3 h-3 fill-current" />
                        <span>{executingId === item.id ? 'Enviando...' : '🚀 Ejecutar en Moomoo'}</span>
                      </button>

                      <button
                        onClick={(e) => handleCopy(item, e)}
                        className="p-1 px-2 text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition flex items-center gap-1"
                        title="Copiar detalles de la señal"
                      >
                        {copiedId === item.id ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span>{copiedId === item.id ? 'Copiado' : 'Copiar'}</span>
                      </button>

                      {isUnread && (
                        <button
                          onClick={(e) => handleMarkOneRead(item.id, e)}
                          className="p-1 px-2 text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition flex items-center gap-1"
                        >
                          <Check className="w-3 h-3" />
                          <span>Leída</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Panel Footer */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/80 text-center text-[10px] text-slate-500 flex items-center justify-between px-4">
          <span>Alertas sincronizadas en vivo</span>
          <span className="flex items-center gap-1 text-emerald-400 font-medium">
            <ShieldCheck className="w-3 h-3" /> Riesgo al 1% por trade
          </span>
        </div>
      </div>
    </div>
  );
}
