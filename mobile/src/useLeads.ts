import { useCallback, useEffect, useRef, useState } from "react";
import { AppState } from "react-native";

import { fetchLeads } from "./api";
import { API_URL, DEFAULT_HEADERS, WS_URL } from "./config";
import { ConnectionStatus, Lead } from "./types";

const MAX_BACKOFF_MS = 10_000;

export function useLeads() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const attemptRef = useRef(0);
  const stoppedRef = useRef(false);

  const loadExisting = useCallback(async () => {
    try {
      setLeads(await fetchLeads());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const connect = useCallback(() => {
    if (stoppedRef.current) return;
    if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) return; // already connecting/open

    setStatus("connecting");
    // RN's WebSocket accepts a third "options" argument with headers.
    const ws = new (WebSocket as any)(WS_URL, undefined, { headers: DEFAULT_HEADERS }) as WebSocket;
    wsRef.current = ws;

    ws.onopen = () => {
      attemptRef.current = 0;
      setStatus("live");
      // One-time resync so nothing sent while we were disconnected is missed.
      void loadExisting();
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(String(event.data));
        if (msg.type === "lead") {
          const lead = msg.data as Lead;
          setLeads((prev) => (prev.some((l) => l.id === lead.id) ? prev : [lead, ...prev]));
        }
      } catch {
        /* ignore malformed frames */
      }
    };

    ws.onerror = () => ws.close();

    ws.onclose = () => {
      if (wsRef.current === ws) wsRef.current = null;
      if (stoppedRef.current) return;
      setStatus("offline");
      const delay = Math.min(1000 * 2 ** attemptRef.current, MAX_BACKOFF_MS);
      attemptRef.current += 1;
      retryRef.current = setTimeout(connect, delay);
    };
  }, [loadExisting]);

  useEffect(() => {
    if (!API_URL) return; // App.tsx shows a config message
    stoppedRef.current = false;
    void loadExisting();
    connect();

    // When the app returns to the foreground, make sure the socket is alive.
    const sub = AppState.addEventListener("change", (state) => {
      if (state === "active" && !wsRef.current) {
        if (retryRef.current) clearTimeout(retryRef.current);
        attemptRef.current = 0;
        connect();
      }
    });

    return () => {
      stoppedRef.current = true;
      sub.remove();
      if (retryRef.current) clearTimeout(retryRef.current);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [connect, loadExisting]);

  return { leads, status, error };
}
