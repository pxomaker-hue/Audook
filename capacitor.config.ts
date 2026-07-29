import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.audook.app',
  appName: 'Audook',
  webDir: 'build',
  // The app talks to a user-supplied NAS backend over plain HTTP (no TLS
  // cert for a local LAN IP). Capacitor serves the app itself from a
  // virtual https://localhost origin, so without this the WebView blocks
  // those requests as mixed content regardless of the manifest's
  // usesCleartextTraffic flag. `server.cleartext` (tried first) is a
  // different setting entirely - this is the one that actually flips
  // WebSettings.setMixedContentMode to MIXED_CONTENT_ALWAYS_ALLOW
  // (see @capacitor/android's Bridge.java / CapConfig.java).
  server: {
    cleartext: true
  },
  android: {
    allowMixedContent: true
  }
};

export default config;
