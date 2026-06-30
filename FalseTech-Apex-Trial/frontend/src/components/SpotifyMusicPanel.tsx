import { useEffect, useMemo, useState } from 'react';

const SPOTIFY_TYPES = new Set(['playlist', 'artist', 'album', 'track']);

type SpotifyMusicPanelMode = 'player' | 'settings';

type SpotifyMusicPanelProps = {
  spotifyUrl: string;
  enabled: boolean;
  visible: boolean;
  mode?: SpotifyMusicPanelMode;
  onEnabledChange: (enabled: boolean) => void;
  onVisibleChange: (visible: boolean) => void;
  onSave: (spotifyUrl: string) => void;
};

function cleanSpotifyId(value: string | undefined): string {
  return (value ?? '').replace(/[^A-Za-z0-9]/g, '');
}

function embedUrlFor(spotifyType: string, spotifyId: string): string {
  return `https://open.spotify.com/embed/${spotifyType}/${spotifyId}`;
}

export function normalizeSpotifyEmbedUrl(url: string): string {
  const raw = (url || '').trim();

  if (!raw) return '';

  if (raw.startsWith('spotify:')) {
    const parts = raw.split(':');
    const spotifyType = parts[1];
    const spotifyId = cleanSpotifyId(parts[2]);

    return spotifyType && SPOTIFY_TYPES.has(spotifyType) && spotifyId ? embedUrlFor(spotifyType, spotifyId) : '';
  }

  try {
    const parsed = new URL(raw);
    if (parsed.protocol !== 'https:' || parsed.hostname !== 'open.spotify.com') return '';

    const pathParts = parsed.pathname.split('/').filter(Boolean);
    if (pathParts.length >= 2 && SPOTIFY_TYPES.has(pathParts[0])) {
      const spotifyId = cleanSpotifyId(pathParts[1]);
      return spotifyId ? embedUrlFor(pathParts[0], spotifyId) : '';
    }

    if (pathParts.length >= 3 && pathParts[0] === 'embed' && SPOTIFY_TYPES.has(pathParts[1])) {
      const spotifyId = cleanSpotifyId(pathParts[2]);
      return spotifyId ? embedUrlFor(pathParts[1], spotifyId) : '';
    }
  } catch {
    return '';
  }

  return '';
}

export function spotifyOpenUrlFromEmbed(embedUrl: string): string {
  if (!embedUrl) return '';
  return embedUrl.replace('https://open.spotify.com/embed/', 'https://open.spotify.com/');
}

function spotifyTypeFromEmbed(embedUrl: string): string {
  try {
    const parsed = new URL(embedUrl);
    const [, spotifyType] = parsed.pathname.split('/').filter(Boolean);
    return spotifyType && SPOTIFY_TYPES.has(spotifyType) ? spotifyType : 'embed';
  } catch {
    return 'embed';
  }
}

export function SpotifyMusicPanel({
  spotifyUrl,
  enabled,
  visible,
  mode = 'player',
  onEnabledChange,
  onVisibleChange,
  onSave
}: SpotifyMusicPanelProps) {
  const [draftUrl, setDraftUrl] = useState(spotifyUrl);
  const [saveMessage, setSaveMessage] = useState('');

  useEffect(() => {
    setDraftUrl(spotifyUrl);
  }, [spotifyUrl]);

  const embedUrl = useMemo(() => normalizeSpotifyEmbedUrl(spotifyUrl), [spotifyUrl]);
  const draftEmbedUrl = useMemo(() => normalizeSpotifyEmbedUrl(draftUrl), [draftUrl]);
  const openUrl = spotifyOpenUrlFromEmbed(embedUrl);
  const spotifyType = spotifyTypeFromEmbed(embedUrl);
  const iframeHeight = spotifyType === 'track' ? 152 : 352;
  const hasDraft = Boolean(draftUrl.trim());
  const canSave = !hasDraft || Boolean(draftEmbedUrl);

  const handleSave = () => {
    if (!canSave) {
      setSaveMessage('Use a Spotify playlist, artist, album, or track link.');
      return;
    }

    onSave(draftEmbedUrl);
    setSaveMessage(draftEmbedUrl ? 'Spotify saved.' : 'Spotify cleared.');
  };

  return (
    <section className={`spotify-panel spotify-panel--${mode}`}>
      <div className="spotify-panel__header">
        <div>
          <h3>Music</h3>
          <p className="muted-copy">Spotify embed. No OAuth.</p>
        </div>
        <div className="button-row compact-actions">
          {embedUrl ? (
            <a className="button" href={openUrl} target="_blank" rel="noreferrer">
              Open Spotify
            </a>
          ) : null}
          <button className="button button--gold" type="button" onClick={() => onVisibleChange(!visible)}>
            {visible ? 'Hide' : 'Show'}
          </button>
        </div>
      </div>

      {mode === 'player' ? (
        <div className="spotify-status-grid">
          <div><span>Source</span><strong>Spotify</strong></div>
          <div><span>Mode</span><strong>Embed</strong></div>
          <div><span>Player</span><strong>{enabled && visible ? 'Visible' : 'Hidden'}</strong></div>
        </div>
      ) : null}

      <details className="spotify-settings" open={mode === 'settings' || !embedUrl}>
        <summary>Music Settings</summary>
        <div className="spotify-settings__body">
          <label className="input-label" htmlFor={`spotify-url-${mode}`}>Spotify URL</label>
          <input
            id={`spotify-url-${mode}`}
            className="input"
            value={draftUrl}
            onChange={(event) => {
              setDraftUrl(event.target.value);
              setSaveMessage('');
            }}
            placeholder="Paste playlist, artist, album, or track"
          />
          {hasDraft && !draftEmbedUrl ? (
            <div className="spotify-warning">Unsupported Spotify link.</div>
          ) : null}
          <div className="toggle-stack spotify-toggle-stack">
            <button className="toggle-row" type="button" onClick={() => onEnabledChange(!enabled)}>
              <span>Enable Spotify</span>
              <span className={`toggle ${enabled ? 'on' : ''}`}><span /></span>
            </button>
            <button className="toggle-row" type="button" onClick={() => onVisibleChange(!visible)}>
              <span>Show player</span>
              <span className={`toggle ${visible ? 'on' : ''}`}><span /></span>
            </button>
          </div>
          <button className="button button--purple" type="button" onClick={handleSave}>
            Save Spotify
          </button>
          {saveMessage ? <div className="fine-print">{saveMessage}</div> : null}
        </div>
      </details>

      {mode === 'player' ? (
        <>
          {!enabled ? (
            <div className="music-empty-state muted-state">Spotify panel disabled.</div>
          ) : !embedUrl ? (
            <div className="music-empty-state">
              <h4>Spotify ready</h4>
              <p>Add a playlist, artist, album, or track.</p>
            </div>
          ) : !visible ? (
            <div className="music-empty-state muted-state">Spotify player hidden.</div>
          ) : (
            <div className="spotify-wrap spotify-wrap--compact">
              <iframe
                title="FalseTech Spotify Player"
                src={embedUrl}
                width="100%"
                height={iframeHeight}
                allow="clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                loading="lazy"
              />
            </div>
          )}
        </>
      ) : null}
    </section>
  );
}
