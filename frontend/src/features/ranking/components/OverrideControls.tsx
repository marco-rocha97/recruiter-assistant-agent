import type { OverrideStatus } from '../types';

interface OverrideControlsProps {
  current: OverrideStatus | null;
  onOverride: (status: OverrideStatus | null) => void;
}

export function OverrideControls({ current, onOverride }: OverrideControlsProps) {
  function handleClick(status: OverrideStatus) {
    onOverride(current === status ? null : status);
  }

  return (
    <div className="mt-2 flex gap-2">
      <button
        type="button"
        aria-label="Mark as shortlisted"
        aria-pressed={current === 'shortlisted'}
        onClick={(e) => { e.stopPropagation(); handleClick('shortlisted'); }}
        className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
          current === 'shortlisted'
            ? 'bg-green-600 text-white'
            : 'bg-green-100 text-green-800 hover:bg-green-200'
        }`}
      >
        Shortlist
      </button>
      <button
        type="button"
        aria-label="Mark as rejected"
        aria-pressed={current === 'rejected'}
        onClick={(e) => { e.stopPropagation(); handleClick('rejected'); }}
        className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
          current === 'rejected'
            ? 'bg-red-600 text-white'
            : 'bg-red-100 text-red-800 hover:bg-red-200'
        }`}
      >
        Reject
      </button>
    </div>
  );
}
