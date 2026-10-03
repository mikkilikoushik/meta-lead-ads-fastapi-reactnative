import { API_URL, DEFAULT_HEADERS } from "./config";
import { Lead } from "./types";

export async function fetchLeads(): Promise<Lead[]> {
  const res = await fetch(`${API_URL}/leads`, { headers: DEFAULT_HEADERS });
  if (!res.ok) throw new Error(`GET /leads failed: ${res.status}`);
  return res.json();
}
