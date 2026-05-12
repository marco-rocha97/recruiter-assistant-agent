import { useState } from 'react';
import { DatasetLink } from './components/DatasetLink';
import { DatasetModal } from './features/dataset/components/DatasetModal';
import { useRankCandidates } from './features/ranking/api';
import { ErrorMessage } from './features/ranking/components/ErrorMessage';
import { JdInput } from './features/ranking/components/JdInput';
import { LoadingState } from './features/ranking/components/LoadingState';
import { Shortlist } from './features/ranking/components/Shortlist';
import type { OverrideMap, OverrideStatus } from './features/ranking/types';

const STORAGE_KEY = 'recruiter_overrides';

export default function App() {
  const mutation = useRankCandidates();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [isDatasetOpen, setIsDatasetOpen] = useState(false);
  const [overrides, setOverrides] = useState<OverrideMap>(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}');
    } catch {
      return {};
    }
  });

  function handleToggle(id: string) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  function handleOverride(candidateId: string, status: OverrideStatus | null): void {
    setOverrides(prev => {
      const next = { ...prev };
      if (status === null) {
        delete next[candidateId];
      } else {
        next[candidateId] = status;
      }
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        // localStorage unavailable — degrade to session-only
      }
      return next;
    });
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white px-6 py-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-gray-900">Recruiter Assistant</h1>
        <DatasetLink onOpen={() => setIsDatasetOpen(true)} />
      </header>
      <main className="mx-auto max-w-2xl px-4 py-8">
        <JdInput
          onSubmit={(text) => {
            setExpandedId(null);
            setOverrides({});
            try { localStorage.removeItem(STORAGE_KEY); } catch { /* unavailable */ }
            mutation.mutate(text);
          }}
          disabled={mutation.isPending}
        />
        {mutation.isPending && (
          <div className="mt-6">
            <LoadingState />
          </div>
        )}
        {mutation.isError && (
          <div className="mt-6">
            <ErrorMessage error={mutation.error} onReset={() => mutation.reset()} />
          </div>
        )}
        {mutation.isSuccess && (
          <div className="mt-6">
            <Shortlist
              shortlist={mutation.data}
              expandedId={expandedId}
              onToggle={handleToggle}
              overrides={overrides}
              onOverride={handleOverride}
            />
          </div>
        )}
      </main>
      {isDatasetOpen && <DatasetModal onClose={() => setIsDatasetOpen(false)} />}
    </div>
  );
}
