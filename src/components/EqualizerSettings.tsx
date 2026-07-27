import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Pencil, Trash2, Check, ChevronDown } from 'lucide-react';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://127.0.0.1:5000/api';

// VLC's equalizer has a fixed 10-band layout, one octave apart - this order
// matches the `bands` array index for every preset (see EqualizerPreset in
// app/database/models.py and the VLC AudioEqualizer API it wraps).
const BAND_LABELS = ['31', '62', '125', '250', '500', '1k', '2k', '4k', '8k', '16k'];
const BAND_MIN = -20;
const BAND_MAX = 20;
const PREAMP_MIN = -20;
const PREAMP_MAX = 20;

interface Preset {
  id: string;
  name: string;
  bands: number[];
  preamp: number;
  is_builtin: boolean;
}

const emptyForm = () => ({ name: '', bands: Array(10).fill(0), preamp: 0 });

const cardStyle: React.CSSProperties = {
  backgroundColor: 'var(--surface)',
  borderRadius: 'var(--radius-md)',
  boxShadow: 'var(--shadow-pop)',
  padding: '30px',
  maxWidth: '600px',
  marginTop: '30px'
};

const buttonStyle: React.CSSProperties = {
  background: 'var(--primary)',
  color: 'var(--secondary)',
  border: 'none',
  padding: '11px 22px',
  borderRadius: '999px',
  cursor: 'pointer',
  fontSize: '14px',
  fontWeight: 700
};

const secondaryButtonStyle: React.CSSProperties = {
  background: 'var(--surface-muted)',
  color: 'var(--text-primary)',
  border: 'none',
  padding: '9px 16px',
  borderRadius: '999px',
  cursor: 'pointer',
  fontSize: '13px',
  fontWeight: 600
};

const iconButtonStyle: React.CSSProperties = {
  ...secondaryButtonStyle,
  padding: '9px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center'
};

