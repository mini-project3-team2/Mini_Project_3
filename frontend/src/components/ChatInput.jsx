import { useEffect, useRef, useState } from 'react'

export const MAX_Q = 1000

// Enter 전송 · Shift+Enter 줄바꿈 (한글 조합 중 Enter 는 무시)
export default function ChatInput({ busy, onSend, onStop }) {
  const [text, setText] = useState('')
  const ref = useRef(null)
  const len = text.length
  const over = len > MAX_Q
  const empty = !text.trim()

  useEffect(() => {
    if (!busy) ref.current?.focus()
  }, [busy])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [text])

  const submit = () => {
    if (busy || empty || over) return
    onSend(text.trim())
    setText('')
  }

  const onKeyDown = (e) => {
    if (e.key !== 'Enter' || e.shiftKey || e.nativeEvent.isComposing || e.keyCode === 229) return
    e.preventDefault()
    submit()
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
    >
      <div
        className={`flex items-end gap-2 rounded-xl border bg-white p-2 focus-within:ring-2 focus-within:ring-accent/40 ${
          over ? 'border-red-700' : 'border-ink/30'
        }`}
      >
        <label htmlFor="question" className="sr-only">
          질문
        </label>
        <textarea
          id="question"
          ref={ref}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={busy}
          placeholder={busy ? '답변이 끝나면 다음 질문을 입력할 수 있어요' : '궁금한 내용을 입력하세요'}
          aria-invalid={over || undefined}
          aria-describedby="question-count"
          className="min-h-11 flex-1 resize-none bg-transparent px-2 py-2.5 text-sm outline-none disabled:cursor-not-allowed"
        />
        <span id="question-count" className={`self-center text-xs ${over ? 'font-semibold text-red-700' : 'text-ink/60'}`}>
          {len} / {MAX_Q}
        </span>
        {busy ? (
          <button
            type="button"
            onClick={onStop}
            className="flex min-h-11 items-center gap-1.5 rounded-lg border border-ink/30 px-3 text-sm font-semibold"
          >
            <span className="size-2.5 rounded-sm bg-current" aria-hidden="true" />
            중단
          </button>
        ) : (
          <button
            type="submit"
            disabled={empty || over}
            aria-label="질문 보내기"
            className="flex size-11 items-center justify-center rounded-lg bg-accent text-white disabled:cursor-not-allowed disabled:bg-line disabled:text-ink/50"
          >
            <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
              <path d="M12 19V5M5 12l7-7 7 7" />
            </svg>
          </button>
        )}
      </div>
      {over && (
        <p role="alert" className="mt-1.5 text-xs text-red-700">
          질문은 {MAX_Q}자 이하로 입력해 주세요.
        </p>
      )}
    </form>
  )
}
