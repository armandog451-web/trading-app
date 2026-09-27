import React, { useState, useEffect, useRef } from 'react';
import TopNavbar from './components/TopNavbar';
import MacroRadarCard from './components/MacroRadarCard';
import SentimentGauge from './components/SentimentGauge';
import TradingViewChart from './components/TradingViewChart';
import ActivePositionsTable from './components/ActivePositionsTable';
import PreMarketScreener from './components/PreMarketScreener';
import BacktestStudio from './components/BacktestStudio';
import SettingsModal from './components/SettingsModal';
import NotificationCenter from './components/NotificationCenter';
import HelpModal from './components/HelpModal';

import {
  fetchDashboardStatus,
  startBot,
  stopBot,
  triggerPanic,
  fetchActivePositions,
  fetchTradeHistory,
  triggerTestTrade,
  fetchMacroFactors,
  fetchSentimentFactors,
  fetchScreenerStocks,
  fetchTechnicalData,
  fetchNotifications,
  syncGitHub,
  fetchLatencyAudit
} from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('cockpit');
  const [selectedSymbol, setSelectedSymbol] = useState('SPY');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [isSyncingGit, setIsSyncingGit] = useState(false);

  const [status, setStatus] = useState(null);
  const [positions, setPositions] = useState([]);
  const [tradeHistory, setTradeHistory] = useState([]);
  const [macroData, setMacroData] = useState(null);
  const [sentimentData, setSentimentData] = useState(null);
  const [screenerStocks, setScreenerStocks] = useState([]);
  const [technicalData, setTechnicalData] = useState(null);

  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const lastUnreadCountRef = useRef(0);

  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  // Cargar notificaciones
  const loadNotifications = async () => {
    try {
      const data = await fetchNotifications();
      if (data) {
        setNotifications(data.items || []);
        setUnreadCount(data.unread_count || 0);

        // Si hay una nueva alerta que antes no estaba, notificar con toast
        if (data.unread_count > lastUnreadCountRef.current && data.items?.length > 0) {
          const latest = data.items[0];
          const typeLabel = latest.asset_type === 'OPTION' ? `OPCIÓN (${latest.option_type} $${latest.strike_price})` : `ACCIÓN (${latest.symbol})`;
          showToast(`⚡ NUEVA RECOMENDACIÓN: ${typeLabel} enviada a App y Telegram`, 'success');
        }
        lastUnreadCountRef.current = data.unread_count || 0;
      }
    } catch (err) {
      console.error('Error cargando notificaciones:', err);
    }
  };

  // Cargar datos periódicamente
  const refreshData = async () => {
    try {
      const [st, pos, hist, mac, sent, scr] = await Promise.all([
        fetchDashboardStatus(),
        fetchActivePositions(),
        fetchTradeHistory(),
        fetchMacroFactors(),
        fetchSentimentFactors(),
        fetchScreenerStocks(),
      ]);

      setStatus(st);
      setPositions(pos);
      setTradeHistory(hist);
      setMacroData(mac);
      setSentimentData(sent);
      setScreenerStocks(scr);
      loadNotifications();
    } catch (err) {
      console.error('Error actualizando dashboard:', err);
    }
  };


  // Cargar datos técnicos del símbolo seleccionado
  const refreshTechnical = async (sym) => {
    try {
      const tech = await fetchTechnicalData(sym);
      setTechnicalData(tech);
    } catch (err) {
      console.error('Error cargando datos técnicos:', err);
    }
  };

  useEffect(() => {
    refreshData();
    refreshTechnical(selectedSymbol);

    const interval = setInterval(() => {
      refreshData();
      refreshTechnical(selectedSymbol);
    }, 4000);

    return () => clearInterval(interval);
  }, [selectedSymbol]);

  const handleToggleBot = async () => {
    try {
      if (status?.is_running) {
        const res = await stopBot();
        showToast('Bot pausado correctamente', 'warn');
      } else {
        const res = await startBot();
        showToast('Bot activado en modo Day Trading Top-Down', 'success');
      }
      refreshData();
    } catch (err) {
      showToast('Error al cambiar estado del bot', 'error');
    }
  };

  const handlePanic = async () => {
    if (window.confirm('⚠️ BOTÓN DE PÁNICO: ¿Confirmas cancelar todas las órdenes y cerrar todas las posiciones abiertas en Alpaca de inmediato?')) {
      try {
        const res = await triggerPanic();
        showToast(res.message || 'Todas las posiciones cerradas de emergencia', 'warn');
        refreshData();
      } catch (err) {
        showToast('Error ejecutando orden de pánico', 'error');
      }
    }
  };

  const handleTestTrade = async () => {
    try {
      const res = await triggerTestTrade(selectedSymbol);
      showToast(`Bracket Order de prueba ejecutada para ${selectedSymbol}`, 'success');
      refreshData();
    } catch (err) {
      showToast('Error al enviar trade de prueba', 'error');
    }
  };

  const handleSyncGitHub = async () => {
    setIsSyncingGit(true);
    showToast('Sincronizando cambios con GitHub...', 'info');
    try {
      const res = await syncGitHub();
      if (res.success) {
        showToast(res.message, 'success');
      } else {
        showToast(res.message || 'Aviso de sincronización', 'warn');
      }
    } catch (err) {
      showToast('Error sincronizando con GitHub: ' + err.message, 'error');
    } finally {
      setIsSyncingGit(false);
    }
  };

  const handleAuditLatency = async () => {
    showToast('Ejecutando auditoría de latencia de red...', 'info');
    try {
      const rep = await fetchLatencyAudit();
      const statusText = rep.high_latency_mode ? 'ALERTA: Umbral 50ms superado. Protocolo de emergencia WebSocket activo.' : 'ÓPTIMO: Latencia dentro del umbral (<50ms).';
      const type = rep.high_latency_mode ? 'warn' : 'success';
      showToast(`Moomoo: ${rep.opend_latency_ms}ms | Alpaca: ${rep.alpaca_latency_ms}ms — ${statusText}`, type);
      refreshData();
    } catch (err) {
      showToast('Error al auditar latencia: ' + err.message, 'error');
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0E14] text-slate-100 flex flex-col selection:bg-emerald-500 selection:text-slate-950">
      
      {/* Toast Notification Bar */}
      {toast && (
        <div className={`fixed top-16 right-6 z-50 px-4 py-2.5 rounded-lg text-xs font-semibold shadow-2xl transition-all border ${
          toast.type === 'success'
            ? 'bg-emerald-500 text-slate-950 border-emerald-400'
            : toast.type === 'warn'
            ? 'bg-amber-500 text-slate-950 border-amber-400'
            : 'bg-rose-600 text-white border-rose-500'
        }`}>
          {toast.message}
        </div>
      )}

      {/* Top Navbar */}
      <TopNavbar
        status={status}
        onToggleBot={handleToggleBot}
        onPanic={handlePanic}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenNotifications={() => setIsNotificationsOpen(true)}
        onOpenHelp={() => setIsHelpOpen(true)}
        unreadCount={unreadCount}
        onTriggerTestTrade={handleTestTrade}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onSyncGitHub={handleSyncGitHub}
        isSyncing={isSyncingGit}
        onAuditLatency={handleAuditLatency}
      />

      {/* Main Workspace */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {activeTab === 'cockpit' ? (
          <>
            {/* Capas Top-Down Superiores (Macro & Sentimiento) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <MacroRadarCard macroData={macroData} />
              <SentimentGauge sentimentData={sentimentData} />
            </div>

            {/* Capa 4 & Gráfico Interactivo de Velas con VWAP */}
            <TradingViewChart
              symbol={selectedSymbol}
              onSelectSymbol={(sym) => {
                setSelectedSymbol(sym);
                refreshTechnical(sym);
              }}
              technicalData={technicalData}
              availableSymbols={['SPY', 'QQQ', 'NVDA', 'TSLA', 'AMD', 'AAPL']}
            />

            {/* Capa 2: Escáner Pre-Market */}
            <PreMarketScreener
              screenerStocks={screenerStocks}
              selectedSymbol={selectedSymbol}
              onSelectSymbol={(sym) => {
                setSelectedSymbol(sym);
                refreshTechnical(sym);
              }}
            />

            {/* Capa 5: Posiciones Abiertas & Historial de Ejecución */}
            <ActivePositionsTable
              positions={positions}
              tradeHistory={tradeHistory}
            />
          </>
        ) : (
          /* Backtesting Studio View */
          <BacktestStudio />
        )}
      </main>

      {/* Notification Center Drawer */}
      <NotificationCenter
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
        notifications={notifications}
        unreadCount={unreadCount}
        onRefresh={loadNotifications}
        selectedSymbol={selectedSymbol}
        onShowToast={showToast}
      />

      {/* Help Modal */}
      <HelpModal
        isOpen={isHelpOpen}
        onClose={() => setIsHelpOpen(false)}
      />

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />


      {/* Footer */}
      <footer className="border-t border-slate-800/80 px-6 py-4 text-center text-xs text-slate-500">
        TradePulse Quantitative Engine v1.0 • Arquitectura Top-Down: Macro, COT, Put/Call, Fundamentales, Liquidez y R:R
      </footer>
    </div>
  );
}
