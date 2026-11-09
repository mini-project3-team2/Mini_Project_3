// page 는 0부터, 화면 번호는 1부터. 번호는 현재 페이지 주변 최대 5개
const WINDOW = 5

function pages(cur, total) {
  const start = Math.max(0, Math.min(cur - Math.floor(WINDOW / 2), total - WINDOW))
  return Array.from({ length: Math.min(WINDOW, total) }, (_, i) => start + i)
}

const btn =
  'min-h-11 min-w-11 rounded-md border px-3 text-sm disabled:cursor-not-allowed disabled:opacity-40'

export default function Pagination({ page, totalPages, disabled, onChange }) {
  if (totalPages <= 1) return null
  const go = (p) => {
    if (!disabled && p >= 0 && p < totalPages && p !== page) onChange(p)
  }

  return (
    <nav aria-label="페이지" className="mt-6 flex flex-wrap justify-center gap-2">
      <button type="button" onClick={() => go(page - 1)} disabled={disabled || page <= 0} className={`${btn} border-ink/30 bg-white`}>
        이전
      </button>
      {pages(page, totalPages).map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => go(p)}
          disabled={disabled && p !== page}
          aria-current={p === page ? 'page' : undefined}
          aria-label={`${p + 1}페이지`}
          className={`${btn} ${p === page ? 'border-accent bg-accent font-semibold text-white' : 'border-ink/30 bg-white'}`}
        >
          {p + 1}
        </button>
      ))}
      <button
        type="button"
        onClick={() => go(page + 1)}
        disabled={disabled || page >= totalPages - 1}
        className={`${btn} border-ink/30 bg-white`}
      >
        다음
      </button>
    </nav>
  )
}
