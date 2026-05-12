import type { OverrideMap, OverrideStatus, ShortlistResponse } from '../types';
import { CandidateRow } from './CandidateRow';

interface ShortlistProps {
  shortlist: ShortlistResponse;
  expandedId: string | null;
  onToggle: (id: string) => void;
  overrides: OverrideMap;
  onOverride: (candidateId: string, status: OverrideStatus | null) => void;
}

export function Shortlist({ shortlist, expandedId, onToggle, overrides, onOverride }: ShortlistProps) {
  return (
    <section aria-label="Ranked candidates">
      <h2 className="mb-4 text-lg font-semibold text-gray-900">Top candidates</h2>
      <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white">
        {shortlist.rankings.map((ranking) => (
          <CandidateRow
            key={ranking.candidate_id}
            ranking={ranking}
            isExpanded={expandedId === ranking.candidate_id}
            onToggle={() => onToggle(ranking.candidate_id)}
            override={overrides[ranking.candidate_id] ?? null}
            onOverride={(status) => onOverride(ranking.candidate_id, status)}
          />
        ))}
      </ul>
    </section>
  );
}
