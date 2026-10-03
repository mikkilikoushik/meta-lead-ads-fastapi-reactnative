export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? "").replace(/\/+$/, "");
export const WS_URL = API_URL.replace(/^http/, "ws") + "/ws";

// ngrok's free tier serves a browser warning page unless this header is present.
export const DEFAULT_HEADERS = { "ngrok-skip-browser-warning": "true" };
