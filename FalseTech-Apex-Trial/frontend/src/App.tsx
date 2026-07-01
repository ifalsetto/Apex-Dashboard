import AuthPanel from "./AuthPanel";
import { SpotifyMusicPanel } from './components/SpotifyMusicPanel';
import { useEffect, useReducer, useState } from 'react';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/+$/, '');

type PlatformUi = 'steam' | 'xbl' | 'psn';
type PlatformApi = 'origin' | 'xbl' | 'psn';
type ProviderId = 'tracker' | 'mozambique' | 'mock';
type TabKey =
  | 'command'
  | 'live'
  | 'friends'
  | 'legends'
  | 'weapons'
  | 'sessions'
  | 'squads'
  | 'music'
  | 'creator'
  | 'performance'
  | 'settings';

const DEFAULT_SPOTIFY_EMBED_URL = 'https://open.spotify.com/embed/artist/3Z9dPu2wQ7angZt7yzqGDP';

type ProfileRecord = {
  username: string;
  platform: string;
  level: number;
  currentRank: string;
  currentRp: number;
  peakRank: string;
  peakRp: number;
  lifetimeMatches: number;
  totalKills: number;
  totalDamage: number;
  totalWins: number;
  mainLegend: string;
  bestLoadout: string;
};

type LegendRecord = {
  id: string;
  name: string;
  role: string;
  fit: number;
  kills: number;
  damage: number;
  wins: number;
  passive: string;
  tactical: string;
  ultimate: string;
  strengths: string[];
  note: string;
};

type WeaponRecord = {
  id: string;
  name: string;
  class: string;
  ammo: string;
  range: string;
  tier: string;
  fit: number;
  attachments: string[];
  strengths: string[];
  weakness: string;
  note: string;
};

type SessionRecord = {
  id: string;
  time: string;
  legend: string;
  map: string;
  placement: string;
  delta: number;
  kills: number;
  damage: number;
  summary: string;
  causes: string[];
};

type UpdateRecord = {
  id: string;
  title: string;
  category: string;
  priority: string;
  summary: string;
  action: string;
};

type DashboardState = {
  activeHandle: string;
  platformUi: PlatformUi;
  lastSync: string | null;
  syncing: boolean;
  syncError: string | null;
  profile: ProfileRecord;
  legends: LegendRecord[];
  weapons: WeaponRecord[];
  sessions: SessionRecord[];
  updates: UpdateRecord[];
};

type DashboardAction =
  | { type: 'SET_ACTIVE_HANDLE'; handle: string }
  | { type: 'SET_PLATFORM'; platformUi: PlatformUi }
  | { type: 'SYNC_START' }
  | {
      type: 'SYNC_SUCCESS';
      payload: {
        profile: ProfileRecord;
        legends: LegendRecord[];
        sessions: SessionRecord[];
        statusMessage?: string | null;
      };
    }
  | { type: 'SYNC_ERROR'; error: string };

type StandardApiResponse<T> = {
  ok: boolean;
  source: ProviderId;
  provider?: ProviderId;
  fallbackUsed: boolean;
  cached: boolean;
  status: 'live' | 'fallback' | 'error';
  message: string;
  data?: T;
  error?: { code: string; message: string };
  meta: {
    path?: string;
    platform?: string;
    player?: string;
    query?: string;
    segmentType?: string;
    fetchedAt?: string;
    provider?: ProviderId;
    fallbackUsed?: boolean;
    status?: 'live' | 'fallback' | 'error';
    message?: string;
    providerChain?: Array<{
      provider: ProviderId;
      status: 'hit' | 'failed' | 'skipped' | 'blocked';
      code?: string;
      message?: string;
    }>;
  };
};

type TrackerProfileResponse = {
  data?: {
    platformInfo?: {
      platformUserHandle?: string;
      platformSlug?: string;
      avatarUrl?: string;
    };
    metadata?: Record<string, unknown>;
    segments?: Array<{
      type?: string;
      metadata?: Record<string, unknown>;
      stats?: Record<string, { value?: number; displayValue?: string; metadata?: Record<string, unknown> }>;
    }>;
  };
};

type TrackerSessionsResponse = {
  data?: {
    items?: Array<{
      metadata?: Record<string, unknown>;
      stats?: Record<string, { value?: number; displayValue?: string }>;
    }>;
  };
};

type TrackerSearchItem = {
  platformId?: number;
  platformSlug?: string;
  platformUserHandle?: string;
};

type TrackerSearchResponse =
  | TrackerSearchItem[]
  | {
      data?: TrackerSearchItem[];
      results?: TrackerSearchItem[];
      players?: TrackerSearchItem[];
    };

const STORAGE = {
  handle: 'falsetech-active-handle-v1',
  platform: 'falsetech-active-platform-v1',
  activeTab: 'falsetech-active-tab-v1',
  friends: 'falsetech-friends-v1',
  musicEnabled: 'falsetech-music-enabled-v1',
  musicVisible: 'falsetech-music-visible-v1',
  spotifyEmbed: 'falsetech-spotify-embed-v1',
  creatorUnlocks: 'falsetech-creator-unlocks-v1'
};

const TABS: Array<{ key: TabKey; label: string; description: string }> = [
  { key: 'command', label: 'Command', description: 'Summary cards and best next actions' },
  { key: 'live', label: 'Live Data', description: 'Tracker proxy status and profile refresh controls' },
  { key: 'friends', label: 'Friends', description: 'Saved handles and profile switching' },
  { key: 'legends', label: 'Legends', description: 'Legend selection and fit details' },
  { key: 'weapons', label: 'Weapons', description: 'Weapon selection and loadout fit' },
  { key: 'sessions', label: 'Sessions', description: 'Session review and match notes' },
  { key: 'squads', label: 'Squads', description: 'Squad structures and team roles' },
  { key: 'music', label: 'Music', description: 'Creator music lane controls' },
  { key: 'creator', label: 'Creator', description: 'Creator unlock and progress tools' },
  { key: 'performance', label: 'Performance', description: 'FPS, latency, display, and network cards' },
  { key: 'settings', label: 'Settings', description: 'Local settings and restore controls' }
];

const DEFAULT_PROFILE: ProfileRecord = {
  username: 'NotFalsetto',
  platform: 'Steam / EA (PC)',
  level: 894,
  currentRank: 'Diamond 4',
  currentRp: 12350,
  peakRank: 'Master',
  peakRp: 21334,
  lifetimeMatches: 1050,
  totalKills: 2646,
  totalDamage: 1893101,
  totalWins: 68,
  mainLegend: 'Lifeline',
  bestLoadout: 'Nemesis + Volt'
};

