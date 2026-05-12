import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ShortlistResponse } from '../../types';
import { Shortlist } from '../Shortlist';

function makeShortlist(n: number): ShortlistResponse {
  return {
    rankings: Array.from({ length: n }, (_, i) => ({
      candidate_id: `candidate_${String(i + 1).padStart(3, '0')}`,
      rank: i + 1,
      category: 'Engineer',
      matched_requirements: ['Python'],
      missing_requirements: [],
      evidence: 'Good candidate.',
      vector_score: 0.82,
    })),
  };
}

describe('Shortlist', () => {
  it('renders N CandidateRow items for N rankings', () => {
    render(
      <Shortlist shortlist={makeShortlist(5)} expandedId={null} onToggle={() => {}} overrides={{}} onOverride={() => {}} />,
    );
    // Each row has 1 expand/collapse button + 2 override buttons = 3 buttons per row
    expect(screen.getAllByRole('button')).toHaveLength(15);
  });

  it('only one row is expanded at a time (controlled by parent)', () => {
    render(
      <Shortlist
        shortlist={makeShortlist(5)}
        expandedId="candidate_001"
        onToggle={() => {}}
        overrides={{}}
        onOverride={() => {}}
      />,
    );
    // EvidencePanel text for the first candidate
    expect(screen.getByText('Good candidate.')).toBeInTheDocument();
    // Rows 2-5 should not show evidence (only one expanded)
    expect(screen.getAllByText('Good candidate.')).toHaveLength(1);
  });

  it('clicking a row calls onToggle with the candidate id', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(
      <Shortlist shortlist={makeShortlist(3)} expandedId={null} onToggle={onToggle} overrides={{}} onOverride={() => {}} />,
    );
    await user.click(screen.getAllByRole('button')[0]);
    expect(onToggle).toHaveBeenCalledWith('candidate_001');
  });

  it('clicking an expanded row calls onToggle (collapse)', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(
      <Shortlist
        shortlist={makeShortlist(3)}
        expandedId="candidate_001"
        onToggle={onToggle}
        overrides={{}}
        onOverride={() => {}}
      />,
    );
    await user.click(screen.getAllByRole('button')[0]);
    expect(onToggle).toHaveBeenCalledWith('candidate_001');
  });
});
