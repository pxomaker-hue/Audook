// Decided once at module load - the platform never changes during the
// app's lifetime, so this is safe to use as a stable branch condition
// (including for picking which React hook to call, see Player.tsx).
export const isCapacitorPlatform = !!(window as any).Capacitor?.isNativePlatform?.();
