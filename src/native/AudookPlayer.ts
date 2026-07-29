import { registerPlugin } from '@capacitor/core';

export interface AudookPlayerPlugin {
  play(options: { url: string; title: string; cover?: string; positionMs?: number }): Promise<void>;
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
}

// Native Kotlin plugin (android/app/src/main/java/com/audook/app/AudookPlayerPlugin.kt) -
// only registered/functional inside the Capacitor Android shell.
const AudookPlayer = registerPlugin<AudookPlayerPlugin>('AudookPlayer');

export default AudookPlayer;
