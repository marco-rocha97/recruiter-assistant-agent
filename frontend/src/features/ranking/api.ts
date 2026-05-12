import { useMutation } from '@tanstack/react-query';
import type { ApiError, ShortlistResponse } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export function useRankCandidates() {
  return useMutation<ShortlistResponse, ApiError, string>({
    mutationFn: async (jdText: string) => {
      const res = await fetch(`${API_BASE}/rank`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jd_text: jdText }),
      });
      if (!res.ok) throw (await res.json()) as ApiError;
      return res.json() as Promise<ShortlistResponse>;
    },
  });
}
