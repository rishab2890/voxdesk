// Small shared UI primitives — Tailwind only, no component library.
"use client";

export function Card({ title, children, actions }: {
  title?: string; children: React.ReactNode; actions?: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-edge bg-panel p-5">
      {(title || actions) && (
        <div className="mb-4 flex items-center justify-between">
          {title && <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-edge bg-panel p-5">
      <div className="text-3xl font-semibold text-white">{value}</div>
      <div className="mt-1 text-sm text-slate-400">{label}</div>
    </div>
  );
}

export function Button({ children, onClick, type = "button", variant = "primary", disabled }: {
  children: React.ReactNode; onClick?: () => void;
  type?: "button" | "submit"; variant?: "primary" | "ghost" | "danger"; disabled?: boolean;
}) {
  const styles = {
    primary: "bg-accent hover:bg-accent-soft text-white",
    ghost: "border border-edge text-slate-300 hover:bg-edge",
    danger: "border border-red-900 text-red-400 hover:bg-red-950",
  }[variant];
  return (
    <button type={type} onClick={onClick} disabled={disabled}
      className={`rounded-lg px-4 py-2 text-sm font-medium transition disabled:opacity-50 ${styles}`}>
      {children}
    </button>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement> & { label?: string }) {
  const { label, ...rest } = props;
  return (
    <label className="block text-sm">
      {label && <span className="mb-1 block text-slate-400">{label}</span>}
      <input {...rest}
        className="w-full rounded-lg border border-edge bg-surface px-3 py-2 text-slate-200 outline-none focus:border-accent" />
    </label>
  );
}

export function TextArea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string }) {
  const { label, ...rest } = props;
  return (
    <label className="block text-sm">
      {label && <span className="mb-1 block text-slate-400">{label}</span>}
      <textarea {...rest}
        className="w-full rounded-lg border border-edge bg-surface px-3 py-2 text-slate-200 outline-none focus:border-accent" />
    </label>
  );
}

export function Badge({ children, tone = "slate" }: { children: React.ReactNode; tone?: string }) {
  const tones: Record<string, string> = {
    green: "bg-green-950 text-green-400 border-green-900",
    amber: "bg-amber-950 text-amber-400 border-amber-900",
    red: "bg-red-950 text-red-400 border-red-900",
    indigo: "bg-indigo-950 text-indigo-300 border-indigo-900",
    slate: "bg-slate-900 text-slate-400 border-slate-800",
  };
  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-xs font-medium ${tones[tone] ?? tones.slate}`}>
      {children}
    </span>
  );
}

export function statusTone(status: string): string {
  return ({ completed: "green", ready: "green", transferred: "indigo", in_progress: "amber",
    processing: "amber", pending: "amber", booked: "green", failed: "red" } as Record<string, string>)[status] ?? "slate";
}

export function ErrorText({ error }: { error: string | null }) {
  return error ? <p className="text-sm text-red-400">{error}</p> : null;
}

export function Empty({ text }: { text: string }) {
  return <p className="py-8 text-center text-sm text-slate-500">{text}</p>;
}
