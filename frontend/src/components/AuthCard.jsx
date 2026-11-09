import ErrorIcon from './ErrorIcon'

function BookIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M12 7v13M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z" />
    </svg>
  )
}

export default function AuthCard({ title, subtitle, footer, children }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 py-10">
      <div className="flex size-10 items-center justify-center rounded-lg bg-accent text-white">
        <BookIcon />
      </div>
      <h1 className="mt-4 text-xl font-bold">{title}</h1>
      <p className="mt-2 text-sm text-ink/70">{subtitle}</p>
      <div className="mt-6 w-full max-w-sm rounded-xl border border-line bg-white p-6">{children}</div>
      <p className="mt-6 text-sm text-ink/70">{footer}</p>
    </div>
  )
}

const tones = {
  success: 'bg-ready-bg text-ready',
  info: 'border border-line bg-bg text-ink',
}

export function FormNotice({ tone = 'success', children }) {
  return (
    <p role="status" className={`mb-5 rounded-md p-3 text-sm ${tones[tone]}`}>
      {children}
    </p>
  )
}

export function Field({ id, label, error, ...props }) {
  const errId = `${id}-error`
  return (
    <div className="mb-5">
      <label htmlFor={id} className="block text-sm font-semibold">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errId : undefined}
        className={`mt-2 h-11 w-full rounded-md border bg-white px-3 text-sm outline-none focus:ring-2 focus:ring-accent/40 ${
          error ? 'border-red-700' : 'border-ink/30'
        }`}
        {...props}
      />
      {error && (
        <p id={errId} role="alert" className="mt-1.5 flex gap-1.5 text-xs text-red-700">
          <ErrorIcon />
          <span>{error}</span>
        </p>
      )}
    </div>
  )
}

export function SubmitButton({ busy, children, busyText }) {
  return (
    <button
      type="submit"
      disabled={busy}
      aria-busy={busy}
      className="min-h-11 w-full rounded-md bg-accent px-4 text-sm font-semibold text-white hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {busy ? busyText : children}
    </button>
  )
}
