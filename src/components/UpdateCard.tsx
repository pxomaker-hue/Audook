import React, { useCallback, useEffect, useState } from 'react';
import { checkForUpdate, installUpdate, UpdateInfo, APP_VERSION } from '../updates';

interface Props {
  style?: React.CSSProperties;
}

const buttonStyle: React.CSSProperties = {
  background: 'var(--primary)', color: '#fff', border: 'none', padding: '10px 18px',
  borderRadius: '999px', cursor: 'pointer', fontSize: '13px', fontWeight: 600,
};

const UpdateCard: React.FC<Props> = ({ style }) => {
  const [info, setInfo] = useState<UpdateInfo | null>(null);
  const [busy, setBusy] = useState<'check' | 'install' | null>(null);
  const [error, setError] = useState('');

  const check = useCallback(async () => {
    setBusy('check');
    setError('');
    try {
      setInfo(await checkForUpdate());
    } catch (e: any) {
      setInfo(null);
      setError(e?.message || 'Vérification impossible');
    } finally {
      setBusy(null);
    }
  }, []);

  useEffect(() => { check(); }, [check]);

  const install = async () => {
    if (!info) return;
    setBusy('install');
    setError('');
    try {
      await installUpdate(info);
    } catch (e: any) {
      setError(e?.message || "Installation impossible");
    } finally {
      setBusy(null);
    }
  };

  const secondary: React.CSSProperties = { color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '10px' };

  return (
    <div style={style}>
      <h2 style={{ color: 'var(--primary)', marginBottom: '15px' }}>Mise à jour</h2>
      <p style={secondary}>Version installée : <strong>{APP_VERSION ? `v${APP_VERSION}` : info?.current || '?'}</strong></p>
      {info && !info.available && <p style={secondary}>Audook est à jour (v{info.latest}).</p>}
      {info?.available && (
        <>
          <p style={secondary}>La version <strong>v{info.latest}</strong> est disponible.</p>
          {info.notes && <pre style={{ ...secondary, whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>{info.notes}</pre>}
          {info.selfUpdate ? (
            <button style={{ ...buttonStyle, marginRight: '10px' }} onClick={install} disabled={busy !== null}>
              {busy === 'install' ? 'Téléchargement…' : 'Télécharger et installer'}
            </button>
          ) : (
            <p style={secondary}>Ce serveur (conteneur Docker) se met à jour à la main : reconstruisez l'image (voir le README).</p>
          )}
        </>
      )}
      {error && <p role="alert" style={{ color: 'var(--danger, #e5484d)', fontSize: '13px', marginBottom: '10px' }}>{error}</p>}
      <button style={{ ...buttonStyle, background: 'var(--surface-muted)', color: 'var(--text-primary)' }} onClick={check} disabled={busy !== null}>
        {busy === 'check' ? 'Vérification…' : 'Rechercher une mise à jour'}
      </button>
    </div>
  );
};

export default UpdateCard;