const DEFAULT_LEGENDS: LegendRecord[] = [
  {
    id: 'lifeline',
    name: 'Lifeline',
    role: 'Support',
    fit: 96,
    kills: 1293,
    damage: 1274677,
    wins: 66,
    passive: 'Support utility and reset identity.',
    tactical: 'D.O.C. sustain and revive stabilization.',
    ultimate: 'Resource recovery and safer tempo extension.',
    strengths: ['Reset leader', 'High sustain', 'Safer endgames'],
    note: 'Best when the squad needs recovery leadership without losing all frag pressure.'
  },
  {
    id: 'horizon',
    name: 'Horizon',
    role: 'Skirmisher',
    fit: 91,
    kills: 842,
    damage: 618420,
    wins: 32,
    passive: 'Air control and smoother landing recovery.',
    tactical: 'Vertical take, reset, and angle break.',
    ultimate: 'Fight compression and nade pressure.',
    strengths: ['Angle creation', 'Height conversion', 'Tempo control'],
    note: 'Best for reproducing your strongest surge sessions when you want faster tempo.'
  },
  {
    id: 'bangalore',
    name: 'Bangalore',
    role: 'Assault',
    fit: 82,
    kills: 323,
    damage: 228551,
    wins: 11,
    passive: 'Fast reposition under pressure.',
    tactical: 'Smoke denial and digi synergy.',
    ultimate: 'Zone denial and reset protection.',
    strengths: ['Disruption', 'Space cover', 'Chaos control'],
    note: 'Useful when you need disruption and space control more than pure sustain.'
  }
];

const DEFAULT_WEAPONS: WeaponRecord[] = [
  {
    id: 'nemesis',
    name: 'Nemesis',
    class: 'AR',
    ammo: 'Energy',
    range: 'Mid',
    tier: 'S',
    fit: 92,
    attachments: ['1x-3x optics', 'Barrel stabilizer', 'Extended energy mag'],
    strengths: ['Burst pressure', 'Flexible range', 'Shield crack reliability'],
    weakness: 'Needs rhythm discipline when fights get messy.',
    note: 'Excellent ranked weapon for controlled damage conversion before committing.'
  },
  {
    id: 'volt',
    name: 'Volt',
    class: 'SMG',
    ammo: 'Energy',
    range: 'Close-Mid',
    tier: 'S',
    fit: 90,
    attachments: ['1x optics', 'Laser sight', 'Extended energy mag'],
    strengths: ['Smooth recoil', 'Reliable cleanup', 'Great chase value'],
    weakness: 'Falls off if you force too much distance.',
    note: 'Strong complement to a support-fragger identity because it cleans fast with low stress.'
  },
  {
    id: 'hemlok',
    name: 'Hemlok',
    class: 'AR',
    ammo: 'Heavy',
    range: 'Mid-Long',
    tier: 'A',
    fit: 87,
    attachments: ['2x-3x optics', 'Barrel stabilizer', 'Extended heavy mag'],
    strengths: ['Controlled poke', 'Ammo efficiency', 'Burst discipline'],
    weakness: 'Can feel slow when the lobby becomes close-range chaos.',
    note: 'Use when you want safer opening damage and stronger rotate punishment.'
  }
];

const DEFAULT_SESSIONS: SessionRecord[] = [
  {
    id: 's1',
    time: '13 minutes ago',
    legend: 'Horizon',
    map: 'Olympus',
    placement: '#4',
    delta: 45,
    kills: 5,
    damage: 1481,
    summary: 'Controlled gain session with clean angle conversions and no major throw fight.',
    causes: ['Good height usage', 'Clean entry damage', 'No panic over-chase']
  },
  {
    id: 's2',
    time: '2 hours ago',
    legend: 'Horizon',
    map: 'Olympus',
    placement: '#1',
    delta: 395,
    kills: 24,
    damage: 4218,
    summary: 'Explosive surge session. This is the ceiling state the app should help you reproduce.',
    causes: ['Disciplined tempo', 'Fast closeouts', 'Weapon pair fit was high']
  },
  {
    id: 's3',
    time: '6 hours ago',
    legend: 'Lifeline',
    map: 'Worlds Edge',
    placement: '#9',
    delta: -11,
    kills: 3,
    damage: 902,
    summary: 'Low-value support session. Good survival structure, weak damage conversion.',
    causes: ['Slow commit timing', 'Low angle pressure', 'Too much resource duty']
  }
];

const DEFAULT_UPDATES: UpdateRecord[] = [
  {
    id: 'u1',
    title: 'Apex v2 command center',
    category: 'Creator',
    priority: 'High',
    summary: 'Every user lands on a focused Apex command center with live stats, sessions, legends, weapons, and squads.',
    action: 'Keep the first screen tuned for real player decisions instead of template content.'
  },
  {
    id: 'u2',
    title: 'Music lane supports creator identity',
    category: 'Music',
    priority: 'High',
    summary: 'The music lane gives the beta a distinct creator surface while staying optional and user-controlled.',
    action: 'Hide from the music card, restore from Settings.'
  },
  {
    id: 'u3',
    title: 'Friends and squads stay profile-first',
    category: 'Social',
    priority: 'Critical',
    summary: 'Profile switching, squad planning, and session review stay close together for repeated Apex use.',
    action: 'Keep Friends, Squads, and Session Review easy to scan.'
  }
];

const SQUADS = [
  {
    name: 'Default Ranked Cell',
    members: ['Lifeline anchor', 'Aggro entry', 'Zone closer'],
    purpose: 'Your reliable ranked shell for safer resets and stronger fight recovery.'
  },
  {
    name: 'Creator Stack',
    members: ['You', 'Featured friend', 'Rotating guest'],
    purpose: 'The showcase squad identity for music, clips, and creator-facing runs.'
  },
  {
    name: 'Trial Team View',
    members: ['Investor preview', 'Partner preview', 'Community preview'],
    purpose: 'Shows how the product supports squads instead of only solo stat cards.'
  }
];

const DEFAULT_STATE: DashboardState = {
  activeHandle: DEFAULT_PROFILE.username,
  platformUi: 'steam',
  lastSync: null,
  syncing: false,
  syncError: null,
  profile: DEFAULT_PROFILE,
  legends: DEFAULT_LEGENDS,
  weapons: DEFAULT_WEAPONS,
  sessions: DEFAULT_SESSIONS,
  updates: DEFAULT_UPDATES
};

