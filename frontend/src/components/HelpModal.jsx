import React, { useState } from 'react';
import {
  HelpCircle,
  X,
  BookOpen,
  TrendingUp,
  FlaskConical,
  Bell,
  Settings,
  ShieldAlert,
  Zap,
  Search,
  CheckCircle2,
  DollarSign,
  Activity,
  BarChart2,
  Lock,
  Smartphone
} from 'lucide-react';

export default function HelpModal({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('cockpit');
  const [searchTerm, setSearchTerm] = useState('');

  if (!isOpen) return null;

  const sections = [
    {
      id: 'cockpit',
      title: 'Panel Principal (Cockpit)',
      icon: TrendingUp,
      color: 'text-emerald-400',
      badge: 'Vista 360° Top-Down',
      content: (
        <div className="space-y-6 text-sm text-slate-300">
          <p className="text-slate-200 font-medium leading-relaxed">
            El <strong>Cockpit Top-Down</strong> es el centro de control cuantitativo donde el bot analiza en tiempo real todas las capas del mercado antes de tomar decisiones de trading.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-emerald-400 font-semibold">
                <Activity className="w-4 h-4" />
                <span>1. Macro Radar & Sentimiento</span>
              </div>
              <p className="text-xs text-slate-400">
                Monitorea tipos de interés, inflación (FRED), el índice de Miedo y Codicia (Fear & Greed) y el Put/Call Ratio para determinar la dirección macro del mercado.
              </p>
            </div>

            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-sky-400 font-semibold">
                <BarChart2 className="w-4 h-4" />
                <span>2. Gráfico Interactivo + VWAP</span>
              </div>
              <p className="text-xs text-slate-400">
                Muestra la acción del precio en velas japonesas con la línea VWAP (Precio Promedio Ponderado por Volumen). Sirve para identificar si la acción está sobrecomprada o sobrevendida institucionalmente.
              </p>
            </div>

            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-amber-400 font-semibold">
                <Zap className="w-4 h-4" />
                <span>3. Escáner Pre-Market</span>
              </div>
              <p className="text-xs text-slate-400">
                Filtra automáticamente las acciones más volátiles y con mayor volumen inusual antes de la apertura de la bolsa de Nueva York.
              </p>
            </div>

            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-purple-400 font-semibold">
                <DollarSign className="w-4 h-4" />
                <span>4. Tabla de Posiciones Activas</span>
              </div>
              <p className="text-xs text-slate-400">
                Rastrea tus ejecuciones abiertas en el broker, calculando tu Ganancia/Pérdida (P&L) en vivo, precio de entrada, Stop Loss y Take Profit.
              </p>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'backtest',
      title: 'Backtest Studio (Simulación)',
      icon: FlaskConical,
      color: 'text-sky-400',
      badge: 'Validación Histórica',
      content: (
        <div className="space-y-6 text-sm text-slate-300">
          <p className="text-slate-200 font-medium leading-relaxed">
            El <strong>Backtest Studio</strong> te permite poner a prueba la estrategia cuantitativa utilizando datos de precios del pasado para medir su efectividad real sin arriesgar capital.
          </p>

          <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-3">
            <h4 className="font-semibold text-slate-100 text-xs uppercase tracking-wider">Métricas Clave de Rendimiento:</h4>
            <ul className="space-y-2 text-xs text-slate-400">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span><strong className="text-slate-200">Win Rate (%):</strong> Porcentaje de operaciones ganadoras frente a perdedoras en el periodo simulado.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span><strong className="text-slate-200">Sharpe Ratio:</strong> Mide el retorno ajustado por riesgo. Un valor superior a 1.5 indica una estrategia sólida.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span><strong className="text-slate-200">Max Drawdown:</strong> La máxima caída porcentual consecutiva que sufrió la cuenta en la simulación.</span>
              </li>
            </ul>
          </div>
        </div>
      )
    },
    {
      id: 'notifications',
      title: 'Acciones & Opciones (Notificaciones)',
      icon: Bell,
      color: 'text-amber-400',
      badge: 'Alertas en Vivo + Telegram',
      content: (
        <div className="space-y-6 text-sm text-slate-300">
          <p className="text-slate-200 font-medium leading-relaxed">
            El <strong>Centro de Notificaciones (Campana 🔔)</strong> genera recomendaciones automáticas de compra estructuradas para <strong>Acciones</strong> y <strong>Opciones Financieras</strong>.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-900/80 p-4 rounded-xl border border-emerald-500/20 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">📈 Recomendación de Acciones</span>
                <span className="px-2 py-0.5 text-[10px] rounded bg-emerald-500/10 text-emerald-400 font-mono">STOCK</span>
              </div>
              <p className="text-xs text-slate-400">
                Entrega precio de entrada óptimo, Stop Loss, Take Profit 1 & 2, Ratio R:R y la cantidad exacta de acciones según el 1% de riesgo.
              </p>
            </div>

            <div className="bg-slate-900/80 p-4 rounded-xl border border-purple-500/20 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-purple-400 uppercase tracking-wider">⚡ Recomendación de Opciones</span>
                <span className="px-2 py-0.5 text-[10px] rounded bg-purple-500/10 text-purple-400 font-mono">CALL / PUT</span>
              </div>
              <p className="text-xs text-slate-400">
                Selecciona contrato <strong>CALL</strong> (alcista) o <strong>PUT</strong> (bajista), Strike óptimo (ATM/OTM), Vencimiento, Prima estimada, SL en prima (-30%) y TP (+50% / +100%).
              </p>
            </div>
          </div>

          <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 flex items-center gap-3">
            <Smartphone className="w-8 h-8 text-sky-400 shrink-0" />
            <div>
              <h5 className="font-semibold text-slate-200 text-xs">Alertas Automáticas en Telegram</h5>
              <p className="text-xs text-slate-400">
                Todas las recomendaciones se envían instantáneamente con diseño profesional y emojis a tu chat de Telegram.
              </p>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'brokers',
      title: 'Configuración & Brokers (Moomoo / Alpaca)',
      icon: Settings,
      color: 'text-purple-400',
      badge: 'Ejecución Automática',
      content: (
        <div className="space-y-6 text-sm text-slate-300">
          <p className="text-slate-200 font-medium leading-relaxed">
            Puedes conectar tus cuentas de broker para ejecutar órdenes reales o simuladas directamente desde la aplicación.
          </p>

          <div className="space-y-3">
            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-2">
              <h5 className="font-semibold text-slate-100 text-xs flex items-center gap-2">
                <Lock className="w-4 h-4 text-amber-400" />
                Moomoo OpenD (Futu API)
              </h5>
              <p className="text-xs text-slate-400">
                Moomoo OpenD se ejecuta localmente en tu computadora en el puerto <strong>11111</strong>. Soporta tanto <strong>Paper Trading</strong> (Simulado sin contraseña) como <strong>Cuenta Real</strong> (ingresando tu clave de trading).
              </p>
            </div>

            <div className="bg-slate-900/80 p-4 rounded-xl border border-slate-800 space-y-2">
              <h5 className="font-semibold text-slate-100 text-xs flex items-center gap-2">
                <Zap className="w-4 h-4 text-sky-400" />
                Alpaca Markets
              </h5>
              <p className="text-xs text-slate-400">
                Permite ejecución sin comisiones mediante llaves API (`API Key` y `Secret Key`).
              </p>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'controls',
      title: 'Botones de Control & Pánico',
      icon: ShieldAlert,
      color: 'text-rose-400',
      badge: 'Seguridad en Vivo',
      content: (
        <div className="space-y-6 text-sm text-slate-300">
          <p className="text-slate-200 font-medium leading-relaxed">
            La barra superior incluye controles rápidos de supervisión y gestión de riesgos:
          </p>

          <div className="space-y-3">
            <div className="bg-slate-900/80 p-3.5 rounded-xl border border-emerald-500/20 flex items-center justify-between">
              <div>
                <span className="font-bold text-emerald-400 text-xs">INICIAR / PAUSAR BOT</span>
                <p className="text-xs text-slate-400">Activa la supervisión automática de mercado cada 4 segundos.</p>
              </div>
            </div>

            <div className="bg-slate-900/80 p-3.5 rounded-xl border border-rose-500/30 flex items-center justify-between">
              <div>
                <span className="font-bold text-rose-400 text-xs">🚨 BOTÓN DE PÁNICO</span>
                <p className="text-xs text-slate-400">Cierra de emergencia TODAS las posiciones abiertas y liquida las órdenes del broker en 1 solo clic.</p>
              </div>
            </div>

            <div className="bg-slate-900/80 p-3.5 rounded-xl border border-sky-500/20 flex items-center justify-between">
              <div>
                <span className="font-bold text-sky-400 text-xs">TEST TRADE</span>
                <p className="text-xs text-slate-400">Envía una orden de verificación de $1 para confirmar la conectividad con el broker.</p>
              </div>
            </div>
          </div>
        </div>
      )
    }
  ];

  const filteredSections = sections.filter(sec =>
    sec.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    sec.badge.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const activeSection = sections.find(s => s.id === activeTab) || sections[0];

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-[#0F141C] border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">

        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
              <BookOpen className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h3 className="font-bold text-slate-100 text-base flex items-center gap-2">
                Centro de Ayuda & Guía del Sistema
              </h3>
              <p className="text-xs text-slate-400">Explicación sencilla de cada módulo de TradePulse</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          
          {/* Navigation Sidebar */}
          <div className="w-full md:w-64 border-r border-slate-800 p-4 space-y-2 bg-slate-900/30 overflow-y-auto">
            {sections.map((sec) => {
              const Icon = sec.icon;
              const isActive = activeTab === sec.id;
              return (
                <button
                  key={sec.id}
                  onClick={() => setActiveTab(sec.id)}
                  className={`w-full text-left p-3 rounded-xl transition flex items-center gap-3 text-xs font-medium border ${
                    isActive
                      ? 'bg-slate-800 border-slate-700 text-slate-100 shadow-md'
                      : 'border-transparent text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${sec.color}`} />
                  <div className="truncate">
                    <div className="truncate">{sec.title}</div>
                    <div className="text-[10px] text-slate-500 font-normal">{sec.badge}</div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Content Area */}
          <div className="flex-1 p-6 overflow-y-auto bg-slate-950/40">
            <div className="flex items-center justify-between mb-6 pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                {React.createElement(activeSection.icon, { className: `w-6 h-6 ${activeSection.color}` })}
                <h4 className="font-bold text-slate-100 text-lg">{activeSection.title}</h4>
              </div>
              <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {activeSection.badge}
              </span>
            </div>

            {activeSection.content}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/50 flex items-center justify-between text-xs text-slate-400">
          <span>¿Tienes dudas? El bot opera con gestión de riesgo estricta (1% max por trade).</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-emerald-500 text-slate-950 font-bold hover:bg-emerald-400 transition"
          >
            Entendido
          </button>
        </div>

      </div>
    </div>
  );
}
