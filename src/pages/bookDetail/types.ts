export interface BookmarkEntry {
  id: number;
  chapter_index: number;
  position_seconds: number;
  title: string | null;
  created_at: string | null;
}

export interface BookChapter {
  id: string;
  title: string;
  index: number;
  duration: number;
  audio_file: string;
}

export interface BookDetail {
  id: string;
  title: string;
  author: string;
  narrator: string;
  cover_url: string;
  duration: number;
  description: string;
  series: string | null;
  series_sequence: string | number | null;
  genre: string[];
  chapters: BookChapter[];
  bookmarks: BookmarkEntry[];
  manual_overrides: string[];
  progress: {
    position: number;
    percentage: number;
    chapter_index: number;
  };
  is_finished: boolean;
  noise_reduction_status: 'idle' | 'processing' | 'done' | 'error';
  use_cleaned_audio: boolean;
}

export interface MatchCandidate {
  work_key: string;
  title: string;
  author: string | null;
  year: number | null;
  cover_url: string | null;
  is_french: boolean;
}
