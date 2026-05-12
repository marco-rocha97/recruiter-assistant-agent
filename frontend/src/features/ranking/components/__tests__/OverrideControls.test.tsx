import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OverrideControls } from '../OverrideControls';

describe('OverrideControls', () => {
  it('renders Shortlist and Reject buttons', () => {
    render(<OverrideControls current={null} onOverride={() => {}} />);
    expect(screen.getByRole('button', { name: 'Mark as shortlisted' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mark as rejected' })).toBeInTheDocument();
  });

  it('both buttons have aria-pressed=false when current=null', () => {
    render(<OverrideControls current={null} onOverride={() => {}} />);
    expect(screen.getByRole('button', { name: 'Mark as shortlisted' })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('button', { name: 'Mark as rejected' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('Shortlist is aria-pressed=true and Reject is aria-pressed=false when current=shortlisted', () => {
    render(<OverrideControls current="shortlisted" onOverride={() => {}} />);
    expect(screen.getByRole('button', { name: 'Mark as shortlisted' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Mark as rejected' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('Reject is aria-pressed=true and Shortlist is aria-pressed=false when current=rejected', () => {
    render(<OverrideControls current="rejected" onOverride={() => {}} />);
    expect(screen.getByRole('button', { name: 'Mark as rejected' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Mark as shortlisted' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('clicking Reject when current=null calls onOverride with rejected', async () => {
    const user = userEvent.setup();
    const onOverride = vi.fn();
    render(<OverrideControls current={null} onOverride={onOverride} />);
    await user.click(screen.getByRole('button', { name: 'Mark as rejected' }));
    expect(onOverride).toHaveBeenCalledWith('rejected');
  });

  it('clicking Shortlist when current=shortlisted calls onOverride with null (toggle off)', async () => {
    const user = userEvent.setup();
    const onOverride = vi.fn();
    render(<OverrideControls current="shortlisted" onOverride={onOverride} />);
    await user.click(screen.getByRole('button', { name: 'Mark as shortlisted' }));
    expect(onOverride).toHaveBeenCalledWith(null);
  });

  it('clicking Reject when current=shortlisted calls onOverride with rejected (switch)', async () => {
    const user = userEvent.setup();
    const onOverride = vi.fn();
    render(<OverrideControls current="shortlisted" onOverride={onOverride} />);
    await user.click(screen.getByRole('button', { name: 'Mark as rejected' }));
    expect(onOverride).toHaveBeenCalledWith('rejected');
  });

  it('clicking Shortlist when current=rejected calls onOverride with shortlisted (switch)', async () => {
    const user = userEvent.setup();
    const onOverride = vi.fn();
    render(<OverrideControls current="rejected" onOverride={onOverride} />);
    await user.click(screen.getByRole('button', { name: 'Mark as shortlisted' }));
    expect(onOverride).toHaveBeenCalledWith('shortlisted');
  });
});
