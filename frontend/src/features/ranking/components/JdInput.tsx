import { useState } from 'react';

const MIN_CHARS = 50;

interface JdInputProps {
  onSubmit: (jdText: string) => void;
  disabled: boolean;
}

export function JdInput({ onSubmit, disabled }: JdInputProps) {
  const [text, setText] = useState('');

  const wordCount = text.trim() === '' ? 0 : text.trim().split(/\s+/).length;
  const charCount = text.length;
  const isReady = charCount >= MIN_CHARS;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isReady) onSubmit(text);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div>
        <label htmlFor="jd-input" className="text-sm font-medium text-gray-700">
          Paste the job description
        </label>
        <p className="text-xs text-gray-400 mt-0.5">
          Minimum {MIN_CHARS} characters — paste the full JD for the best results
        </p>
      </div>
      <textarea
        id="jd-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        rows={10}
        placeholder="Paste the full job description here…"
        className="w-full rounded-lg border border-gray-300 p-3 font-mono text-sm disabled:opacity-50"
      />
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400">
          {wordCount} {wordCount === 1 ? 'word' : 'words'} · {charCount} chars
        </span>
        <button
          type="submit"
          disabled={disabled || !isReady}
          className="rounded-lg bg-indigo-600 px-6 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Find candidates
        </button>
      </div>
    </form>
  );
}
