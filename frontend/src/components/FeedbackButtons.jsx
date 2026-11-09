import { useState } from 'react'
import { sendFeedback } from '../services/api'
import { errorMessage } from '../utils/errorMessage'
import ErrorIcon from './ErrorIcon'
import { BUTTON_OFF, BUTTON_ON, ICON, PILL, THUMB_DOWN, THUMB_UP } from './feedbackStyle'

const options = [
  ['HELPFUL', '도움됨', THUMB_UP],
  ['NOT_HELPFUL', '도움 안 됨', THUMB_DOWN],
]

// 채팅 화면 전용. chatId 가 없으면(답변 완료 전) 비활성. 실패하면 이전 값으로 되돌린다
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
      <div role="group" aria-label="답변 피드백" className="flex flex-wrap items-center gap-1.5">
        <span className="mr-1 text-xs text-ink/60">이 답변이 도움이 되었나요?</span>
        {options.map(([v, label, d]) => {
          const on = value === v
          return (
            <button
              key={v}
              type="button"
              onClick={() => choose(v)}
              disabled={off}
              aria-pressed={on}
              className={`${PILL} ${on ? BUTTON_ON : BUTTON_OFF} disabled:cursor-not-allowed disabled:opacity-50`}
            >
              <svg viewBox="0 0 24 24" className={ICON} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
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
