import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from '../src/App';

describe('App Smoke Test', () => {
  it('renders application navigation and brand title', () => {
    render(<App />);
    expect(screen.getByText(/CivicPulse/i)).toBeInTheDocument();
  });
});
