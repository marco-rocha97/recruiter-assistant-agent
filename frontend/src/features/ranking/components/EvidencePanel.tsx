import type { CandidateRanking } from '../types';

interface EvidencePanelProps {
  ranking: CandidateRanking;
}

export function EvidencePanel({ ranking }: EvidencePanelProps) {
  return (
    <div className="mt-2 rounded-md bg-gray-50 p-4 text-sm text-gray-700">
      <div className="mb-2">
        <span className="font-medium text-green-700">Matched: </span>
        <span>{ranking.matched_requirements.join(', ')}</span>
      </div>
      {ranking.missing_requirements.length > 0 && (
        <div className="mb-2">
          <span className="font-medium text-amber-700">Missing: </span>
          <span>{ranking.missing_requirements.join(', ')}</span>
        </div>
      )}
      <p className="mt-2 italic text-gray-600">{ranking.evidence}</p>
    </div>
  );
}
