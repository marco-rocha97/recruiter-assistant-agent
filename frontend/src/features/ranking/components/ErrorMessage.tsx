import type { ApiError } from '../types';

interface ErrorMessageProps {
  error: ApiError;
  onReset: () => void;
}

export function ErrorMessage({ error, onReset }: ErrorMessageProps) {
  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4">
      <p className="text-sm text-red-700">{error.message}</p>
      <button
        onClick={onReset}
        className="mt-3 rounded bg-red-600 px-4 py-1.5 text-sm font-medium text-white"
      >
        Try again
      </button>
    </div>
  );
}
