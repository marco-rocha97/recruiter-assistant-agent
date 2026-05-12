import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { CandidateRanking } from '../../types';
import { CandidateRow } from '../CandidateRow';

const testRanking: CandidateRanking = {
  candidate_id: 'candidate_001',
  rank: 1,
  category: 'Python Engineer',
  matched_requirements: ['Python', 'FastAPI', 'Docker'],
  missing_requirements: ['Kubernetes'],
  evidence: 'Strong Python background with 3 years FastAPI experience.',
  vector_score: 0.82,
};

describe('CandidateRow', () => {
  it('shows rank and category when collapsed', () => {
    render(
      <ul>
        <CandidateRow ranking={testRanking} isExpanded={false} onToggle={() => {}} override={null} onOverride={() => {}} />
      </ul>,
    );
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getByText('Python Engineer')).toBeInTheDocument();
  });

  it('clicking the row calls onToggle', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(
      <ul>
        <CandidateRow ranking={testRanking} isExpanded={false} onToggle={onToggle} override={null} onOverride={() => {}} />
      </ul>,
    );
    await user.click(screen.getAllByRole('button')[0]);
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it('pressing Enter on the focused row calls onToggle', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(
      <ul>
        <CandidateRow ranking={testRanking} isExpanded={false} onToggle={onToggle} override={null} onOverride={() => {}} />
      </ul>,
    );
    screen.getAllByRole('button')[0].focus();
    await user.keyboard('{Enter}');
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it('pressing Space on the focused row calls onToggle', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    render(
      <ul>
        <CandidateRow ranking={testRanking} isExpanded={false} onToggle={onToggle} override={null} onOverride={() => {}} />
      </ul>,
    );
    screen.getAllByRole('button')[0].focus();
    await user.keyboard(' ');
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it('shows EvidencePanel when expanded', () => {
    render(
      <ul>
        <CandidateRow ranking={testRanking} isExpanded={true} onToggle={() => {}} override={null} onOverride={() => {}} />
      </ul>,
    );
    expect(
      screen.getByText('Strong Python background with 3 years FastAPI experience.'),
    ).toBeInTheDocument();
  });

  it('hides EvidencePanel when collapsed', () => {
    render(
      <ul>
        <CandidateRow ranking={testRanking} isExpanded={false} onToggle={() => {}} override={null} onOverride={() => {}} />
      </ul>,
    );
    expect(
      screen.queryByText('Strong Python background with 3 years FastAPI experience.'),
    ).not.toBeInTheDocument();
  });

  it('renders no override chip when override=null', () => {
    render(
      <ul>
        <CandidateRow ranking={testRanking} isExpanded={false} onToggle={() => {}} override={null} onOverride={() => {}} />
      </ul>,
    );
    expect(screen.queryByText('Shortlisted')).not.toBeInTheDocument();
    expect(screen.queryByText('Rejected')).not.toBeInTheDocument();
  });

  it('shows Shortlisted chip when override=shortlisted', () => {
    render(
      <ul>
        <CandidateRow ranking={testRanking} isExpanded={false} onToggle={() => {}} override="shortlisted" onOverride={() => {}} />
      </ul>,
    );
    expect(screen.getByText('Shortlisted')).toBeInTheDocument();
  });

  it('shows Rejected chip when override=rejected', () => {
    render(
      <ul>
        <CandidateRow ranking={testRanking} isExpanded={false} onToggle={() => {}} override="rejected" onOverride={() => {}} />
      </ul>,
    );
    expect(screen.getByText('Rejected')).toBeInTheDocument();
  });

  it('rank badge #1 is visible when override=shortlisted', () => {
    render(
      <ul>
        <CandidateRow ranking={testRanking} isExpanded={false} onToggle={() => {}} override="shortlisted" onOverride={() => {}} />
      </ul>,
    );
    expect(screen.getByText('#1')).toBeInTheDocument();
  });

  it('OverrideControls buttons are visible regardless of isExpanded state', () => {
    render(
      <ul>
        <CandidateRow ranking={testRanking} isExpanded={false} onToggle={() => {}} override={null} onOverride={() => {}} />
      </ul>,
    );
    expect(screen.getByRole('button', { name: 'Mark as shortlisted' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mark as rejected' })).toBeInTheDocument();
  });
});
