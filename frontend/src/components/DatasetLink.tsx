/**
 * Persistent button to open the dataset transparency modal (T03).
 * Rendered in the page header regardless of mutation state so visitors can always
 * inspect the candidate pool and exclusion log before or after submitting a JD.
 */
export function DatasetLink({ onOpen }: { onOpen: () => void }) {
  return (
    <button
      onClick={onOpen}
      className="text-xs text-indigo-600 underline underline-offset-2 hover:text-indigo-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded"
    >
      About this dataset
    </button>
  );
}