function reducer(state: DashboardState, action: DashboardAction): DashboardState {
  switch (action.type) {
    case 'SET_ACTIVE_HANDLE':
      return { ...state, activeHandle: action.handle };
    case 'SET_PLATFORM':
      return { ...state, platformUi: action.platformUi };
    case 'SYNC_START':
      return { ...state, syncing: true, syncError: null };
    case 'SYNC_SUCCESS':
      return {
        ...state,
        syncing: false,
        syncError: action.payload.statusMessage ?? null,
        lastSync: new Date().toISOString(),
        profile: action.payload.profile,
        legends: action.payload.legends,
        sessions: action.payload.sessions
      };
    case 'SYNC_ERROR':
      return { ...state, syncing: false, syncError: action.error };
    default:
      return state;
  }
}

function platformToApi(platformUi: PlatformUi): PlatformApi {
  if (platformUi === 'steam') return 'origin';
  return platformUi;
}

function platformLabel(platformUi: PlatformUi): string {
  if (platformUi === 'steam') return 'Steam / EA (PC)';
  if (platformUi === 'xbl') return 'Xbox';
  return 'PlayStation';
}

function slugify(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || 'item';
}

function readNumber(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function readText(value: unknown, fallback = 'Unknown'): string {
  return typeof value === 'string' && value.trim() ? value.trim() : fallback;
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat().format(value);
}

class ApiRequestError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.code = code;
  }
}

function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return API_BASE_URL ? `${API_BASE_URL}${normalizedPath}` : normalizedPath;
}

async function fetchStandard<T>(url: string): Promise<StandardApiResponse<T>> {
  const response = await fetch(apiUrl(url), {
    method: 'GET',
    headers: {
      Accept: 'application/json'
    }
  });
  let body: StandardApiResponse<T> | null = null;

  try {
    body = (await response.json()) as StandardApiResponse<T>;
  } catch {
    body = null;
  }

  if (!response.ok || !body?.ok) {
    throw new ApiRequestError(
      body?.error?.message ?? 'Request failed',
      response.status,
      body?.error?.code
    );
  }
  return body;
}

function liveFallbackMessage(error: unknown): string {
  if (error instanceof ApiRequestError) {
    if (error.status === 401 || error.status === 403 || error.code === 'UNAUTHORIZED' || error.code === 'FORBIDDEN') {
      return 'Tracker API access is pending approval or denied. Using local beta preview data.';
    }
    if (
      error.status === 502 ||
      error.code === 'TRACKER_PROXY_FAILURE' ||
      error.code === 'TRACKER_UPSTREAM_UNAVAILABLE' ||
      error.code === 'TRACKER_TIMEOUT' ||
      error.code === 'PROVIDER_FAILURE'
    ) {
      return 'Local backend reached the Worker, but Tracker upstream is unavailable. Using local beta preview data.';
    }
  }

  return 'Live Tracker data is unavailable. Using local beta preview data.';
}

function providerStatusMessage(...responses: Array<StandardApiResponse<unknown>>): string | null {
  const fallbackResponses = responses.filter((response) => response.fallbackUsed || response.status === 'fallback');
  if (!fallbackResponses.length) return null;

  const authFallback = fallbackResponses.find((response) =>
    response.meta.providerChain?.some((attempt) => attempt.code === 'UNAUTHORIZED' || attempt.code === 'FORBIDDEN')
  );
  if (authFallback) {
    return 'Tracker API access is pending approval or denied. Using local beta preview data.';
  }

  const upstreamFallback = fallbackResponses.find((response) =>
    response.meta.providerChain?.some((attempt) =>
      ['TRACKER_UPSTREAM_UNAVAILABLE', 'TRACKER_TIMEOUT', 'TRACKER_PROXY_FAILURE', 'PROVIDER_FAILURE'].includes(attempt.code ?? '')
    )
  );
  if (upstreamFallback) {
    return 'Local backend reached the Worker, but Tracker upstream is unavailable. Using local beta preview data.';
  }

  return fallbackResponses[0].message || fallbackResponses[0].meta.message || 'Live Tracker data is unavailable. Using local beta preview data.';
}

function isTabKey(value: string | null): value is TabKey {
  return TABS.some((tab) => tab.key === value);
}

function pickOverviewSegment(profilePayload: TrackerProfileResponse) {
  return profilePayload.data?.segments?.find((segment) => segment.type === 'overview') ?? profilePayload.data?.segments?.[0];
}

function normalizeProfile(profilePayload: TrackerProfileResponse, platformUi: PlatformUi, handle: string): ProfileRecord {
  const overview = pickOverviewSegment(profilePayload);
  const stats = overview?.stats ?? {};
  const metadata = profilePayload.data?.metadata ?? {};
  const platformInfo = profilePayload.data?.platformInfo ?? {};

  return {
    username: readText(platformInfo.platformUserHandle, handle),
    platform: platformLabel(platformUi),
    level: readNumber(stats.level?.value),
    currentRank: readText(stats.rankScore?.metadata?.rankName ?? stats.rankScore?.displayValue, 'Unknown'),
    currentRp: readNumber(stats.rankScore?.value),
    peakRank: readText(stats.rankScore?.metadata?.rankName ?? stats.rankScore?.displayValue, 'Unknown'),
    peakRp: readNumber(stats.rankScore?.value),
    lifetimeMatches: readNumber(stats.matchesPlayed?.value),
    totalKills: readNumber(stats.kills?.value),
    totalDamage: readNumber(stats.damage?.value),
    totalWins: readNumber(stats.wins?.value),
    mainLegend: readText(metadata.activeLegendName, DEFAULT_PROFILE.mainLegend),
    bestLoadout: DEFAULT_PROFILE.bestLoadout
  };
}

function normalizeLegendSegments(segmentsPayload: TrackerProfileResponse | undefined): LegendRecord[] {
  const segments = segmentsPayload?.data?.segments ?? [];
  if (!segments.length) return DEFAULT_LEGENDS;
  return segments.slice(0, 8).map((segment, index) => {
    const metadata = segment.metadata ?? {};
    const stats = segment.stats ?? {};
    const name = readText(metadata.name ?? metadata.legendName, `Legend ${index + 1}`);
    return {
      id: slugify(name),
      name,
      role: readText(metadata.roleName, 'Legend'),
      fit: Math.max(72, 80 - index * 2),
      kills: readNumber(stats.kills?.value),
      damage: readNumber(stats.damage?.value),
      wins: readNumber(stats.wins?.value),
      passive: 'Live legend passive detail can be expanded in V2.',
      tactical: 'Live legend tactical detail can be expanded in V2.',
      ultimate: 'Live legend ultimate detail can be expanded in V2.',
      strengths: ['Live stat source', 'Profile-specific', 'Refreshable'],
      note: `Live legend card for ${name}.`
    };
  });
}

