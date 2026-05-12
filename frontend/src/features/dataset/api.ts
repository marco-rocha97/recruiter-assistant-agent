import { useQuery } from '@tanstack/react-query';
import type { DatasetInfo } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export function useDatasetInfo() {
  return useQuery<DatasetInfo>({
    queryKey: ['dataset'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/dataset`);
      if (!res.ok) throw new Error('Failed to load dataset info');
      return res.json();
    },
    staleTime: Infinity,
  });
}
