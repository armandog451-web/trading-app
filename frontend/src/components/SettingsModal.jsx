import React, { useState, useEffect } from 'react';
import { X, Key, Shield, Bell, Save, CheckCircle, Send, AlertCircle, ExternalLink, Server, Cpu } from 'lucide-react';
import {
  fetchSettings,
  updateRiskSettings,
  updateBrokerSettings,
  updateTelegramSettings,
  testTelegramConnection,
  testBrokerConnection,
  testMoomooConnection
} from '../services/api';

export default function SettingsModal({ isOpen, onClose }) {
  // Active Broker selection
  const [activeBroker, setActiveBroker] = useState('ALPACA'); // ALPACA, MOOMOO, SIMULATOR
  const [autoExecuteTrades, setAutoExecuteTrades] = useState(false); // false = Notification Only Mode

  // Alpaca state
  const [apiKey, setApiKey] = useState('');
  const [secretKey, setSecretKey] = useState('');
  const [isPaper, setIsPaper] = useState(true);
  const [testingBroker, setTestingBroker] = useState(false);
  const [brokerFeedback, setBrokerFeedback] = useState(null);

  // Moomoo state
  const [moomooHost, setMoomooHost] = useState('127.0.0.1');
  const [moomooPort, setMoomooPort] = useState(11111);
  const [moomooTradePwd, setMoomooTradePwd] = useState('');
  const [moomooPaper, setMoomooPaper] = useState(true);
  const [moomooAccId, setMoomooAccId] = useState(0);
  const [testingMoomoo, setTestingMoomoo] = useState(false);
  const [moomooFeedback, setMoomooFeedback] = useState(null);

  // Risk state
  const [maxDailyLoss, setMaxDailyLoss] = useState(2.0);
  const [riskPerTrade, setRiskPerTrade] = useState(1.0);
  const [minRr, setMinRr] = useState(2.0);
  const [squareOffTime, setSquareOffTime] = useState('15:50');
  const [maxPositions, setMaxPositions] = useState(3);

  // Telegram state
  const [telegramToken, setTelegramToken] = useState('');
  const [telegramChatId, setTelegramChatId] = useState('');
  const [notifyMarketClose, setNotifyMarketClose] = useState(false);
  const [testingTg, setTestingTg] = useState(false);
  const [tgFeedback, setTgFeedback] = useState(null);

  const [savedMsg, setSavedMsg] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchSettings().then(cfg => {
        if (cfg) {
          setMaxDailyLoss(cfg.risk.max_daily_loss_pct);
          setRiskPerTrade(cfg.risk.risk_per_trade_pct);
          setMinRr(cfg.risk.min_rr_ratio);
          setSquareOffTime(cfg.risk.auto_square_off_time);
          setMaxPositions(cfg.risk.max_open_positions);

          if (cfg.broker) {
            if (cfg.broker.active_broker) setActiveBroker(cfg.broker.active_broker);
            if (cfg.broker.auto_execute_trades !== undefined) setAutoExecuteTrades(cfg.broker.auto_execute_trades);
            setIsPaper(cfg.broker.alpaca_paper ?? true);
            if (cfg.broker.alpaca_api_key) setApiKey(cfg.broker.alpaca_api_key);
            if (cfg.broker.moomoo_host) setMoomooHost(cfg.broker.moomoo_host);
            if (cfg.broker.moomoo_port) setMoomooPort(cfg.broker.moomoo_port);
            if (cfg.broker.moomoo_paper !== undefined) setMoomooPaper(cfg.broker.moomoo_paper);
            if (cfg.broker.moomoo_acc_id !== undefined) setMoomooAccId(cfg.broker.moomoo_acc_id);
          }


          if (cfg.notifications) {
            setTelegramToken(cfg.notifications.telegram_bot_token || '');
            setTelegramChatId(cfg.notifications.telegram_chat_id || '');
            setNotifyMarketClose(Boolean(cfg.notifications.notify_market_close));
          }
        }
      }).catch(console.error);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleTestBroker = async () => {
    setTestingBroker(true);
    setBrokerFeedback(null);
    try {
      const res = await testBrokerConnection({
        alpaca_api_key: apiKey,
        alpaca_secret_key: secretKey,
        alpaca_paper: isPaper
      });
      if (res.success) {
        setBrokerFeedback({ type: 'success', text: res.message });
      } else {
        setBrokerFeedback({ type: 'error', text: res.error || 'Error conectando con Alpaca' });
      }
    } catch (err) {
      setBrokerFeedback({ type: 'error', text: 'Error inesperado probando conexión con Alpaca' });
    } finally {
      setTestingBroker(false);
    }
  };

  const handleTestMoomoo = async () => {
    setTestingMoomoo(true);
    setMoomooFeedback(null);
    try {
      const res = await testMoomooConnection({
        moomoo_host: moomooHost,
        moomoo_port: Number(moomooPort),
        moomoo_trade_pwd: moomooTradePwd,
        moomoo_paper: moomooPaper,
        moomoo_acc_id: Number(moomooAccId)
      });
      if (res.success) {
        setMoomooFeedback({ type: 'success', text: res.message });
      } else {
        setMoomooFeedback({ type: 'error', text: res.error || 'Error conectando con Moomoo OpenD' });
      }
    } catch (err) {
      setMoomooFeedback({ type: 'error', text: 'Error de red al intentar conectar con Moomoo OpenD' });
    } finally {
      setTestingMoomoo(false);
    }
  };

  const handleTestTelegram = async () => {
    setTestingTg(true);
    setTgFeedback(null);
    try {
      const res = await testTelegramConnection(telegramToken, telegramChatId);
      if (res.success) {
        setTgFeedback({ type: 'success', text: `¡Conexión exitosa! ${res.message}` });
      } else {
        setTgFeedback({ type: 'error', text: res.error || 'Fallo de conexión con Telegram' });
      }
    } catch (err) {
      setTgFeedback({ type: 'error', text: 'Error inesperado probando conexión' });
    } finally {
      setTestingTg(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    try {
      await updateRiskSettings({
        max_daily_loss_pct: Number(maxDailyLoss),
        risk_per_trade_pct: Number(riskPerTrade),
        min_rr_ratio: Number(minRr),
        auto_square_off_time: squareOffTime,
        max_open_positions: Number(maxPositions)
      });

      await updateBrokerSettings({
        active_broker: activeBroker,
        auto_execute_trades: autoExecuteTrades,
        alpaca_api_key: apiKey,
        alpaca_secret_key: secretKey,
        alpaca_paper: isPaper,
        moomoo_host: moomooHost,
        moomoo_port: Number(moomooPort),
        moomoo_trade_pwd: moomooTradePwd,
        moomoo_paper: moomooPaper,
        moomoo_acc_id: Number(moomooAccId)
      });

      await updateTelegramSettings(telegramToken, telegramChatId, notifyMarketClose);

      setSavedMsg(`Configuraciones guardadas. Broker: ${activeBroker} | Modo: ${autoExecuteTrades ? 'Ejecución Automática' : 'Solo Notificaciones'}`);
      setTimeout(() => setSavedMsg(''), 3500);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-[#121824] border border-slate-800 rounded-2xl w-full max-w-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95">
        
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-900/50">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-emerald-400" />
            <h2 className="font-bold text-base text-white">Configuración del Bot & Brokers</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSave} className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {savedMsg && (
            <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-3 rounded-lg text-xs flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              {savedMsg}
            </div>
          )}

          {/* Section: Active Broker Selector */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Server className="w-4 h-4 text-cyan-400" />
              Selección de Broker Activo
            </h3>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setActiveBroker('ALPACA')}
                className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition cursor-pointer ${
                  activeBroker === 'ALPACA'
                    ? 'bg-emerald-500/15 border-emerald-500/50 text-emerald-400 shadow-md'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                <Key className="w-4 h-4" />
                <span>Alpaca Markets</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveBroker('MOOMOO')}
                className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition cursor-pointer ${
                  activeBroker === 'MOOMOO'
                    ? 'bg-amber-500/15 border-amber-500/50 text-amber-400 shadow-md'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                <Server className="w-4 h-4" />
                <span>Moomoo Open API</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveBroker('SIMULATOR')}
                className={`p-3 rounded-xl border text-xs font-semibold flex flex-col items-center gap-1.5 transition cursor-pointer ${
                  activeBroker === 'SIMULATOR'
                    ? 'bg-blue-500/15 border-blue-500/50 text-blue-400 shadow-md'
                    : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                <Cpu className="w-4 h-4" />
                <span>Simulador Local</span>
              </button>
            </div>

            {/* Mode Toggle: Signal Only vs Auto Trade */}
            <div className="bg-slate-900/80 p-3 rounded-xl border border-slate-800/80 space-y-2">
              <label className="text-[11px] font-bold text-slate-300 block uppercase tracking-wider">
                Modo de Acción al Encontrar Oportunidades:
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setAutoExecuteTrades(false)}
                  className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 cursor-pointer transition ${
                    !autoExecuteTrades
                      ? 'bg-cyan-500/15 border-cyan-500/50 text-cyan-400 shadow-sm'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Bell className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Modo Solo Notificaciones (Moomoo / Telegram)</span>
                </button>

                <button
                  type="button"
                  onClick={() => setAutoExecuteTrades(true)}
                  className={`p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-center gap-2 cursor-pointer transition ${
                    autoExecuteTrades
                      ? 'bg-emerald-500/15 border-emerald-500/50 text-emerald-400 shadow-sm'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Ejecución Automática Directa</span>
                </button>
              </div>

              <p className="text-[11px] text-slate-400 leading-relaxed pt-1">
                {!autoExecuteTrades
                  ? '💡 MODO NOTIFICACIONES ACTIVO: El bot analizará el mercado y enviará la recomendación completa de compra/venta (Acciones y Opciones) a Telegram y a la App SIN colocar la orden automáticamente en Moomoo.'
                  : '⚠️ EJECUCIÓN AUTOMÁTICA ACTIVA: El bot enviará la orden Bracket directamente a tu broker al confirmar la señal.'}
              </p>
            </div>
          </div>


          {/* Section: Risk Engine */}
          <div className="pt-3 border-t border-slate-800">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-blue-400" />
              Parámetros de Riesgo Institucional
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] text-slate-300 block mb-1">Circuit Breaker (Pérdida Diaria Máx %)</label>
                <input
                  type="number"
                  step="0.5"
                  value={maxDailyLoss}
                  onChange={e => setMaxDailyLoss(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 text-xs font-mono"
                />
              </div>

              <div>
                <label className="text-[11px] text-slate-300 block mb-1">Riesgo por Trade (% Capital)</label>
                <input
                  type="number"
                  step="0.25"
                  value={riskPerTrade}
                  onChange={e => setRiskPerTrade(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 text-xs font-mono"
                />
              </div>

              <div>
                <label className="text-[11px] text-slate-300 block mb-1">Ratio R:R Mínimo Exigido</label>
                <input
                  type="number"
                  step="0.5"
                  value={minRr}
                  onChange={e => setMinRr(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 text-xs font-mono"
                />
              </div>

              <div>
                <label className="text-[11px] text-slate-300 block mb-1">Cierre Intraday Forzoso (EST)</label>
                <input
                  type="text"
                  value={squareOffTime}
                  onChange={e => setSquareOffTime(e.target.value)}
                  placeholder="15:50"
                  className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 text-xs font-mono"
                />
              </div>
            </div>
          </div>

          {/* Conditional Broker Section: Alpaca */}
          {activeBroker === 'ALPACA' && (
            <div className="pt-3 border-t border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Key className="w-4 h-4 text-emerald-400" />
                  Credenciales de Alpaca Markets
                </h3>
                <span className={`text-[10px] px-2 py-0.5 rounded font-semibold border ${
                  isPaper
                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                    : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                }`}>
                  {isPaper ? 'Modo Paper' : 'Modo Real'}
                </span>
              </div>

              <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80 text-[11px] text-slate-400 space-y-1">
                <p className="font-semibold text-slate-300">💡 Generar API Keys en Alpaca:</p>
                <p>Ingresa a <a href="https://app.alpaca.markets" target="_blank" rel="noreferrer" className="text-emerald-400 underline font-mono inline-flex items-center gap-0.5">app.alpaca.markets <ExternalLink className="w-3 h-3" /></a> en Paper o Live Trading.</p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-3 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800 text-xs">
                  <input
                    type="checkbox"
                    id="paperMode"
                    checked={isPaper}
                    onChange={e => setIsPaper(e.target.checked)}
                    className="rounded text-emerald-500 focus:ring-emerald-400 cursor-pointer"
                  />
                  <label htmlFor="paperMode" className="text-slate-200 cursor-pointer font-medium">
                    Usar cuenta <strong>Paper Trading</strong> (Simulado sin riesgo real)
                  </label>
                </div>

                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Alpaca API Key ID</label>
                  <input
                    type="text"
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    placeholder={isPaper ? "PK..." : "AK..."}
                    className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 text-xs font-mono"
                  />
                </div>

                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Alpaca Secret Key</label>
                  <input
                    type="password"
                    value={secretKey}
                    onChange={e => setSecretKey(e.target.value)}
                    placeholder="••••••••••••••••••••••••••••"
                    className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 text-xs font-mono"
                  />
                </div>

                <div className="pt-1">
                  <button
                    type="button"
                    onClick={handleTestBroker}
                    disabled={testingBroker || !apiKey || !secretKey}
                    className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition active:scale-95 cursor-pointer"
                  >
                    <Key className="w-3.5 h-3.5 text-emerald-400" />
                    <span>{testingBroker ? 'Verificando Alpaca...' : 'Probar Conexión Alpaca'}</span>
                  </button>

                  {brokerFeedback && (
                    <div className={`mt-2 p-2.5 rounded-lg text-xs flex items-center gap-2 border ${
                      brokerFeedback.type === 'success'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                    }`}>
                      {brokerFeedback.type === 'success' ? <CheckCircle className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
                      <span>{brokerFeedback.text}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Conditional Broker Section: Moomoo */}
          {activeBroker === 'MOOMOO' && (
            <div className="pt-3 border-t border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Server className="w-4 h-4 text-amber-400" />
                  Conexión Moomoo Open API (Gateway Local FutuOpenD / MoomooOpenD)
                </h3>
                <span className={`text-[10px] px-2 py-0.5 rounded font-semibold border ${
                  moomooPaper
                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                    : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                }`}>
                  {moomooPaper ? 'Moomoo Paper' : 'Moomoo Real'}
                </span>
              </div>

              <div className="bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80 text-[11px] text-slate-400 space-y-1">
                <p className="font-semibold text-slate-300">💡 Instrucciones Moomoo OpenD:</p>
                <p>1. Descarga e inicia <strong>Moomoo OpenD</strong> o <strong>FutuOpenD</strong> en tu computadora.</p>
                <p>2. Abre el puerto local (por defecto <code className="bg-slate-800 px-1 py-0.5 rounded text-white font-mono">11111</code>) y desactiva el cifrado SSL en OpenD para TCP local.</p>
                <p>3. Inicia sesión en la app de Moomoo y genera tu Contraseña de Trading si utilizas cuenta Real.</p>
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-3 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800 text-xs">
                  <input
                    type="checkbox"
                    id="moomooPaperMode"
                    checked={moomooPaper}
                    onChange={e => setMoomooPaper(e.target.checked)}
                    className="rounded text-amber-500 focus:ring-amber-400 cursor-pointer"
                  />
                  <label htmlFor="moomooPaperMode" className="text-slate-200 cursor-pointer font-medium">
                    Usar cuenta <strong>Moomoo Paper Trading</strong> (Simulado en Moomoo)
                  </label>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] text-slate-300 block mb-1">Host Gateway OpenD</label>
                    <input
                      type="text"
                      value={moomooHost}
                      onChange={e => setMoomooHost(e.target.value)}
                      placeholder="127.0.0.1"
                      className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 text-xs font-mono"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] text-slate-300 block mb-1">Puerto TCP</label>
                    <input
                      type="number"
                      value={moomooPort}
                      onChange={e => setMoomooPort(e.target.value)}
                      placeholder="11111"
                      className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 text-xs font-mono"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-[11px] text-slate-300 block mb-1">Contraseña de Trading (Unlock Password)</label>
                  <input
                    type="password"
                    value={moomooTradePwd}
                    onChange={e => setMoomooTradePwd(e.target.value)}
                    placeholder="Contraseña de 6 dígitos de Moomoo"
                    className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 text-xs font-mono"
                  />
                </div>

                <div className="pt-1">
                  <button
                    type="button"
                    onClick={handleTestMoomoo}
                    disabled={testingMoomoo}
                    className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition active:scale-95 cursor-pointer"
                  >
                    <Server className="w-3.5 h-3.5 text-amber-400" />
                    <span>{testingMoomoo ? 'Probando Moomoo OpenD...' : 'Probar Conexión Moomoo OpenD'}</span>
                  </button>

                  {moomooFeedback && (
                    <div className={`mt-2 p-2.5 rounded-lg text-xs flex items-center gap-2 border ${
                      moomooFeedback.type === 'success'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                    }`}>
                      {moomooFeedback.type === 'success' ? <CheckCircle className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
                      <span>{moomooFeedback.text}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Conditional Broker Section: Simulator */}
          {activeBroker === 'SIMULATOR' && (
            <div className="pt-3 border-t border-slate-800">
              <div className="bg-blue-500/10 border border-blue-500/30 text-blue-300 p-3.5 rounded-xl text-xs space-y-1">
                <p className="font-bold flex items-center gap-1.5">
                  <Cpu className="w-4 h-4 text-blue-400" />
                  Modo Simulador Local Activo
                </p>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  Las ejecuciones de acciones y opciones se procesarán con fondos virtuales de $100,000 dentro del motor del sistema, sin requerir conexión a brokers externos. ideal para pruebas y desarrollo.
                </p>
              </div>
            </div>
          )}

          {/* Section: Notifications */}
          <div className="pt-3 border-t border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <Bell className="w-4 h-4 text-purple-400" />
                Alertas Móviles en Telegram
              </h3>
              <span className="text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded font-semibold">
                Acciones & Opciones
              </span>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-[11px] text-slate-300 block mb-1">Telegram Bot Token</label>
                <input
                  type="password"
                  value={telegramToken}
                  onChange={e => setTelegramToken(e.target.value)}
                  placeholder="Ej: 7123456789:AAHk..._zyx"
                  className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 text-xs font-mono"
                />
              </div>

              <div>
                <label className="text-[11px] text-slate-300 block mb-1">Telegram Chat ID</label>
                <input
                  type="text"
                  value={telegramChatId}
                  onChange={e => setTelegramChatId(e.target.value)}
                  placeholder="Ej: 123456789"
                  className="w-full bg-slate-900 border border-slate-700 text-white rounded-lg p-2 text-xs font-mono"
                />
              </div>

              <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-slate-700/60">
                <div>
                  <span className="text-xs text-slate-200 font-medium block">Notificaciones de Cierre de Bolsa</span>
                  <span className="text-[10px] text-slate-400 block">Alertas de final de sesión y cierre forzoso (15:50 EST)</span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={notifyMarketClose}
                    onChange={e => setNotifyMarketClose(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-8 h-4 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-purple-600"></div>
                </label>
              </div>

              <div className="pt-1">
                <button
                  type="button"
                  onClick={handleTestTelegram}
                  disabled={testingTg || !telegramToken || !telegramChatId}
                  className="flex items-center gap-1.5 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition active:scale-95 cursor-pointer"
                >
                  <Send className="w-3.5 h-3.5 text-blue-400" />
                  <span>{testingTg ? 'Verificando Telegram...' : 'Probar Conexión Telegram'}</span>
                </button>

                {tgFeedback && (
                  <div className={`mt-2 p-2.5 rounded-lg text-xs flex items-center gap-2 border ${
                    tgFeedback.type === 'success'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  }`}>
                    {tgFeedback.type === 'success' ? <CheckCircle className="w-4 h-4 shrink-0" /> : <AlertCircle className="w-4 h-4 shrink-0" />}
                    <span>{tgFeedback.text}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Buttons */}
          <div className="pt-4 border-t border-slate-800 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs rounded-lg text-slate-400 hover:text-white transition bg-slate-800 cursor-pointer"
            >
              Cerrar
            </button>
            <button
              type="submit"
              className="flex items-center gap-2 px-5 py-2 text-xs rounded-lg font-bold bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition shadow-lg shadow-emerald-500/20 cursor-pointer"
            >
              <Save className="w-4 h-4" /> Guardar Cambios
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
