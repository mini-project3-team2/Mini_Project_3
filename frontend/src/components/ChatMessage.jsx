import { Link } from 'react-router-dom'
import FeedbackButtons from './FeedbackButtons'
import FormAlert from './FormAlert'
import SourceCard from './SourceCard'

export function BookIcon({ className = 'size-4' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M12 7v13M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z" />
    </svg>
  )
}

function Progress({ children }) {
  return (
    <p className="mt-2 flex items-center gap-2 text-xs text-ink/70">
      <span className="size-3.5 rounded-full border-2 border-accent border-t-transparent motion-safe:animate-spin" aria-hidden="true" />
      {children}
    </p>
  )
}

// 질문 · 답변 · 출처는 모두 텍스트로만 출력 (마크다운 · HTML 해석 안 함)
export default function ChatMessage({ msg, onFeedback }) {
  const { question, answer, sources, status, error, chatId, feedback } = msg
  const live = status === 'streaming' || status === 'done'

  return (
    <article className="space-y-4">
      <div className="flex justify-end">
        <p className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl bg-accent px-4 py-2.5 text-sm text-white">
          {question}
        </p>
      </div>

      <div className="flex gap-3">
        <span className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-ready-bg text-accent">
          <BookIcon />
        </span>
        <div className="min-w-0 flex-1">
          {status === 'waiting' && <Progress>답변을 준비하고 있어요</Progress>}

          {answer && (
            <p className="whitespace-pre-wrap break-words rounded-xl border border-line bg-white px-4 py-3 text-sm leading-relaxed">
              {answer}
            </p>
          )}

          {status === 'streaming' && <Progress>내 자료에서 찾아서 답변하는 중이에요</Progress>}

          {/* 출처는 답변이 끝난 뒤에만 (거절 판별이 done 에서 끝나므로 스트리밍 중에는 숨김) */}
          {status === 'done' && sources.length > 0 && (
            <section className="mt-3">
              <h3 className="mb-2 text-xs font-semibold text-ink/70">근거 자료</h3>
              <ul className="flex flex-wrap gap-2">
                {sources.map((s, i) => (
                  <SourceCard key={`${s.documentId}-${s.page}-${i}`} documentName={s.documentName} page={s.page} />
                ))}
              </ul>
            </section>
          )}

          {live && <FeedbackButtons chatId={chatId} value={feedback} onChange={onFeedback} />}

          {status === 'stopped' && (
            <p className="mt-2 text-xs text-ink/70">답변을 중단했어요. 이 답변은 질문 기록에 저장되지 않아요.</p>
          )}

          {status === 'error' && (
            <FormAlert className={answer ? 'mt-3' : ''}>
              <p>{error?.text}</p>
              {error?.code === 'NO_DOCUMENT' && (
                <Link to="/documents" className="mt-1 inline-block font-semibold underline">
                  내 자료로 가서 업로드하기
                </Link>
              )}
            </FormAlert>
          )}
        </div>
      </div>
    </article>
  )
}
