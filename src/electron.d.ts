export interface IElectronAPI {
  getAppConfig: () => Promise<any>;
  getBooks: () => Promise<any[]>;
  searchBooks: (query: string) => Promise<any[]>;
  getBookDetails: (bookId: string) => Promise<any>;
  playBook: (bookId: string) => Promise<void>;
  pausePlayback: () => Promise<void>;
  resumePlayback: () => Promise<void>;
  stopPlayback: () => Promise<void>;
  seekTo: (position: number) => Promise<void>;
  setVolume: (volume: number) => Promise<void>;
  setSpeed: (speed: number) => Promise<void>;
  syncServers: () => Promise<void>;
  selectFolder: () => Promise<string | null>;
  onPlayerState: (callback: (state: any) => void) => void;
  onPlayerPosition: (callback: (data: any) => void) => void;
}

declare global {
  interface Window {
    electron?: IElectronAPI;
  }
}
