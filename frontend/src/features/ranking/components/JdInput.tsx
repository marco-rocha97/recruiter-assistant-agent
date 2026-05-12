import { useState } from 'react';

interface JdInputProps {
  onSubmit: (jdText: string) => void;
  disabled: boolean;
}

export function JdInput({ onSubmit, disabled }: JdInputProps) {
  const [text, setText] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (text.length >= 50) onSubmit(text);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <label htmlFor="jd-input" className="text-sm font-medium text-gray-700">
        Paste the job description
      </label>
      <textarea
        id="jd-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        rows={10}
        placeholder="Paste the full job description here…"
        className="w-full rounded-lg border border-gray-300 p-3 font-mono text-sm disabled:opacity-50"
      />
      <button
        type="submit"
        disabled={disabled || text.length < 50}
        className="self-end rounded-lg bg-indigo-600 px-6 py-2 text-sm font-medium text-white disabled:opacity-40"
      >
        Find candidates
      </button>
    </form>
  );
}
