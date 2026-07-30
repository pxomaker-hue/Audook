import { registerPlugin } from '@capacitor/core';

export interface AudookPlayerPlugin {
  // The whole book's chapters are passed as one playlist (instead of a
  // single chapter re-played on every transition) so ExoPlayer can advance
  // through them on its own, entirely natively - the previous one-chapter-
  // at-a-time approach relied on the JS side reacting to an 'ended' event to
  // start the next chapter, which never ran once the WebView was suspended
  // in the background/screen off, silently stopping playback at every
  // chapter boundary.
  play(options: {
    chapters: { url: string; title: string }[];
    startIndex: number;
    cover?: string;
    positionMs?: number;
  }): Promise<void>;
  previousChapter(): Promise<void>;
  nextChapter(): Promise<void>;
  setSpeed(options: { speed: number }): Promise<void>;
  // bands: 10 dB values (null disables the equalizer entirely) - mapped
  // onto whichever bands this device's own Equalizer effect exposes, see
  // AudookPlayerPlugin.kt's DESKTOP_EQ_FREQUENCIES.
  setEqualizer(options: { bands: number[] | null; preamp?: number }): Promise<void>;
  // Per-book EBU-style gain in dB (0 disables it) - positive boosts via
  // LoudnessEnhancer, negative attenuates via the player's own volume.
  setLoudnessGain(options: { gainDb: number }): Promise<void>;
  // preset: one of COMPRESSOR_PRESETS' keys in app/player/vlc_player.py
  // ("leger"/"modere"/"fort"), or null/omitted to disable. Applied via
  // Android's DynamicsProcessing multi-band compressor - a different
  // algorithm than VLC's own "compressor" filter, tuned to land in the same
  // ballpark rather than reproduce it exactly.
  setCompression(options: { preset: string | null }): Promise<void>;
  pause(): Promise<void>;
  resume(): Promise<void>;
  seek(options: { ms: number }): Promise<void>;
  stop(): Promise<void>;
  addListener(
    eventName: 'positionUpdate',
    listenerFunc: (data: { positionMs: number; durationMs: number }) => void
  ): Promise<{ remove: () => void }>;
  addListener(
    eventName: 'stateChange',
    listenerFunc: (data: { isPlaying: boolean }) => void
  ): Promise<{ remove: () => void }>;
  addListener(
    eventName: 'ended',
    listenerFunc: (data: { ended: boolean }) => void
  ): Promise<{ remove: () => void }>;
  addListener(
    eventName: 'chapterChanged',
    listenerFunc: (data: { chapterIndex: number }) => void
  ): Promise<{ remove: () => void }>;
}

// Native Kotlin plugin (android/app/src/main/java/com/audook/app/AudookPlayerPlugin.kt) -
// only registered/functional inside the Capacitor Android shell.
const AudookPlayer = registerPlugin<AudookPlayerPlugin>('AudookPlayer');

export default AudookPlayer;
