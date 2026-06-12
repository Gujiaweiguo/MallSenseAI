import { ref, readonly } from 'vue';

import { AUTH_TOKEN_STORAGE_KEY } from '@/auth/storage';
import type { AlertEvent } from '@/api/types';

const lastEvent = ref<AlertEvent | null>(null);
const connected = ref(false);

let ws: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

function wsUrl(): string {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}/api/ws/alerts`;
}

function connect(): void {
  const token = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  if (!token) return;

  const url = `${wsUrl()}?token=${encodeURIComponent(token)}`;
  ws = new WebSocket(url);

  ws.onopen = () => {
    connected.value = true;
  };

  ws.onmessage = (event: MessageEvent) => {
    try {
      const data: AlertEvent = JSON.parse(event.data as string);
      lastEvent.value = data;
    } catch {
      // ignore malformed messages
    }
  };

  ws.onclose = () => {
    connected.value = false;
    ws = null;
    scheduleReconnect();
  };

  ws.onerror = () => {
    ws?.close();
  };
}

function disconnect(): void {
  if (reconnectTimer !== null) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (ws !== null) {
    ws.onclose = null; // prevent reconnect on intentional close
    ws.close();
    ws = null;
  }
  connected.value = false;
}

const RECONNECT_DELAY_MS = 3000;

function scheduleReconnect(): void {
  if (reconnectTimer !== null) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    const token = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
    if (token) connect();
  }, RECONNECT_DELAY_MS);
}

export function useAlertEvents() {
  return {
    lastEvent: readonly(lastEvent),
    connected: readonly(connected),
    connect,
    disconnect,
  };
}
