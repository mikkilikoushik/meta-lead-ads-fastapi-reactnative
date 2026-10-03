export interface Lead {
  id: number;
  meta_lead_id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  form_id: string | null;
  page_id: string | null;
  created_time: string;
}

export type ConnectionStatus = "connecting" | "live" | "offline";
