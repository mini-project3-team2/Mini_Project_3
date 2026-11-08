const kinds = {
  INDEXING: ['적재 중', 'bg-indexing-bg text-indexing'],
  READY: ['완료', 'bg-ready-bg text-ready'],
}

export default function StatusBadge({ status }) {
  const [label, tone] = kinds[status] ?? ['확인 필요', 'bg-line text-ink']
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ${tone}`}>
      {status === 'INDEXING' ? (
        <span className="size-3 rounded-full border-2 border-current border-t-transparent motion-safe:animate-spin" aria-hidden="true" />
      ) : status === 'READY' ? (
        <svg viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="3" aria-hidden="true">
          <path d="M20 6 9 17l-5-5" />
        </svg>
      ) : null}
      {label}
    </span>
  )
}
