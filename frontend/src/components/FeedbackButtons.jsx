import { useState } from 'react'
import { sendFeedback } from '../services/api'
import { errorMessage } from '../utils/errorMessage'
import ErrorIcon from './ErrorIcon'

const options = [
  ['HELPFUL', '도움됨', 'M7 10v12M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z'],
  ['NOT_HELPFUL', '도움 안 됨', 'M17 14V2M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z'],
]

// chatId 가 없으면(답변 완료 전) 비활성. 실패하면 이전 값으로 되돌린다
export default function FeedbackButtons({ chatId, value, onChange }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const off = chatId == null || busy

  const choose = async (v) => {
    if (off || v === value) return
    const prev = value
    onChange(v)
    setBusy(true)
    setErr('')
    try {
      const d = await sendFeedback(chatId, v)
      onChange(d?.feedback ?? v)
    } catch (e) {
      onChange(prev)
      setErr(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mt-3">
      <div role="group" aria-label="답변 피드백" className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-ink/70">이 답변이 도움이 되었나요?</span>
        {options.map(([v, label, d]) => {
          const on = value === v
          return (
            <button
              key={v}
              type="button"
              onClick={() => choose(v)}
              disabled={off}
              aria-pressed={on}
              className={`flex min-h-11 items-center gap-1.5 rounded-full border px-4 text-sm disabled:cursor-not-allowed disabled:opacity-50 ${
                on ? 'border-accent bg-ready-bg font-semibold text-accent' : 'border-ink/30 bg-white'
              }`}
            >
              <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <path d={d} />
              </svg>
              {label}
            </button>
          )
        })}
      </div>
      {err && (
        <p role="alert" className="mt-1.5 flex gap-1.5 text-xs text-red-700">
          <ErrorIcon />
          <span>{err}</span>
        </p>
      )}
    </div>
  )
}
