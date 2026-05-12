import { useEffect, useRef } from 'react';
import { useDatasetInfo } from '../api';

export function DatasetModal({ onClose }: { onClose: () => void }) {
  const { data, isLoading, isError } = useDatasetInfo();
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeButtonRef.current?.focus();

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  return (
    // backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      {/* panel — stop propagation so clicks inside don't close */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dataset-title"
        className="relative w-full max-w-lg rounded-lg bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 id="dataset-title" className="text-base font-semibold text-gray-900">
            About this dataset
          </h2>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            aria-label="Close dataset info"
            className="rounded p-1 text-gray-500 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            ✕
          </button>
        </div>

        {isLoading && (
          <p className="text-sm text-gray-500">Loading dataset info…</p>
        )}

        {isError && (
          <p className="text-sm text-red-600">
            Dataset info is temporarily unavailable.
          </p>
        )}

        {data && (
          <div className="space-y-4 text-sm text-gray-700">
            <div className="flex gap-8">
              <div>
                <p className="text-2xl font-bold text-gray-900">{data.total_included}</p>
                <p className="text-xs text-gray-500 mt-0.5">active candidates</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{data.total_excluded}</p>
                <p className="text-xs text-gray-500 mt-0.5">excluded during preparation</p>
              </div>
            </div>

            {data.exclusions.length > 0 && (
              <div>
                <p className="font-medium text-gray-900 mb-2">Exclusion log</p>
                <ul className="divide-y divide-gray-100 border border-gray-100 rounded-md overflow-hidden">
                  {data.exclusions.map((e) => (
                    <li key={e.source_id} className="px-3 py-2 bg-gray-50">
                      <span className="font-mono text-xs text-gray-500 mr-2">
                        {e.source_id}
                      </span>
                      <span className="text-gray-700">{e.category}</span>
                      <span className="ml-2 inline-block rounded bg-red-50 px-1.5 py-0.5 text-xs text-red-700">
                        {e.reason}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <p className="text-xs text-gray-400">
              Source: {data.total_source.toLocaleString()} CVs sampled from a public Kaggle resume dataset.
              {data.total_selected} were selected for processing; {data.total_included} passed all gates.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