function normalizeSessions(sessionsPayload: TrackerSessionsResponse | undefined): SessionRecord[] {
  const items = sessionsPayload?.data?.items ?? [];
  if (!items.length) return DEFAULT_SESSIONS;
  return items.slice(0, 10).map((item, index) => {
    const metadata = item.metadata ?? {};
    const stats = item.stats ?? {};
    const placement = readText(stats.placement?.displayValue, '#?');
    return {
      id: `live-session-${index + 1}`,
      time: readText(metadata.timestamp ?? metadata.date, `Session ${index + 1}`),
      legend: readText(metadata.legendName, 'Unknown'),
      map: readText(metadata.mapName, 'Unknown'),
      placement,
      delta: readNumber(stats.rankPoints?.value ?? stats.rankScore?.value),
      kills: readNumber(stats.kills?.value),
      damage: readNumber(stats.damage?.value),
      summary: `Placement ${placement} on ${readText(metadata.mapName, 'Unknown map')}.`,
      causes: ['Live import', 'Review manually in dashboard']
    };
  });
}

function extractSearchHandle(searchPayload: TrackerSearchResponse | undefined, fallback: string): string {
  const items = Array.isArray(searchPayload)
    ? searchPayload
    : searchPayload?.data ?? searchPayload?.results ?? searchPayload?.players ?? [];
  if (!items.length) return fallback;
  return readText(items[0].platformUserHandle, fallback);
}

function buildPath(points: number[]): string {
  if (!points.length) return '';
  const max = Math.max(...points, 1);
  const min = Math.min(...points, 0);
  const range = max - min || 1;
  return points
    .map((value, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * 100;
      const y = 48 - ((value - min) / range) * 40;
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
    })
    .join(' ');
}

function AmbientStage() {
  const actors = [
    { label: 'Wraith', left: '8%', top: '18%', delay: '0s', scale: 0.95 },
    { label: 'Pathy', left: '74%', top: '10%', delay: '1.2s', scale: 1 },
    { label: 'Bang', left: '12%', top: '72%', delay: '0.5s', scale: 0.88 },
    { label: 'Horizon', left: '71%', top: '76%', delay: '1.8s', scale: 0.9 },
    { label: 'Lifeline', left: '46%', top: '8%', delay: '0.9s', scale: 0.82 }
  ];

  return (
    <div className="ambient-stage" aria-hidden="true">
      <div className="ambient-grid" />
      {actors.map((actor) => (
        <div
          key={actor.label}
          className="ambient-actor"
          style={{ left: actor.left, top: actor.top, animationDelay: actor.delay, transform: `scale(${actor.scale})` }}
        >
          <span>{actor.label}</span>
        </div>
      ))}
      {Array.from({ length: 10 }).map((_, index) => (
        <div
          key={`tracer-${index}`}
          className="ambient-tracer"
          style={{ left: `${6 + index * 9}%`, top: `${18 + (index % 4) * 16}%`, animationDelay: `${index * 0.6}s` }}
        />
      ))}
    </div>
  );
}

function TabBar({ activeTab, onSelect }: { activeTab: TabKey; onSelect: (tab: TabKey) => void }) {
  return (
    <nav className="tab-bar" aria-label="Apex Dashboard v2 sections">
      <div className="tab-list" role="tablist" aria-orientation="horizontal">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            id={`tab-${tab.key}`}
            data-tab={tab.key}
            className={`tab-button ${activeTab === tab.key ? 'active' : ''}`}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.key}
            aria-controls={`panel-${tab.key}`}
            tabIndex={activeTab === tab.key ? 0 : -1}
            onClick={() => onSelect(tab.key)}
          >
            <span>{tab.label}</span>
            <small>{tab.description}</small>
          </button>
        ))}
      </div>
    </nav>
  );
}

function TabPanel({ tabKey, activeTab, children }: { tabKey: TabKey; activeTab: TabKey; children: React.ReactNode }) {
  if (activeTab !== tabKey) return null;

  return (
    <section
      id={`panel-${tabKey}`}
      className="tab-panel"
      role="tabpanel"
      aria-labelledby={`tab-${tabKey}`}
      tabIndex={0}
    >
      {children}
    </section>
  );
}

function StatusBanner({ message, tone = 'warning' }: { message: string; tone?: 'warning' | 'error' }) {
  return (
    <div className={`status-banner ${tone}`} role="status" aria-live="polite">
      <strong>Live data status</strong>
      <span>{message}</span>
    </div>
  );
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <div className={`card ${className}`.trim()}>{children}</div>;
}

function StatBadge({ title, value }: { title: string; value: string }) {
  return (
    <div className="stat-badge">
      <div className="stat-badge__title">{title}</div>
      <div className="stat-badge__value">{value}</div>
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric-tile">
      <div className="metric-tile__label">{label}</div>
      <div className="metric-tile__value">{value}</div>
    </div>
  );
}

function Pill({ children, tone = 'default' }: { children: React.ReactNode; tone?: 'default' | 'gold' | 'purple' }) {
  return <span className={`pill pill--${tone}`}>{children}</span>;
}

function WeaponBarChart({ weapons }: { weapons: WeaponRecord[] }) {
  return (
    <div className="bar-chart">
      {weapons.map((weapon) => (
        <div key={weapon.id} className="bar-row">
          <div className="bar-row__label">{weapon.name}</div>
          <div className="bar-row__track">
            <div className="bar-row__fill" style={{ width: `${weapon.fit}%` }} />
          </div>
          <div className="bar-row__value">{weapon.fit}</div>
        </div>
      ))}
    </div>
  );
}

