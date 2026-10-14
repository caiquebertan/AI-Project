// {{header}}
// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { Probe } from './Probe';

afterEach(cleanup);

describe('probe component', () => {
  it('PLAT-WEB-015 smoke component test under jsdom', () => {
    render(<Probe label="hello" />);
    const element = screen.getByTestId('probe-label');
    expect(element.textContent).toBe('hello');
    expect(element.getAttribute('data-state')).toBe('ready');
  });
});
