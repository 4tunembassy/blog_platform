export type ContentState =
  | "INGESTED"
  | "CLASSIFIED"
  | "DEFERRED"
  | "RETIRED"
  | "DRAFTED"
  | "VALIDATED"
  | "APPROVED"
  | "PUBLISHED";

export type ContentItem = {
  id: string;
  title: string;
  state: ContentState | string;
  risk_tier: number;
  created_at: string; // ISO
  updated_at: string; // ISO
};

export type ContentListResponse = {
  items: ContentItem[];
  limit: number;
  offset: number;
  total: number;
};

export type AllowedTransitionsResponse = {
  content_id: string;
  from_state: string;
  risk_tier: number;
  allowed: string[];
};

export type ContentEvent = {
  id: string;
  entity_type: string;
  entity_id: string;
  event_type: string;
  actor_type: string;
  actor_id?: string | null;
  payload: any;
  created_at: string; // ISO
};

export type TransitionRequest = {
  to_state: string;
};

export type TransitionResponse = {
  content_id: string;
  from_state: string;
  to_state: string;
  risk_tier: number;
};
