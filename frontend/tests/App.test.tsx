import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import App from '../src/App';
import { SubmitPage } from '../src/pages/SubmitPage';
import { DashboardPage } from '../src/pages/DashboardPage';
import { StatsPage } from '../src/pages/StatsPage';

describe('CivicPulse Frontend Component Suite (Rubric B)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1. Renders application navigation header and brand identity', () => {
    render(<App />);
    expect(screen.getByText(/CivicPulse/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Submit/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Stats/i })).toBeInTheDocument();
  });

  it('2. Enforces client-side validation on complaint text length (<10 chars)', async () => {
    render(<SubmitPage />);
    const submitBtn = screen.getByRole('button', { name: /Submit Complaint/i });
    const textarea = screen.getByPlaceholderText(/Describe the issue in detail/i);

    fireEvent.change(textarea, { target: { value: 'Too short' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Must be at least 10 characters/i)).toBeInTheDocument();
    });
  });

  it('3. Enforces location field validation requirement', async () => {
    render(<SubmitPage />);
    const submitBtn = screen.getByRole('button', { name: /Submit Complaint/i });
    const textarea = screen.getByPlaceholderText(/Describe the issue in detail/i);

    fireEvent.change(textarea, { target: { value: 'Water main burst flooding street since morning' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Must be at least 3 characters/i)).toBeInTheDocument();
    });
  });

  it('4. DashboardPage renders filter controls and status selectors', () => {
    render(
      <BrowserRouter>
        <DashboardPage />
      </BrowserRouter>
    );

    expect(screen.getByText(/Operations Dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/Category/i)).toBeInTheDocument();
    expect(screen.getByText(/Priority/i)).toBeInTheDocument();
    expect(screen.getByText(/Status/i)).toBeInTheDocument();
  });

  it('5. StatsPage renders header and telemetry refresh action', () => {
    render(<StatsPage />);
    expect(screen.getByRole('heading', { level: 1, name: /Statistics/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Refresh/i })).toBeInTheDocument();
  });

  it('6. SubmitPage renders AI triage results and triaged_by provider badge', async () => {
    vi.spyOn(global, 'fetch').mockImplementationOnce(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({
          id: 'b1234567-89ab-cdef-0123-456789abcdef',
          text: 'Major water line rupture on commercial avenue',
          location: 'Sector G-9, Islamabad',
          reporter_contact: '0300-1112233',
          category: 'water',
          priority: 'high',
          status: 'open',
          ai_summary: 'URGENT: Major water line rupture on commercial avenue',
          triaged_by: 'llm:groq',
          triage_latency_ms: 280,
          created_at: new Date().toISOString(),
        }),
      } as any)
    );

    render(<SubmitPage />);
    const textarea = screen.getByPlaceholderText(/Describe the issue in detail/i);
    const locationInput = screen.getByPlaceholderText(/Street, area, city/i);
    const submitBtn = screen.getByRole('button', { name: /Submit Complaint/i });

    fireEvent.change(textarea, { target: { value: 'Major water line rupture on commercial avenue' } });
    fireEvent.change(locationInput, { target: { value: 'Sector G-9, Islamabad' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: /Complaint Submitted/i })).toBeInTheDocument();
      expect(screen.getByText(/llm:groq/i)).toBeInTheDocument();
      expect(screen.getByText(/URGENT: Major water line rupture/i)).toBeInTheDocument();
    });
  });

  it('7. SubmitPage displays rate limit 429 error message with retry-after duration', async () => {
    vi.spyOn(global, 'fetch').mockImplementationOnce(() =>
      Promise.resolve({
        ok: false,
        status: 429,
        json: async () => ({
          error: 'rate_limit_exceeded',
          retry_after: 45,
        }),
      } as any)
    );

    render(<SubmitPage />);
    const textarea = screen.getByPlaceholderText(/Describe the issue in detail/i);
    const locationInput = screen.getByPlaceholderText(/Street, area, city/i);
    const submitBtn = screen.getByRole('button', { name: /Submit Complaint/i });

    fireEvent.change(textarea, { target: { value: 'Repeated complaint to test rate limiter threshold' } });
    fireEvent.change(locationInput, { target: { value: 'Sector I-8, Islamabad' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Rate limit exceeded\. Please try again in 45 seconds\./i)).toBeInTheDocument();
    });
  });
});
