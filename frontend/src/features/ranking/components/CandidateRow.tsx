import type { KeyboardEvent } from 'react';
import type { CandidateRanking, OverrideStatus } from '../types';
import { EvidencePanel } from './EvidencePanel';
import { OverrideControls } from './OverrideControls';

interface CandidateRowProps {
  ranking: CandidateRanking;
  isExpanded: boolean;
  onToggle: () => void;
  override: OverrideStatus | null;
  onOverride: (status: OverrideStatus | null) => void;
}

export function CandidateRow({ ranking, isExpanded, onToggle, override, onOverride }: CandidateRowProps) {
  function handleKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onToggle();
    }
  }

  const previewMatched = ranking.matched_requirements.slice(0, 3);
  const missingCount = ranking.missing_requirements.length;

  return (
    <li className="border-b border-gray-200 last:border-0">
      <div
        role="button"
        tabIndex={0}
        onClick={onToggle}
        onKeyDown={handleKeyDown}
        aria-expanded={isExpanded}
        className="flex cursor-pointer items-center gap-3 p-4 hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        <span className="w-6 text-center text-xs font-bold text-indigo-600">
          #{ranking.rank}
        </span>
        {override === 'shortlisted' && (
          <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
            Shortlisted
          </span>
        )}
        {override === 'rejected' && (
          <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
            Rejected
          </span>
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{ranking.category}</p>
          <div className="mt-1 flex flex-wrap gap-1">
            {previewMatched.map((req) => (
              <span
                key={req}
                className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-800"
              >
                {req}
              </span>
            ))}
            {missingCount > 0 && (
              <span className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
                {missingCount} missing
              </span>
            )}
          </div>
        </div>
        <svg
          className={`h-4 w-4 shrink-0 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </div>
      {isExpanded && (
        <div className="px-4 pb-4">
          <EvidencePanel ranking={ranking} />
        </div>
      )}
      <div className="px-4 pb-2">
        <OverrideControls current={override} onOverride={onOverride} />
      </div>
    </li>
  );
}