const EqualizerSettings: React.FC = () => {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [activePresetId, setActivePresetId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | 'new' | null>(null);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [presetsRes, stateRes] = await Promise.all([
        axios.get(`${API_BASE}/equalizer/presets`),
        axios.get(`${API_BASE}/player/state`)
      ]);
      setPresets(presetsRes.data);
      setActivePresetId(stateRes.data.equalizer_preset_id ?? null);
    } catch (err) {
      console.error('Failed to load equalizer presets:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleApply = async (presetId: string | null) => {
    setActivePresetId(presetId);
    try {
      await axios.post(`${API_BASE}/player/equalizer`, { preset_id: presetId });
    } catch (err) {
      console.error('Failed to apply equalizer preset:', err);
    }
  };

  const startCreate = () => {
    setForm(emptyForm());
    setEditingId('new');
    setError(null);
  };

  const startEdit = (preset: Preset) => {
    setForm({ name: preset.name, bands: [...preset.bands], preamp: preset.preamp });
    setEditingId(preset.id);
    setError(null);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setError(null);
  };

  const handleBandChange = (index: number, value: number) => {
    setForm(prev => {
      const bands = [...prev.bands];
      bands[index] = value;
      return { ...prev, bands };
    });
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      setError('Le nom est requis');
      return;
    }
    try {
      setSaving(true);
      setError(null);
      if (editingId === 'new') {
        await axios.post(`${API_BASE}/equalizer/presets`, form);
      } else {
        await axios.put(`${API_BASE}/equalizer/presets/${editingId}`, form);
      }
      setEditingId(null);
      await load();
    } catch (err: any) {
      setError(err?.response?.data?.error || 'Impossible d\'enregistrer le préréglage');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (preset: Preset) => {
    if (!window.confirm(`Supprimer le préréglage "${preset.name}" ?`)) return;
    try {
      await axios.delete(`${API_BASE}/equalizer/presets/${preset.id}`);
      await load();
    } catch (err) {
      console.error('Failed to delete equalizer preset:', err);
    }
  };

  return (
    <div style={cardStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ color: 'var(--primary)', margin: 0 }}>Égaliseur</h2>
        {editingId === null && (
          <button onClick={startCreate} className="cta-button" style={buttonStyle}>
            + Nouveau préréglage
          </button>
        )}
      </div>

      {loading ? (
        <p style={{ color: 'var(--text-secondary)' }}>Chargement...</p>
      ) : (
        <>
          {editingId === null && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: editingId === null ? 0 : '20px' }}>
              <div
                onClick={() => handleApply(null)}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  backgroundColor: 'var(--surface-muted)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '14px 18px',
                  cursor: 'pointer',
                  outline: activePresetId === null ? '2px solid var(--primary)' : 'none'
                }}
              >
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>Désactivé</span>
                {activePresetId === null && <Check size={16} color="var(--primary)" />}
              </div>

              {presets.map(preset => {
                const isExpanded = expandedId === preset.id;
                return (
                  <div
                    key={preset.id}
                    style={{
                      backgroundColor: 'var(--surface-muted)',
                      borderRadius: 'var(--radius-sm)',
                      outline: activePresetId === preset.id ? '2px solid var(--primary)' : 'none',
                      overflow: 'hidden'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px' }}>
                      <span
                        onClick={() => handleApply(preset.id)}
                        style={{ color: 'var(--text-primary)', fontWeight: 600, cursor: 'pointer', flex: 1 }}
                      >
                        {preset.name}
                        {preset.is_builtin && (
                          <span style={{ color: 'var(--text-tertiary)', fontSize: '12px', fontWeight: 400 }}> (intégré)</span>
                        )}
                      </span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {activePresetId === preset.id && <Check size={16} color="var(--primary)" />}
                        {!preset.is_builtin && (
                          <>
                            <button onClick={() => startEdit(preset)} style={iconButtonStyle} title="Modifier">
                              <Pencil size={14} />
                            </button>
                            <button
                              onClick={() => handleDelete(preset)}
                              style={{ ...iconButtonStyle, color: '#ff6b6b' }}
                              title="Supprimer"
                            >
                              <Trash2 size={14} />
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => setExpandedId(isExpanded ? null : preset.id)}
                          style={iconButtonStyle}
                          title={isExpanded ? 'Masquer les réglages' : 'Voir les réglages'}
                        >
                          <ChevronDown
                            size={14}
                            style={{ transition: 'transform 0.2s', transform: isExpanded ? 'rotate(180deg)' : 'none' }}
                          />
                        </button>
                      </div>
                    </div>

                    {isExpanded && (
                      <div style={{ padding: '4px 18px 18px' }}>
                        <div style={{ fontSize: '11px', color: 'var(--text-tertiary)', marginBottom: '10px' }}>
                          Préamplification : {preset.preamp > 0 ? '+' : ''}{preset.preamp} dB
                        </div>
                        <div className="eq-band-grid eq-band-grid--readonly">
                          {BAND_LABELS.map((label, i) => {
                            const value = preset.bands[i] ?? 0;
                            const heightPct = ((value - BAND_MIN) / (BAND_MAX - BAND_MIN)) * 100;
                            return (
                              <div key={label} className="eq-band-column">
                                <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', minHeight: '14px' }}>
                                  {value > 0 ? '+' : ''}{value}
                                </span>
                                <div className="eq-band-bar-track">
                                  <div className="eq-band-bar-fill" style={{ height: `${heightPct}%` }} />
                                </div>
                                <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{label}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {editingId !== null && (
            <div style={{ backgroundColor: 'var(--surface-muted)', borderRadius: 'var(--radius-sm)', padding: '20px' }}>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-primary)', fontSize: '13px', fontWeight: 600 }}>
                  Nom
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Mon préréglage"
                  style={{
                    width: '100%',
                    padding: '11px 16px',
                    backgroundColor: 'var(--surface)',
                    color: 'var(--text-primary)',
                    border: 'none',
                    borderRadius: '999px',
                    fontFamily: 'inherit',
                    fontSize: '14px'
                  }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '8px', color: 'var(--text-primary)', fontSize: '13px', fontWeight: 600 }}>
                  Préamplification ({form.preamp > 0 ? '+' : ''}{form.preamp} dB)
                </label>
                <input
                  type="range"
                  min={PREAMP_MIN}
                  max={PREAMP_MAX}
                  step={0.5}
                  value={form.preamp}
                  onChange={(e) => setForm(prev => ({ ...prev, preamp: parseFloat(e.target.value) }))}
                  style={{ width: '100%', cursor: 'pointer' }}
                />
              </div>

              <label style={{ display: 'block', marginBottom: '12px', color: 'var(--text-primary)', fontSize: '13px', fontWeight: 600 }}>
                Bandes de fréquence
              </label>
              <div className="eq-band-grid">
                {BAND_LABELS.map((label, i) => (
                  <div key={label} className="eq-band-column">
                    <span style={{ fontSize: '11px', color: 'var(--text-tertiary)', minHeight: '14px' }}>
                      {form.bands[i] > 0 ? '+' : ''}{form.bands[i]}
                    </span>
                    <div className="eq-band-slider-wrap">
                      <input
                        type="range"
                        className="eq-band-slider"
                        min={BAND_MIN}
                        max={BAND_MAX}
                        step={0.5}
                        value={form.bands[i]}
                        onChange={(e) => handleBandChange(i, parseFloat(e.target.value))}
                      />
                    </div>
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{label}</span>
                  </div>
                ))}
              </div>

              {error && <p style={{ color: '#ff6b6b', fontSize: '13px', marginBottom: '15px' }}>{error}</p>}

              <div style={{ display: 'flex', gap: '10px' }}>
                <button onClick={handleSave} disabled={saving} className="cta-button" style={{ ...buttonStyle, opacity: saving ? 0.6 : 1 }}>
                  {saving ? 'Enregistrement...' : 'Enregistrer'}
                </button>
                <button onClick={cancelEdit} className="cta-button" style={secondaryButtonStyle}>
                  Annuler
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default EqualizerSettings;