function SessionSparkline({ sessions }: { sessions: SessionRecord[] }) {
  const values = sessions.slice(0, 8).map((session) => session.delta);
  const path = buildPath(values);
  return (
    <div className="sparkline-wrap">
      <svg viewBox="0 0 100 50" className="sparkline" preserveAspectRatio="none">
        <path d={path} fill="none" stroke="url(#sparkGradient)" strokeWidth="2.5" strokeLinecap="round" />
        <defs>
          <linearGradient id="sparkGradient" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#d4af37" />
            <stop offset="100%" stopColor="#9d4edd" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

export default function App() {
  const [state, dispatch] = useReducer(reducer, DEFAULT_STATE);
  const [activeTab, setActiveTab] = useState<TabKey>('command');
  const [searchValue, setSearchValue] = useState(DEFAULT_PROFILE.username);
  const [friends, setFriends] = useState<string[]>([]);
  const [selectedLegend, setSelectedLegend] = useState(DEFAULT_LEGENDS[0].id);
  const [selectedWeapon, setSelectedWeapon] = useState(DEFAULT_WEAPONS[0].id);
  const [selectedSession, setSelectedSession] = useState(DEFAULT_SESSIONS[0].id);
  const [musicEnabled, setMusicEnabled] = useState(true);
  const [musicVisible, setMusicVisible] = useState(true);
  const [spotifyEmbedUrl, setSpotifyEmbedUrl] = useState(DEFAULT_SPOTIFY_EMBED_URL);
  const [demoSubscribed, setDemoSubscribed] = useState(false);
  const [demoAddedSong, setDemoAddedSong] = useState(false);
  const [demoSharedApp, setDemoSharedApp] = useState(false);
  const [demoSharedSpotify, setDemoSharedSpotify] = useState(false);
  const [fpsTarget, setFpsTarget] = useState(300);
  const [latencyTarget, setLatencyTarget] = useState(50);
  const [displayCap, setDisplayCap] = useState(240);

  useEffect(() => {
    const savedHandle = localStorage.getItem(STORAGE.handle);
    const savedPlatform = localStorage.getItem(STORAGE.platform) as PlatformUi | null;
    const savedActiveTab = localStorage.getItem(STORAGE.activeTab);
    const savedFriends = localStorage.getItem(STORAGE.friends);
    const savedMusicEnabled = localStorage.getItem(STORAGE.musicEnabled);
    const savedMusicVisible = localStorage.getItem(STORAGE.musicVisible);
    const savedSpotifyEmbed = localStorage.getItem(STORAGE.spotifyEmbed);
    const savedUnlocks = localStorage.getItem(STORAGE.creatorUnlocks);

    if (savedHandle) {
      dispatch({ type: 'SET_ACTIVE_HANDLE', handle: savedHandle });
      setSearchValue(savedHandle);
    }
    if (savedPlatform === 'steam' || savedPlatform === 'xbl' || savedPlatform === 'psn') {
      dispatch({ type: 'SET_PLATFORM', platformUi: savedPlatform });
    }
    if (isTabKey(savedActiveTab)) setActiveTab(savedActiveTab);
    if (savedFriends) {
      try {
        const parsed = JSON.parse(savedFriends);
        if (Array.isArray(parsed)) setFriends(parsed);
      } catch {
        // ignore
      }
    }
    if (savedMusicEnabled) setMusicEnabled(savedMusicEnabled === 'true');
    if (savedMusicVisible) setMusicVisible(savedMusicVisible === 'true');
    if (savedSpotifyEmbed !== null) setSpotifyEmbedUrl(savedSpotifyEmbed);
    if (savedUnlocks) {
      try {
        const parsed = JSON.parse(savedUnlocks);
        setDemoSubscribed(Boolean(parsed.demoSubscribed));
        setDemoAddedSong(Boolean(parsed.demoAddedSong));
        setDemoSharedApp(Boolean(parsed.demoSharedApp));
        setDemoSharedSpotify(Boolean(parsed.demoSharedSpotify));
      } catch {
        // ignore
      }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE.handle, state.activeHandle);
  }, [state.activeHandle]);

  useEffect(() => {
    localStorage.setItem(STORAGE.platform, state.platformUi);
  }, [state.platformUi]);

  useEffect(() => {
    localStorage.setItem(STORAGE.activeTab, activeTab);
  }, [activeTab]);

  useEffect(() => {
    localStorage.setItem(STORAGE.friends, JSON.stringify(friends));
  }, [friends]);

  useEffect(() => {
    localStorage.setItem(STORAGE.musicEnabled, String(musicEnabled));
  }, [musicEnabled]);

  useEffect(() => {
    localStorage.setItem(STORAGE.musicVisible, String(musicVisible));
  }, [musicVisible]);

  useEffect(() => {
    localStorage.setItem(STORAGE.spotifyEmbed, spotifyEmbedUrl);
  }, [spotifyEmbedUrl]);

  useEffect(() => {
    localStorage.setItem(
      STORAGE.creatorUnlocks,
      JSON.stringify({ demoSubscribed, demoAddedSong, demoSharedApp, demoSharedSpotify })
    );
  }, [demoSubscribed, demoAddedSong, demoSharedApp, demoSharedSpotify]);

  const refreshLive = async (handle = state.activeHandle) => {
    dispatch({ type: 'SYNC_START' });
    try {
      const platformApi = platformToApi(state.platformUi);
      const searchRes = await fetchStandard<TrackerSearchResponse>(
        `/api/apex/search?platform=${platformApi}&query=${encodeURIComponent(handle)}`
      );
      const canonicalHandle = extractSearchHandle(searchRes.data, handle);
      const encodedHandle = encodeURIComponent(canonicalHandle);
      const [profileRes, sessionsRes, legendRes] = await Promise.all([
        fetchStandard<TrackerProfileResponse>(`/api/apex/profile/${platformApi}/${encodedHandle}`),
        fetchStandard<TrackerSessionsResponse>(`/api/apex/profile/${platformApi}/${encodedHandle}/sessions`),
        fetchStandard<TrackerProfileResponse>(`/api/apex/profile/${platformApi}/${encodedHandle}/segments/legend`)
      ]);

      dispatch({ type: 'SET_ACTIVE_HANDLE', handle: canonicalHandle });
      dispatch({
        type: 'SYNC_SUCCESS',
        payload: {
          profile: normalizeProfile(profileRes.data ?? {}, state.platformUi, canonicalHandle),
          legends: normalizeLegendSegments(legendRes.data),
          sessions: normalizeSessions(sessionsRes.data),
          statusMessage: providerStatusMessage(searchRes, profileRes, sessionsRes, legendRes)
        }
      });
    } catch (error) {
      dispatch({ type: 'SYNC_ERROR', error: liveFallbackMessage(error) });
    }
  };

  useEffect(() => {
    void refreshLive();
    const intervalId = window.setInterval(() => void refreshLive(), 60000);
    const onFocus = () => void refreshLive();
    const onVisibility = () => {
      if (document.visibilityState === 'visible') void refreshLive();
    };
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [state.platformUi]);

  const selectedLegendRecord = state.legends.find((item) => item.id === selectedLegend) ?? state.legends[0];
  const selectedWeaponRecord = state.weapons.find((item) => item.id === selectedWeapon) ?? state.weapons[0];
  const selectedSessionRecord = state.sessions.find((item) => item.id === selectedSession) ?? state.sessions[0];

  const winRate = ((state.profile.totalWins / Math.max(1, state.profile.lifetimeMatches)) * 100).toFixed(1);
  const customLayoutsUnlocked = demoSubscribed && demoAddedSong;
  const extraLayoutSlots = customLayoutsUnlocked ? 1 + Number(demoSharedApp) + Number(demoSharedSpotify) : 0;

  const handleAddFriend = () => {
    const trimmed = searchValue.trim();
    if (!trimmed) return;
    setActiveTab('friends');
    if (friends.some((friend) => friend.toLowerCase() === trimmed.toLowerCase())) return;
    setFriends((current) => [trimmed, ...current]);
  };

  const handleOpenProfile = (handle: string) => {
    const trimmed = handle.trim();
    if (!trimmed) return;
    setSearchValue(trimmed);
    dispatch({ type: 'SET_ACTIVE_HANDLE', handle: trimmed });
    setActiveTab('live');
    void refreshLive(trimmed);
  };

  const handleRemoveFriend = (handle: string) => {
    setFriends((current) => current.filter((item) => item !== handle));
  };

  const apiStatusTone = state.syncError === 'Live Tracker data is unavailable. Using local beta preview data.' ? 'error' : 'warning';

  return (
    <div className="app-shell">
      <AmbientStage />
      <div className="overlay-glow" />
        <AuthPanel /> 
      <header className="header">
        <div className="header-top">
          <div>
            <div className="brand-row">
              <div className="brand-mark">FT</div>
              <div>
                <h1>FalseTech Apex Dashboard v2 Beta</h1>
                <p>
                  {state.profile.username} | live stats | sessions | legends | weapons | squads
                </p>
              </div>
            </div>
          </div>
          <div className="header-actions">
            <button className="button button--gold" onClick={() => void refreshLive()} disabled={state.syncing}>
              {state.syncing ? 'Refreshing...' : 'Refresh Live'}
            </button>
          </div>
        </div>

        <div className="search-row">
          <div className="search-group">
            <select
              className="select"
              value={state.platformUi}
              onChange={(event) => dispatch({ type: 'SET_PLATFORM', platformUi: event.target.value as PlatformUi })}
            >
              <option value="steam">Steam / EA (PC)</option>
              <option value="xbl">Xbox</option>
              <option value="psn">PlayStation</option>
            </select>
            <input
              className="input"
              value={searchValue}
              onChange={(event) => setSearchValue(event.target.value)}
              placeholder="Enter Apex username"
            />
            <button className="button button--purple" onClick={() => handleOpenProfile(searchValue)}>Open</button>
            <button className="button" onClick={handleAddFriend}>Add Friend</button>
          </div>
          <div className="pill-row">
            <Pill tone="gold">Royal purple + gold</Pill>
            <Pill>Live Data</Pill>
            <Pill>Friends</Pill>
            <Pill>Match Notes</Pill>
          </div>
        </div>

        <div className="stats-grid">
          <StatBadge title="Current Rank" value={`${state.profile.currentRank} | ${formatNumber(state.profile.currentRp)} RP`} />
          <StatBadge title="Peak Rank" value={`${state.profile.peakRank} | ${formatNumber(state.profile.peakRp)} RP`} />
          <StatBadge title="Main Legend" value={state.profile.mainLegend} />
          <StatBadge title="Best Loadout" value={state.profile.bestLoadout} />
          <StatBadge title="Win Rate" value={`${winRate}%`} />
        </div>
      </header>

      <TabBar activeTab={activeTab} onSelect={setActiveTab} />

      <main className="main-content">
        <TabPanel tabKey="command" activeTab={activeTab}>
          <div className="grid grid--hero">
            <Card className="hero-card">
              <div className="pill-row">
                <Pill tone="gold">FalseTech Apex Dashboard v2 Beta</Pill>
                <Pill tone="purple">Apex command center</Pill>
              </div>
              <h2>Live Apex command center for profile stats, sessions, and squad decisions</h2>
              <p className="muted-copy">
                This v2 beta keeps the product Apex-first with live profile stats, session review, legends intelligence,
                weapons intelligence, friends, squads, music, creator tools, and settings in one local-first dashboard.
              </p>
              <div className="feature-grid">
                {[
                  'Live profile switching',
                  'Session Review',
                  'Legends intelligence',
                  'Weapons intelligence',
                  'Squads',
                  'Creator Tools'
                ].map((item) => (
                  <div key={item} className="feature-chip">{item}</div>
                ))}
              </div>
            </Card>

            <div className="stack-column">
              <Card><strong>Active profile</strong><p>{state.activeHandle} | {platformLabel(state.platformUi)}</p></Card>
              <Card><strong>Dashboard mode</strong><p>FalseTech Apex Dashboard v2 Beta</p></Card>
              <Card><strong>Last live sync</strong><p>{state.lastSync ? new Date(state.lastSync).toLocaleString() : 'Waiting for first refresh'}</p></Card>
              {state.syncError ? <StatusBanner message={state.syncError} tone={apiStatusTone} /> : null}
              <Card>
                <strong>Best next actions</strong>
                <div className="button-row compact-actions">
                  <button className="button button--purple" onClick={() => setActiveTab('live')}>Check Live Data</button>
                  <button className="button" onClick={() => setActiveTab('sessions')}>Review Sessions</button>
                  <button className="button" onClick={() => setActiveTab('legends')}>Tune Legend Pick</button>
                </div>
              </Card>
            </div>
          </div>
        </TabPanel>

        <TabPanel tabKey="live" activeTab={activeTab}>
          {state.syncError ? <StatusBanner message={state.syncError} tone={apiStatusTone} /> : null}
          <div className="grid grid--split">
            <Card>
              <h3>Live source</h3>
              <p className="muted-copy">This dashboard is built for a secure backend proxy, not direct browser calls to Tracker.</p>
              <div className="code-block">/api/apex/search?platform={platformToApi(state.platformUi)}&query={state.activeHandle}</div>
              <div className="code-block">/api/apex/profile/{platformToApi(state.platformUi)}/{state.activeHandle}</div>
              <div className="code-block">/api/apex/profile/{platformToApi(state.platformUi)}/{state.activeHandle}/sessions</div>
              <div className="code-block">/api/apex/profile/{platformToApi(state.platformUi)}/{state.activeHandle}/segments/legend</div>
              <div className="button-row">
                <button className="button button--purple" onClick={() => void refreshLive()} disabled={state.syncing}>Refresh Now</button>
                <button className="button" onClick={() => dispatch({ type: 'SET_PLATFORM', platformUi: 'steam' })}>Steam / EA</button>
                <button className="button" onClick={() => dispatch({ type: 'SET_PLATFORM', platformUi: 'xbl' })}>Xbox</button>
                <button className="button" onClick={() => dispatch({ type: 'SET_PLATFORM', platformUi: 'psn' })}>PlayStation</button>
              </div>
              <p className="fine-print">Steam users are shown as Steam / EA in the UI, but the backend uses the Tracker-compatible origin route.</p>
            </Card>
            <Card>
              <h3>Refresh rules</h3>
              <div className="stack-column">
                <Info title="On open" text="The dashboard opens on the Apex v2 beta command center and immediately refreshes the active live profile." />
                <Info title="On focus" text="When the tab regains focus, the board refreshes again so visible numbers do not stay stale." />
                <Info title="On friend switch" text="When a friend handle opens, the whole board refreshes around them." />
                <Info title="On timer" text="The board refreshes every 60 seconds while it is open." />
              </div>
            </Card>
          </div>
        </TabPanel>

        <TabPanel tabKey="music" activeTab={activeTab}>
          <div className="grid grid--split">
            <Card>
              <SpotifyMusicPanel
                spotifyUrl={spotifyEmbedUrl}
                enabled={musicEnabled}
                visible={musicVisible}
                onEnabledChange={setMusicEnabled}
                onVisibleChange={setMusicVisible}
                onSave={setSpotifyEmbedUrl}
              />
            </Card>
            <Card>
              <h3>Music behavior</h3>
              <div className="stack-column">
                <Info title="No OAuth" text="Public Spotify embeds only." />
                <Info title="No keys" text="No Spotify API key is needed." />
                <Info title="Control" text="Hide, show, or disable anytime." />
              </div>
            </Card>
          </div>
        </TabPanel>

        <TabPanel tabKey="friends" activeTab={activeTab}>
          <div className="grid grid--split">
            <Card>
              <h3>Friend list</h3>
              <p className="muted-copy">No screenshots. No files. Just usernames and live refresh.</p>
              <div className="friend-add-row">
                <input className="input" value={searchValue} onChange={(event) => setSearchValue(event.target.value)} placeholder="Add Apex username" />
                <button className="button button--gold" onClick={handleAddFriend}>Add</button>
              </div>
              {friends.length === 0 ? (
                <div className="empty-box">No friends added yet.</div>
              ) : (
                <div className="friend-list">
                  {friends.map((friend) => (
                    <div key={friend} className="friend-chip">
                      <button onClick={() => handleOpenProfile(friend)}>{friend}</button>
                      <button onClick={() => handleRemoveFriend(friend)} aria-label={`Remove ${friend}`}>x</button>
                    </div>
                  ))}
                </div>
              )}
            </Card>
            <Card>
              <h3>Friend flow</h3>
              <div className="stack-column">
                <Info title="Step 1" text="Type a friend's Apex username once and add it to the list." />
                <Info title="Step 2" text="Click the username whenever you want to switch the board to that live profile." />
                <Info title="Step 3" text="The dashboard refreshes that live profile automatically, just like your own." />
                <Info title="Result" text="The app stays focused on Apex profile switching, session review, and squad context." />
              </div>
            </Card>
          </div>
        </TabPanel>

        <TabPanel tabKey="squads" activeTab={activeTab}>
          <div className="three-up-grid">
            {SQUADS.map((squad) => (
              <Card key={squad.name}>
                <h3>{squad.name}</h3>
                <p className="muted-copy">{squad.purpose}</p>
                <div className="pill-row">
                  {squad.members.map((member) => <Pill key={member}>{member}</Pill>)}
                </div>
              </Card>
            ))}
          </div>
        </TabPanel>

        <TabPanel tabKey="creator" activeTab={activeTab}>
          <div className="grid grid--split">
            <Card>
              <h3>Layout access model</h3>
              <div className="metric-grid">
                <MetricTile label="Beta command center" value="FalseTech Apex v2" />
                <MetricTile label="Saved custom layout slots" value={extraLayoutSlots} />
              </div>
              <div className="stack-column">
                <Info title="Core view" text="The beta starts with live stats, sessions, legends, weapons, friends, squads, music, creator tools, and settings." />
                <Info title="Custom layout unlock" text="Custom layout building can unlock after creator actions such as Spotify subscribe and playlist add events." />
                <Info title="More saved layouts" text="Sharing the app or Spotify channel can unlock more saved layout slots in the beta logic." />
              </div>
            </Card>
            <Card>
              <h3>Preview unlock controls</h3>
              <div className="toggle-stack">
                <Toggle label="Demo: Spotify subscribed" checked={demoSubscribed} onToggle={() => setDemoSubscribed((value) => !value)} />
                <Toggle label="Demo: Added one song to playlist" checked={demoAddedSong} onToggle={() => setDemoAddedSong((value) => !value)} />
                <Toggle label="Demo: Shared this app" checked={demoSharedApp} onToggle={() => setDemoSharedApp((value) => !value)} />
                <Toggle label="Demo: Shared Spotify channel" checked={demoSharedSpotify} onToggle={() => setDemoSharedSpotify((value) => !value)} />
              </div>
              <div className="unlock-state">
                Custom layouts: <strong>{customLayoutsUnlocked ? 'Unlocked' : 'Locked'}</strong>
              </div>
            </Card>
          </div>
        </TabPanel>

        <TabPanel tabKey="performance" activeTab={activeTab}>
          <div className="grid grid--split">
            <div className="three-up-grid compact-grid">
              <Card><MetricTile label="FPS Target" value={`${fpsTarget} FPS`} /></Card>
              <Card><MetricTile label="Latency Target" value={`${latencyTarget} ms`} /></Card>
              <Card><MetricTile label="Display Cap" value={`${displayCap} Hz`} /></Card>
            </div>
            <Card>
              <h3>Performance command shell</h3>
              <div className="slider-stack">
                <Range label="FPS Target" value={fpsTarget} min={120} max={360} onChange={setFpsTarget} />
                <Range label="Latency Target" value={latencyTarget} min={20} max={80} onChange={setLatencyTarget} />
                <Range label="Display Cap" value={displayCap} min={120} max={240} onChange={setDisplayCap} step={10} />
              </div>
              <div className="preset-grid">
                {[
                  ['Display mode', 'Fullscreen'],
                  ['Reflex', 'Enabled + Boost'],
                  ['Streaming', 'Creator-safe'],
                  ['Network', 'Ping and jitter checks only']
                ].map(([label, value]) => <MetricTile key={label} label={label} value={value} />)}
              </div>
            </Card>
          </div>
        </TabPanel>

        <TabPanel tabKey="legends" activeTab={activeTab}>
          <div className="grid grid--split-wide">
            <div className="card-grid">
              {state.legends.map((legend) => (
                <button
                  key={legend.id}
                  className={`select-card ${selectedLegendRecord.id === legend.id ? 'selected' : ''}`}
                  onClick={() => {
                    setSelectedLegend(legend.id);
                    setActiveTab('legends');
                  }}
                >
                  <strong>{legend.name}</strong>
                  <span>{legend.role}</span>
                  <p>{legend.note}</p>
                </button>
              ))}
            </div>
            <Card>
              <h3>{selectedLegendRecord.name} | {selectedLegendRecord.fit}/100 fit</h3>
              <div className="stack-column">
                <Info title="Passive" text={selectedLegendRecord.passive} />
                <Info title="Tactical" text={selectedLegendRecord.tactical} />
                <Info title="Ultimate" text={selectedLegendRecord.ultimate} />
                <div className="pill-row">{selectedLegendRecord.strengths.map((value) => <Pill key={value}>{value}</Pill>)}</div>
              </div>
            </Card>
          </div>
        </TabPanel>

        <TabPanel tabKey="weapons" activeTab={activeTab}>
          <div className="grid grid--split-wide">
            <div className="stack-column">
              <div className="card-grid">
                {state.weapons.map((weapon) => (
                  <button
                    key={weapon.id}
                    className={`select-card ${selectedWeaponRecord.id === weapon.id ? 'selected' : ''}`}
                    onClick={() => {
                      setSelectedWeapon(weapon.id);
                      setActiveTab('weapons');
                    }}
                  >
                    <strong>{weapon.name}</strong>
                    <span>{weapon.class} | {weapon.ammo}</span>
                    <p>{weapon.note}</p>
                  </button>
                ))}
              </div>
              <Card>
                <h3>Personal weapon fit</h3>
                <WeaponBarChart weapons={state.weapons} />
              </Card>
            </div>
            <Card>
              <h3>{selectedWeaponRecord.name} | {selectedWeaponRecord.tier} tier</h3>
              <div className="metric-grid">
                <MetricTile label="Range" value={selectedWeaponRecord.range} />
                <MetricTile label="Fit" value={`${selectedWeaponRecord.fit}/100`} />
                <MetricTile label="Tier" value={selectedWeaponRecord.tier} />
              </div>
              <div className="stack-column">
                <div className="pill-row">{selectedWeaponRecord.attachments.map((item) => <Pill key={item}>{item}</Pill>)}</div>
                <div className="pill-row">{selectedWeaponRecord.strengths.map((item) => <Pill tone="gold" key={item}>{item}</Pill>)}</div>
                <Info title="Weakness" text={selectedWeaponRecord.weakness} />
                <Info title="Why it matters" text={selectedWeaponRecord.note} />
              </div>
            </Card>
          </div>
        </TabPanel>

        <TabPanel tabKey="sessions" activeTab={activeTab}>
          <div className="grid grid--split-wide">
            <div className="stack-column">
              {state.sessions.map((session) => (
                <button
                  key={session.id}
                  className={`session-card ${selectedSessionRecord.id === session.id ? 'selected' : ''}`}
                  onClick={() => {
                    setSelectedSession(session.id);
                    setActiveTab('sessions');
                  }}
                >
                  <div className="session-card__top">
                    <strong>{session.legend}</strong>
                    <span className={session.delta >= 0 ? 'positive' : 'negative'}>
                      {session.delta >= 0 ? '+' : ''}{session.delta} RP
                    </span>
                  </div>
                  <div className="session-card__meta">{session.time} | {session.map} | {session.placement}</div>
                  <p>{session.summary}</p>
                </button>
              ))}
              <Card>
                <h3>Session trend</h3>
                <SessionSparkline sessions={state.sessions} />
              </Card>
            </div>
            <Card>
              <h3>{selectedSessionRecord.legend} | {selectedSessionRecord.time}</h3>
              <div className="metric-grid">
                <MetricTile label="Placement" value={selectedSessionRecord.placement} />
                <MetricTile label="Kills" value={selectedSessionRecord.kills} />
                <MetricTile label="Damage" value={formatNumber(selectedSessionRecord.damage)} />
              </div>
              <div className="stack-column">
                <Info title="Summary" text={selectedSessionRecord.summary} />
                <div className="pill-row">{selectedSessionRecord.causes.map((item) => <Pill key={item}>{item}</Pill>)}</div>
                <Info title="Match Notes" text="Use this review lane for player-owned notes, decisions, and follow-up work after each session." />
              </div>
            </Card>
          </div>
        </TabPanel>

        <TabPanel tabKey="settings" activeTab={activeTab}>
          <div className="grid grid--split">
            <Card>
              <SpotifyMusicPanel
                spotifyUrl={spotifyEmbedUrl}
                enabled={musicEnabled}
                visible={musicVisible}
                mode="settings"
                onEnabledChange={setMusicEnabled}
                onVisibleChange={setMusicVisible}
                onSave={setSpotifyEmbedUrl}
              />
            </Card>
            <Card>
              {state.syncError ? <StatusBanner message={state.syncError} tone={apiStatusTone} /> : null}
              <div className="stack-column">
                <Info title="Tracker API status" text="If approval is pending, 401 or 403 responses keep the local beta preview data visible instead of breaking the dashboard." />
                <Info title="Backend upstream status" text="A 502 means the local backend reached the Worker, but Tracker upstream did not return usable data." />
                <Info title="Fallback data" text="Default profile, legends, weapons, and sessions remain visible until live Tracker access succeeds." />
              </div>
            </Card>
            <Card>
              <h3>Why this product is memorable</h3>
              <div className="stack-column">
                {state.updates.map((item) => (
                  <div key={item.id} className="update-card">
                    <div className="pill-row">
                      <Pill tone="gold">{item.category}</Pill>
                      <Pill tone="purple">{item.priority}</Pill>
                    </div>
                    <strong>{item.title}</strong>
                    <p>{item.summary}</p>
                    <div className="update-card__action">{item.action}</div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </TabPanel>
      </main>
    </div>
  );
}

function Info({ title, text }: { title: string; text: string }) {
  return (
    <div className="info-block">
      <div className="info-block__title">{title}</div>
      <div className="info-block__body">{text}</div>
    </div>
  );
}

function Toggle({ label, checked, onToggle }: { label: string; checked: boolean; onToggle: (value: boolean) => void }) {
  return (
    <button className="toggle-row" onClick={() => onToggle(!checked)}>
      <span>{label}</span>
      <span className={`toggle ${checked ? 'on' : ''}`}>
        <span />
      </span>
    </button>
  );
}

function Range({ label, value, min, max, step = 1, onChange }: { label: string; value: number; min: number; max: number; step?: number; onChange: (value: number) => void }) {
  return (
    <label className="range-row">
      <div className="range-row__header">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

