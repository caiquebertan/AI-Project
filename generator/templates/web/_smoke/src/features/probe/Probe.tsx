// {{header}}
export function Probe({ label }: { label: string }) {
  return (
    <p data-testid="probe-label" data-state="ready">
      {label}
    </p>
  );
}
