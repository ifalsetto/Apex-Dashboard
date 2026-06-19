import { useEffect, useMemo, useReducer, useState } from 'react';

type PlatformUi = 'steam' | 'xbl' | 'psn';
type PlatformApi = 'origin' | 'xbl' | 'psn';
type SectionKey =
  | 'overview'
  | 'live'
  | 'music'
  | 'friends'
  | 'squads'
  | 'creator'
  | 'command'
  | 'legends'
  | 'weapons'
  | 'sessions'
  | 'settings';

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
      };
    }
  | { type: 'SYNC_ERROR'; error: string };

type StandardApiResponse<T> = {
  ok: boolean;
  source: 'tracker';
  cached: boolean;
  data?: T;
  error?: { code: string; message: string };
  meta: Record<string, unknown>;
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

type TrackerSearchResponse = {
  data?: Array<{
    platformId?: number;
    platformSlug?: string;
    platformUserHandle?: string;
  }>;
};

const STORAGE = {
  handle: 'falsetech-active-handle-v1',
  platform: 'falsetech-active-platform-v1',
  friends: 'falsetech-friends-v1',
  musicVisible: 'falsetech-music-visible-v1',
  spotifyEmbed: 'falsetech-spotify-embed-v1',
  creatorUnlocks: 'falsetech-creator-unlocks-v1'
};

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
    title: 'Default layout starts every user the same way',
    category: 'Creator',
    priority: 'High',
    summary: 'Every fresh user begins on your branded default layout before custom layouts unlock.',
    action: 'Keep your default board polished because this is the first impression.'
  },
  {
    id: 'u2',
    title: 'Music lane builds creator identity instantly',
    category: 'Music',
    priority: 'High',
    summary: 'Your music on the dashboard by default makes the product feel like your world, not a generic tracker.',
    action: 'Hide from the player card, restore from settings.'
  },
  {
    id: 'u3',
    title: 'Friends and squads stay live-first',
    category: 'Social',
    priority: 'Critical',
    summary: 'The board should feel like the home base for an Apex player, not just a static stats page.',
    action: 'Keep live profile switching and squad surfaces near the top.'
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

const DEFAULT_OPEN: Record<SectionKey, boolean> = {
  overview: true,
  live: true,
  music: true,
  friends: true,
  squads: true,
  creator: true,
  command: true,
  legends: true,
  weapons: true,
  sessions: true,
  settings: true
};

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
        syncError: null,
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

async function fetchStandard<T>(url: string): Promise<StandardApiResponse<T>> {
  const response = await fetch(url);
  const body = (await response.json()) as StandardApiResponse<T>;
  if (!response.ok || !body.ok) {
    throw new Error(body.error?.message ?? 'Request failed');
  }
  return body;
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
  const items = searchPayload?.data ?? [];
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

function Section({
  title,
  description,
  isOpen,
  onToggle,
  children
}: {
  title: string;
  description: string;
  isOpen: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <section className="panel">
      <button className="section-toggle" onClick={onToggle}>
        <div>
          <div className="section-title">{title}</div>
          <div className="section-description">{description}</div>
        </div>
        <div className={`section-chevron ${isOpen ? 'open' : ''}`}>⌄</div>
      </button>
      {isOpen ? <div className="section-body">{children}</div> : null}
    </section>
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
  const [sections, setSections] = useState(DEFAULT_OPEN);
  const [searchValue, setSearchValue] = useState(DEFAULT_PROFILE.username);
  const [friends, setFriends] = useState<string[]>([]);
  const [selectedLegend, setSelectedLegend] = useState(DEFAULT_LEGENDS[0].id);
  const [selectedWeapon, setSelectedWeapon] = useState(DEFAULT_WEAPONS[0].id);
  const [selectedSession, setSelectedSession] = useState(DEFAULT_SESSIONS[0].id);
  const [musicVisible, setMusicVisible] = useState(true);
  const [spotifyEmbedUrl, setSpotifyEmbedUrl] = useState('');
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
    const savedFriends = localStorage.getItem(STORAGE.friends);
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
    if (savedFriends) {
      try {
        const parsed = JSON.parse(savedFriends);
        if (Array.isArray(parsed)) setFriends(parsed);
      } catch {
        // ignore
      }
    }
    if (savedMusicVisible) setMusicVisible(savedMusicVisible === 'true');
    if (savedSpotifyEmbed) setSpotifyEmbedUrl(savedSpotifyEmbed);
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
    localStorage.setItem(STORAGE.friends, JSON.stringify(friends));
  }, [friends]);

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
      const [searchRes, profileRes, sessionsRes, legendRes] = await Promise.all([
        fetchStandard<TrackerSearchResponse>(`/api/apex/search?platform=${platformApi}&query=${encodeURIComponent(handle)}`),
        fetchStandard<TrackerProfileResponse>(`/api/apex/profile/${platformApi}/${encodeURIComponent(handle)}`),
        fetchStandard<TrackerSessionsResponse>(`/api/apex/profile/${platformApi}/${encodeURIComponent(handle)}/sessions`),
        fetchStandard<TrackerProfileResponse>(`/api/apex/profile/${platformApi}/${encodeURIComponent(handle)}/segments/legend`)
      ]);

      const canonicalHandle = extractSearchHandle(searchRes.data, handle);
      dispatch({ type: 'SET_ACTIVE_HANDLE', handle: canonicalHandle });
      dispatch({
        type: 'SYNC_SUCCESS',
        payload: {
          profile: normalizeProfile(profileRes.data ?? {}, state.platformUi, canonicalHandle),
          legends: normalizeLegendSegments(legendRes.data),
          sessions: normalizeSessions(sessionsRes.data)
        }
      });
    } catch (error) {
      dispatch({ type: 'SYNC_ERROR', error: error instanceof Error ? error.message : 'Live refresh failed' });
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

  const searchFilter = searchValue.trim().toLowerCase();
  const filteredLegends = useMemo(
    () => state.legends.filter((legend) => `${legend.name} ${legend.role}`.toLowerCase().includes(searchFilter || '')),
    [state.legends, searchFilter]
  );
  const filteredWeapons = useMemo(
    () => state.weapons.filter((weapon) => `${weapon.name} ${weapon.class} ${weapon.ammo}`.toLowerCase().includes(searchFilter || '')),
    [state.weapons, searchFilter]
  );
  const filteredSessions = useMemo(
    () => state.sessions.filter((session) => `${session.legend} ${session.map} ${session.summary}`.toLowerCase().includes(searchFilter || '')),
    [state.sessions, searchFilter]
  );

  const winRate = ((state.profile.totalWins / Math.max(1, state.profile.lifetimeMatches)) * 100).toFixed(1);
  const customLayoutsUnlocked = demoSubscribed && demoAddedSong;
  const extraLayoutSlots = customLayoutsUnlocked ? 1 + Number(demoSharedApp) + Number(demoSharedSpotify) : 0;

  const handleAddFriend = () => {
    const trimmed = searchValue.trim();
    if (!trimmed) return;
    if (friends.some((friend) => friend.toLowerCase() === trimmed.toLowerCase())) return;
    setFriends((current) => [trimmed, ...current]);
  };

  const handleOpenProfile = (handle: string) => {
    const trimmed = handle.trim();
    if (!trimmed) return;
    setSearchValue(trimmed);
    dispatch({ type: 'SET_ACTIVE_HANDLE', handle: trimmed });
    void refreshLive(trimmed);
  };

  const handleRemoveFriend = (handle: string) => {
    setFriends((current) => current.filter((item) => item !== handle));
  };

  const toggleSection = (key: SectionKey) => setSections((current) => ({ ...current, [key]: !current[key] }));
  const setAllSections = (open: boolean) => setSections(Object.keys(DEFAULT_OPEN).reduce((acc, key) => ({ ...acc, [key]: open }), {} as Record<SectionKey, boolean>));

  return (
    <div className="app-shell">
      <AmbientStage />
      <div className="overlay-glow" />
      <header className="header">
        <div className="header-top">
          <div>
            <div className="brand-row">
              <div className="brand-mark">FT</div>
              <div>
                <h1>FalseTech Apex Elite Dashboard</h1>
                <p>
                  {state.profile.username} • live stats • default layout first • music • squads • creator unlocks
                </p>
              </div>
            </div>
          </div>
          <div className="header-actions">
            <button className="button button--gold" onClick={() => void refreshLive()} disabled={state.syncing}>
              {state.syncing ? 'Refreshing…' : 'Refresh Live'}
            </button>
            <button className="button" onClick={() => setAllSections(true)}>Expand All</button>
            <button className="button" onClick={() => setAllSections(false)}>Collapse All</button>
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
            <Pill>Default layout first</Pill>
            <Pill>Music on by default</Pill>
            <Pill>Live friends</Pill>
          </div>
        </div>

        <div className="stats-grid">
          <StatBadge title="Current Rank" value={`${state.profile.currentRank} • ${formatNumber(state.profile.currentRp)} RP`} />
          <StatBadge title="Peak Rank" value={`${state.profile.peakRank} • ${formatNumber(state.profile.peakRp)} RP`} />
          <StatBadge title="Main Legend" value={state.profile.mainLegend} />
          <StatBadge title="Best Loadout" value={state.profile.bestLoadout} />
          <StatBadge title="Win Rate" value={`${winRate}%`} />
        </div>
      </header>

      <main className="main-content">
        <Section title="Default Layout Overview" description="Every new dashboard starts on your branded default layout." isOpen={sections.overview} onToggle={() => toggleSection('overview')}>
          <div className="grid grid--hero">
            <Card className="hero-card">
              <div className="pill-row">
                <Pill tone="gold">FalseTech Default Layout</Pill>
                <Pill tone="purple">Apex-first creator home</Pill>
              </div>
              <h2>Live Apex home base with your creator identity built in</h2>
              <p className="muted-copy">
                This trial build keeps the product Apex-first while adding your music lane, squads, creator unlocks, and social identity.
                New users start on your actual default layout so the product always feels like your board first.
              </p>
              <div className="feature-grid">
                {[
                  'Live profile switching',
                  'Music lane on by default',
                  'Hide music from player',
                  'Re-enable from settings',
                  'Squads as a first-class surface',
                  'Creator unlock preview flow'
                ].map((item) => (
                  <div key={item} className="feature-chip">{item}</div>
                ))}
              </div>
            </Card>

            <div className="stack-column">
              <Card><strong>Active profile</strong><p>{state.activeHandle} • {platformLabel(state.platformUi)}</p></Card>
              <Card><strong>Default layout</strong><p>FalseTech Default Layout</p></Card>
              <Card><strong>Last live sync</strong><p>{state.lastSync ? new Date(state.lastSync).toLocaleString() : 'Waiting for first refresh'}</p></Card>
              {state.syncError ? <Card><strong>Live status</strong><p>{state.syncError}</p></Card> : null}
            </div>
          </div>
        </Section>

        <Section title="Live Data Engine" description="Open a profile, switch a friend, and the whole board refreshes around them." isOpen={sections.live} onToggle={() => toggleSection('live')}>
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
              <p className="fine-print">Steam users are shown as Steam / EA in the UI, but the backend uses the Tracker-compatible PC route.</p>
            </Card>
            <Card>
              <h3>Refresh rules</h3>
              <div className="stack-column">
                <Info title="On open" text="The dashboard opens on your default layout and immediately refreshes the active live profile." />
                <Info title="On focus" text="When the tab regains focus, the board refreshes again so visible numbers do not stay stale." />
                <Info title="On friend switch" text="When a friend handle opens, the whole board refreshes around them." />
                <Info title="On timer" text="The board refreshes every 60 seconds while it is open." />
              </div>
            </Card>
          </div>
        </Section>

        <Section title="Music Lane" description="Your music sits on the dashboard by default and can be hidden from the player itself." isOpen={sections.music} onToggle={() => toggleSection('music')}>
          <div className="grid grid--split">
            <Card>
              <div className="card-header-inline">
                <div>
                  <h3>Default creator music player</h3>
                  <p className="muted-copy">Visible by default on first load. Hide from here. Restore from Settings.</p>
                </div>
                {musicVisible ? <button className="button" onClick={() => setMusicVisible(false)}>Hide Player</button> : null}
              </div>
              {musicVisible ? (
                spotifyEmbedUrl ? (
                  <div className="spotify-wrap">
                    <iframe
                      title="FalseTech Spotify Player"
                      src={spotifyEmbedUrl}
                      width="100%"
                      height="352"
                      allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                      loading="lazy"
                    />
                  </div>
                ) : (
                  <div className="music-placeholder">
                    <h4>Spotify embed lane ready</h4>
                    <p>
                      Paste your real Spotify embed URL in Settings to make the music lane fully live for the preview.
                    </p>
                    <div className="pill-row">
                      <Pill>Music on by default</Pill>
                      <Pill>Hide here, restore in settings</Pill>
                    </div>
                  </div>
                )
              ) : (
                <div className="music-placeholder muted-state">
                  Music player hidden. Go to <strong>Settings</strong> to re-enable it.
                </div>
              )}
            </Card>
            <Card>
              <h3>Music behavior</h3>
              <div className="stack-column">
                <Info title="Default" text="The music player appears on the dashboard by default because your music is part of the product identity." />
                <Info title="Hide" text="A user can hide the player directly from the music card without leaving the dashboard." />
                <Info title="Restore" text="To bring it back, the user goes into Settings and turns the music lane back on." />
              </div>
            </Card>
          </div>
        </Section>

        <Section title="Friends Live Profiles" description="Friends are just saved usernames. Click one and the entire board becomes their live dashboard." isOpen={sections.friends} onToggle={() => toggleSection('friends')}>
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
                      <button onClick={() => handleRemoveFriend(friend)} aria-label={`Remove ${friend}`}>×</button>
                    </div>
                  ))}
                </div>
              )}
            </Card>
            <Card>
              <h3>Friend flow</h3>
              <div className="stack-column">
                <Info title="Step 1" text="Type a friend’s Apex username once and add it to the list." />
                <Info title="Step 2" text="Click the username whenever you want to switch the board to that live profile." />
                <Info title="Step 3" text="The dashboard refreshes that live profile automatically, just like your own." />
                <Info title="Result" text="The app feels socially useful without becoming a generic social-media clone." />
              </div>
            </Card>
          </div>
        </Section>

        <Section title="Squads" description="Squads make the dashboard feel like a home base for teams, not just a stat pane for one player." isOpen={sections.squads} onToggle={() => toggleSection('squads')}>
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
        </Section>

        <Section title="Creator Unlocks" description="Your default layout is the starting state. Custom layouts and extra saved templates unlock later." isOpen={sections.creator} onToggle={() => toggleSection('creator')}>
          <div className="grid grid--split">
            <Card>
              <h3>Layout access model</h3>
              <div className="metric-grid">
                <MetricTile label="Starting layout" value="FalseTech Default Layout" />
                <MetricTile label="Saved custom layout slots" value={extraLayoutSlots} />
              </div>
              <div className="stack-column">
                <Info title="Default rule" text="Every new dashboard opens on your actual default layout first so users know what the product looks like at its core." />
                <Info title="Custom layout unlock" text="Custom layout building unlocks only after the preview logic marks Spotify subscribed and song added to playlist." />
                <Info title="More saved templates" text="Sharing the app or your Spotify channel unlocks more saved layout slots in the preview logic." />
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
        </Section>

        <Section title="Competitive Command" description="Your optimizer DNA still sits inside the stronger creator and social shell." isOpen={sections.command} onToggle={() => toggleSection('command')}>
          <div className="grid grid--split">
            <div className="three-up-grid compact-grid">
              <Card><MetricTile label="FPS Target" value={`${fpsTarget} FPS`} /></Card>
              <Card><MetricTile label="Latency Target" value={`${latencyTarget} ms`} /></Card>
              <Card><MetricTile label="Display Cap" value={`${displayCap} Hz`} /></Card>
            </div>
            <Card>
              <h3>Default layout command shell</h3>
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
                  ['Visibility bias', 'Competitive']
                ].map(([label, value]) => <MetricTile key={label} label={label} value={value} />)}
              </div>
            </Card>
          </div>
        </Section>

        <Section title="Legends Intel" description="Legend detail stays inside the same dashboard, no page drift." isOpen={sections.legends} onToggle={() => toggleSection('legends')}>
          <div className="grid grid--split-wide">
            <div className="card-grid">
              {filteredLegends.map((legend) => (
                <button
                  key={legend.id}
                  className={`select-card ${selectedLegendRecord.id === legend.id ? 'selected' : ''}`}
                  onClick={() => setSelectedLegend(legend.id)}
                >
                  <strong>{legend.name}</strong>
                  <span>{legend.role}</span>
                  <p>{legend.note}</p>
                </button>
              ))}
            </div>
            <Card>
              <h3>{selectedLegendRecord.name} • {selectedLegendRecord.fit}/100 fit</h3>
              <div className="stack-column">
                <Info title="Passive" text={selectedLegendRecord.passive} />
                <Info title="Tactical" text={selectedLegendRecord.tactical} />
                <Info title="Ultimate" text={selectedLegendRecord.ultimate} />
                <div className="pill-row">{selectedLegendRecord.strengths.map((value) => <Pill key={value}>{value}</Pill>)}</div>
              </div>
            </Card>
          </div>
        </Section>

        <Section title="Weapons Lab" description="Weapon detail stays live-profile backed and visually active." isOpen={sections.weapons} onToggle={() => toggleSection('weapons')}>
          <div className="grid grid--split-wide">
            <div className="stack-column">
              <div className="card-grid">
                {filteredWeapons.map((weapon) => (
                  <button
                    key={weapon.id}
                    className={`select-card ${selectedWeaponRecord.id === weapon.id ? 'selected' : ''}`}
                    onClick={() => setSelectedWeapon(weapon.id)}
                  >
                    <strong>{weapon.name}</strong>
                    <span>{weapon.class} • {weapon.ammo}</span>
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
              <h3>{selectedWeaponRecord.name} • {selectedWeaponRecord.tier} tier</h3>
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
        </Section>

        <Section title="Sessions Review" description="Session history follows the active live profile and stays visually readable." isOpen={sections.sessions} onToggle={() => toggleSection('sessions')}>
          <div className="grid grid--split-wide">
            <div className="stack-column">
              {filteredSessions.map((session) => (
                <button
                  key={session.id}
                  className={`session-card ${selectedSessionRecord.id === session.id ? 'selected' : ''}`}
                  onClick={() => setSelectedSession(session.id)}
                >
                  <div className="session-card__top">
                    <strong>{session.legend}</strong>
                    <span className={session.delta >= 0 ? 'positive' : 'negative'}>
                      {session.delta >= 0 ? '+' : ''}{session.delta} RP
                    </span>
                  </div>
                  <div className="session-card__meta">{session.time} • {session.map} • {session.placement}</div>
                  <p>{session.summary}</p>
                </button>
              ))}
              <Card>
                <h3>Session trend</h3>
                <SessionSparkline sessions={state.sessions} />
              </Card>
            </div>
            <Card>
              <h3>{selectedSessionRecord.legend} • {selectedSessionRecord.time}</h3>
              <div className="metric-grid">
                <MetricTile label="Placement" value={selectedSessionRecord.placement} />
                <MetricTile label="Kills" value={selectedSessionRecord.kills} />
                <MetricTile label="Damage" value={formatNumber(selectedSessionRecord.damage)} />
              </div>
              <div className="stack-column">
                <Info title="Summary" text={selectedSessionRecord.summary} />
                <div className="pill-row">{selectedSessionRecord.causes.map((item) => <Pill key={item}>{item}</Pill>)}</div>
              </div>
            </Card>
          </div>
        </Section>

        <Section title="Settings" description="Music restore, Spotify embed URL, and preview unlock controls live here." isOpen={sections.settings} onToggle={() => toggleSection('settings')}>
          <div className="grid grid--split">
            <Card>
              <h3>Music settings</h3>
              <div className="toggle-stack">
                <Toggle label="Show default music player" checked={musicVisible} onToggle={() => setMusicVisible((current) => !current)} />
              </div>
              <div className="input-stack">
                <label className="input-label">Spotify embed URL</label>
                <input
                  className="input"
                  value={spotifyEmbedUrl}
                  onChange={(event) => setSpotifyEmbedUrl(event.target.value)}
                  placeholder="Paste Spotify embed URL here"
                />
                <div className="fine-print">Add your real Spotify embed URL here to make the music lane fully live for the preview.</div>
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
        </Section>
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
