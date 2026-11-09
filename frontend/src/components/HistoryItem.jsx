import { useState } from 'react'
import { formatDateTime } from '../utils/errorMessage'
import FeedbackChip from './FeedbackChip'
import SourceCard from './SourceCard'

// 이 길이(또는 줄 수)를 넘는 답변만 4줄로 접고 "더 보기"를 보여 준다
const LONG_CHARS = 200
const LONG_LINES = 4

const isLong = (s) => s.length > LONG_CHARS || s.split('\n').length > LONG_LINES

// 질문 · 답변 · 자료 이름은 모두 텍스트로만 출력
// 피드백은 읽기 전용 칩 — 전체일정계획 144행 축소 조항 "질문 기록 화면의 피드백 변경 (표시만 유지)" 적용
export default function HistoryItem({ item }) {
  const [open, setOpen] = useState(false)
  const answer = item.answer ?? ''
  const long = isLong(answer)
  const sources = Array.isArray(item.sources) ? item.sources : []
  const answerId = `answer-${item.id}`

  return (
    <li className="rounded-xl border border-line bg-white p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <h2 className="min-w-0 flex-1 whitespace-pre-wrap break-words text-sm font-semibold">{item.question}</h2>
        <time dateTime={item.createdAt} className="shrink-0 whitespace-nowrap text-xs text-ink/60">
          {formatDateTime(item.createdAt)}
        </time>
      </div>

      <p
        id={answerId}
        className={`mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-ink/90 ${long && !open ? 'line-clamp-4' : ''}`}
      >
        {answer}
      </p>
      {long && (
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls={answerId}
          className="min-h-11 text-sm font-semibold text-accent underline"
        >
          {open ? '접기' : '더 보기'}
        </button>
      )}

      {/* 출처 칩(왼쪽)과 피드백 칩(오른쪽 끝)을 한 줄에. 좁으면 피드백이 다음 줄 오른쪽으로 */}
      <div className="mt-3 flex flex-wrap items-end gap-2">
        {sources.length > 0 && (
          <ul aria-label="근거 자료" className="flex min-w-0 flex-wrap gap-2">
            {sources.map((s, i) => (
              <SourceCard
                key={`${s?.documentId}-${s?.page}-${i}`}
                compact
                documentName={typeof s?.documentName === 'string' ? s.documentName : ''}
                page={Number.isInteger(s?.page) ? s.page : null}
              />
            ))}
          </ul>
        )}
        <span className="ml-auto">
          <FeedbackChip value={item.feedback} />
        </span>
      </div>
    </li>
  )
}
