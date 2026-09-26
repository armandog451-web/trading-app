const API_BASE = '/api';

export async function fetchDashboardStatus() {
  const res = await fetch(`${API_BASE}/dashboard/status`);
  return res.json();
}

export async function startBot() {
  const res = await fetch(`${API_BASE}/dashboard/bot/start`, { method: 'POST' });
  return res.json();
}

export async function stopBot() {
  const res = await fetch(`${API_BASE}/dashboard/bot/stop`, { method: 'POST' });
  return res.json();
}

export async function triggerPanic() {
  const res = await fetch(`${API_BASE}/dashboard/panic`, { method: 'POST' });
  return res.json();
}

export async function fetchActivePositions() {
  const res = await fetch(`${API_BASE}/dashboard/positions`);
  return res.json();
}

export async function fetchTradeHistory() {
  const res = await fetch(`${API_BASE}/dashboard/trades`);
  return res.json();
}

export async function triggerTestTrade(symbol = 'SPY') {
  const res = await fetch(`${API_BASE}/dashboard/test-trade?symbol=${symbol}`, { method: 'POST' });
  return res.json();
}

export async function fetchMacroFactors() {
  const res = await fetch(`${API_BASE}/factors/macro`);
  return res.json();
}

export async function fetchSentimentFactors() {
  const res = await fetch(`${API_BASE}/factors/sentiment`);
  return res.json();
}

export async function fetchScreenerStocks() {
  const res = await fetch(`${API_BASE}/factors/screener`);
  return res.json();
}

export async function fetchTechnicalData(symbol = 'SPY') {
  const res = await fetch(`${API_BASE}/factors/technical/${symbol}`);
  return res.json();
}

export async function runBacktest(params) {
  const res = await fetch(`${API_BASE}/backtest/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  return res.json();
}

export async function fetchSettings() {
  const res = await fetch(`${API_BASE}/settings`);
  return res.json();
}

export async function updateRiskSettings(data) {
  const res = await fetch(`${API_BASE}/settings/risk`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function updateBrokerSettings(data) {
  const res = await fetch(`${API_BASE}/settings/broker`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function testBrokerConnection(data) {
  const res = await fetch(`${API_BASE}/settings/test-broker`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function testMoomooConnection(data) {
  const res = await fetch(`${API_BASE}/settings/test-moomoo`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}



export async function updateTelegramSettings(token, chatId, notifyMarketClose = false) {
  const res = await fetch(`${API_BASE}/settings/telegram`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      telegram_bot_token: token,
      telegram_chat_id: chatId,
      notify_market_close: notifyMarketClose
    }),
  });
  return res.json();
}

export async function fetchNotifications(unreadOnly = false) {
  const res = await fetch(`${API_BASE}/notifications?unread_only=${unreadOnly}`);
  return res.json();
}

export async function markNotificationRead(id) {
  const res = await fetch(`${API_BASE}/notifications/${id}/read`, { method: 'POST' });
  return res.json();
}

export async function markAllNotificationsRead() {
  const res = await fetch(`${API_BASE}/notifications/read-all`, { method: 'POST' });
  return res.json();
}

export async function triggerDemoSignal(assetType = 'STOCK', symbol = 'SPY', customNote = '') {
  const res = await fetch(`${API_BASE}/notifications/trigger-demo-signal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ asset_type: assetType, symbol, custom_note: customNote }),
  });
  return res.json();
}

export async function testTelegramConnection(token = '', chatId = '', customMessage = '') {
  const res = await fetch(`${API_BASE}/notifications/test-telegram`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      telegram_bot_token: token || undefined,
      telegram_chat_id: chatId || undefined,
      custom_message: customMessage || undefined,
    }),
  });
  return res.json();
}

export async function executeNotificationTrade(id) {
  const res = await fetch(`${API_BASE}/notifications/${id}/execute`, { method: 'POST' });
  return res.json();
}

export async function syncGitHub() {
  const res = await fetch(`${API_BASE}/settings/sync-github`, { method: 'POST' });
  return res.json();
}



