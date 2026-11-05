// Mirrors the JSON shapes produced by webapp/serializers.py and webapp/api/*.py.

export type DeadlineStatus = "open" | "upcoming" | "rolling" | "past";
export type VenueType = "Conference" | "Journal" | "Workshop/Symposium";

export interface Cycle {
  id: number;
  year: number;
  label: string;
  timezone: "AoE" | "UTC";
  is_projected: boolean;
  verified_at: string | null;
  source_url: string;
  submission_open_date: string | null;
  abstract_deadline: string | null;
  submission_deadline: string;
  notification_date: string | null;
  camera_ready_date: string | null;
  event_start_date: string | null;
  event_end_date: string | null;
}

export interface VenueRef {
  slug: string;
  acronym: string;
  name: string;
  flag: string;
  venue_type: VenueType;
}

export interface Tag {
  slug: string;
  name: string;
}

export interface VenueCard extends VenueRef {
  primary_domain: string;
  subfields: Tag[];
  rank_label: string;
  core_rank: string;
  ccf_rank: string;
  quartile: string;
  h5_index: number | null;
  impact_factor: number | null;
  acceptance_rate: number | null;
  city: string;
  country: string;
  continent: string;
  attendance_mode: string;
  review_process: string;
  is_open_access: boolean;
  is_rolling: boolean;
  status: DeadlineStatus;
  next_deadline: { kind: "Abstract" | "Paper"; at: string } | null;
  next_cycle: Cycle | null;
  starred: boolean;
  trackers: number | null;
}

export interface Chip {
  name: string;
  value: string;
  label: string;
}

export interface Paged<T> {
  total: number;
  page: number;
  num_pages: number;
  page_size: number;
  chips: Chip[];
  results: T[];
}

export interface TimelineRow {
  venue: VenueRef & { rank_label: string; starred: boolean };
  cycle: { id: number; label: string; is_projected: boolean };
  summary: string;
  segments: { kind: "open" | "review" | "camera" | "event"; label: string; left: number; width: number; start: string; end: string }[];
  markers: { label: string; left: number; at: string }[];
}

export interface TimelineData {
  total: number;
  row_count: number;
  rolling_hidden: number;
  page: number;
  num_pages: number;
  page_size: number;
  chips: Chip[];
  today: number;
  ticks: { left: number; label: string; year: number | null }[];
  rows: TimelineRow[];
}

export interface CalendarEvent {
  venue: VenueRef;
  cycle: string;
  is_projected: boolean;
  label: string;
  kind: "abstract" | "submission" | "notification" | "camera_ready";
  at: string;
}

export interface CalendarData {
  total: number;
  chips: Chip[];
  months: { year: number; month: number; label: string; events: CalendarEvent[] }[];
}

export interface Facets {
  domains: string[];
  countries: string[];
  continents: string[];
  tags: { slug: string; name: string; n: number }[];
  types: string[];
  core: string[];
  ccf: string[];
  quartiles: string[];
  review: string[];
  status: { value: string; label: string }[];
  within: { value: string; label: string }[];
  sort: { value: string; label: string }[];
}

export interface HomeData {
  stats: { venues: number; open: number; closing_30: number; countries: number };
  closing_soon: { venue: VenueRef & { rank_label: string }; cycle: Cycle }[];
}

export interface Review {
  id: number;
  rating: number;
  review_quality: number;
  turnaround_days: number | null;
  outcome: "accepted" | "rejected" | "pending";
  outcome_label: string;
  comment: string;
  created_at: string;
  author: string;
  mine: boolean;
}

export interface ReviewStats {
  n: number;
  rating: number | null;
  quality: number | null;
  turnaround: number | null;
  accepted: number;
  decided: number;
  accept_pct: number | null;
}

export interface DeadlineChange {
  id: number;
  venue: VenueRef;
  cycle: string;
  field: string;
  field_label: string;
  old_value: string | null;
  new_value: string | null;
  delta_days: number | null;
  changed_at: string;
}

export interface VenueDetail extends VenueCard {
  description: string;
  scope: string;
  h5_median: number | null;
  citescore: number | null;
  sjr: number | null;
  issn: string;
  page_limit: string;
  formatting_style: string;
  template_url: string;
  apc_cost_usd: number | null;
  publisher: string;
  official_website: string;
  submission_portal_url: string;
  cycles: Cycle[];
  steps: { label: string; when: string; state: "done" | "current" | "upcoming"; is_date: boolean }[];
  calendar_links: { google?: string; outlook?: string };
  checklist: { label: string; value: string }[];
  latex: string;
  bibtex: string;
  tracking_count: number;
  review_stats: ReviewStats;
  reviews: Review[];
  changes: DeadlineChange[];
  related: VenueCard[];
  urls: { page: string; ics: string | null };
  me: {
    starred: boolean;
    note: string;
    note_updated_at: string | null;
    lists: { slug: string; name: string; member: boolean }[] | null;
    review: Review | null;
  };
}

export interface CompareCell {
  value: string | number | { start: string; end: string } | null;
  best: boolean;
}

export interface CompareData {
  max: number;
  venues: VenueCard[];
  rows: { label: string; key: string; type: "text" | "number" | "percent" | "datetime" | "daterange"; cells: CompareCell[] }[];
}

export interface SessionUser {
  username: string;
  email: string;
  name: string;
  initials: string;
  timezone: string;
  email_verified: boolean;
  is_staff: boolean;
}

export interface Session {
  authenticated: boolean;
  csrf_token: string;
  user: SessionUser | null;
  unread_count: number;
  target_count: number;
  messages: { level: string; text: string }[];
  admin_url: string | null;
}

export interface Notification {
  id: number;
  kind: string;
  kind_label: string;
  message: string;
  url: string;
  created_at: string;
  read: boolean;
}

export interface VenueListSummary {
  slug: string;
  name: string;
  description: string;
  is_public: boolean;
  count: number | null;
  created_at: string;
}

export interface SavedSearch {
  id: number;
  name: string;
  querystring: string;
  alert: boolean;
  last_count: number;
  created_at: string;
}

export interface Submission {
  id: number;
  paper: { id: number; title: string };
  venue: VenueRef;
  cycle: { id: number; year: number; label: string; submission_deadline: string } | null;
  status: string;
  status_label: string;
  submitted_on: string | null;
  decision_on: string | null;
  notes: string;
  deadline: string | null;
  days_left: number | null;
  checklist: { done: number; total: number };
  created_at: string;
  updated_at: string;
}

export interface SubmissionDetail extends Submission {
  checklist_items: { id: number; text: string; done: boolean }[];
  venue_cycles: Cycle[];
  venue_rank_label: string;
}

export interface Paper {
  id: number;
  title: string;
  abstract: string;
  keywords: string;
  created_at: string;
  submission_count: number | null;
}

export interface Recommendation {
  venue: VenueCard;
  percent: number;
  reasons: string[];
}

export interface Boot {
  page: string;
  status: number;
  session: Session;
  initial: {
    facets?: Facets;
    home?: HomeData;
    explore?: Paged<VenueCard> | TimelineData | CalendarData;
    venue?: VenueDetail;
    list?: unknown;
  };
  extra: { not_found?: "page" | "venue" | "list" | "submission" };
  site: { name: string; url: string };
}
