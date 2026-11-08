import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import ChatInput from '../components/ChatInput'
import ChatMessage, { BookIcon } from '../components/ChatMessage'
import { UploadIcon } from '../components/FileUploader'
import useChatStream from '../hooks/useChatStream'
import useDocuments from '../hooks/useDocuments'
import { useChatStore } from '../store/chatStore'

const EXAMPLES = ['이 자료의 핵심 개념을 정리해 줘', '자료에 나온 두 개념은 뭐가 달라?', '이 내용은 왜 필요한 거야?']

const linkBtn = 'mt-5 inline-flex min-h-11 items-center rounded-md bg-accent px-5 text-sm font-semibold text-white hover:bg-accent/90'

// 첫 화면: 자료 목록을 못 불러왔으면 기본 문구, 0개면 올리기 안내, 적재 중뿐이면 기다림 안내, READY 가 있으면 예시 질문
function Welcome({ items, onPick }) {
  const ready = items?.filter((d) => d.status === 'READY').length ?? 0
  const icon = (el) => (
    <span className="flex size-11 items-center justify-center rounded-full bg-ready-bg text-accent">{el}</span>
  )

  if (items && items.length === 0) {
    return (
      <>
        {icon(<UploadIcon className="size-5" />)}
        <p className="mt-4 text-2xl font-bold">아직 업로드한 자료가 없어요</p>
        <p className="mt-2 text-sm text-ink/70">자료를 먼저 업로드해 주세요. PDF 자료를 업로드하면 그 내용으로 질문할 수 있어요</p>
        <Link to="/documents" className={linkBtn}>
          자료 업로드하러 가기
        </Link>
      </>
    )
  }
  if (items && ready === 0) {
    return (
      <>
        {icon(<BookIcon className="size-5" />)}
        <p className="mt-4 text-2xl font-bold">자료를 적재하고 있어요</p>
        <p className="mt-2 text-sm text-ink/70">적재가 끝난 자료부터 질문의 근거로 쓸 수 있어요</p>
        <Link to="/documents" className={linkBtn}>
          내 자료 보기
        </Link>
      </>
    )
  }
  return (
    <>
      {icon(<BookIcon className="size-5" />)}
      <p className="mt-4 text-2xl font-bold">무엇이 궁금한가요?</p>
      <p className="mt-2 text-sm text-ink/70">
        {ready > 0 ? `업로드한 자료 ${ready}개를 근거로 찾아서 답해 드려요` : '업로드한 자료를 근거로 찾아서 답해 드려요'}
      </p>
      {ready > 0 && (
        <div className="mt-6">
          <p className="text-xs font-semibold text-ink/70">이렇게 물어볼 수 있어요</p>
          <ul className="mt-3 flex flex-wrap justify-center gap-2">
            {EXAMPLES.map((q) => (
              <li key={q}>
                <button
                  type="button"
                  onClick={() => onPick(q)}
                  className="min-h-11 rounded-full border border-ink/30 bg-white px-4 text-sm hover:border-accent"
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}

// 스크린리더용: token 마다가 아니라 상태가 바뀔 때만 문구가 바뀐다 (오류는 FormAlert 의 role=alert 가 알림)
function liveText(m) {
  if (!m) return ''
  if (m.status === 'waiting' || m.status === 'streaming') return '답변을 준비하고 있어요'
  if (m.status === 'done') return `답변이 도착했어요. ${m.answer}`
  if (m.status === 'stopped') return '답변을 중단했어요'
  return ''
}

const nearBottom = () => window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 160

export default function ChatPage() {
  const messages = useChatStore((s) => s.messages)
  const patch = useChatStore((s) => s.patch)
  const { send, stop, busy } = useChatStream()
  const { items } = useDocuments()
  const [text, setText] = useState('')
  const inputRef = useRef(null)
  const endRef = useRef(null)
  const stick = useRef(true)
  const count = useRef(messages.length)

  useEffect(() => {
    const onScroll = () => {
      stick.current = nearBottom()
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // 새 질문을 보내면 항상, 답변이 이어질 때는 사용자가 아래쪽을 보고 있을 때만 따라 내려간다
  useEffect(() => {
    const added = messages.length > count.current
    count.current = messages.length
    if (added || stick.current) endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages])

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-7rem)] w-full max-w-3xl flex-col">
      <h1 className="sr-only">AI 학습 채팅</h1>

      {messages.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center py-10 text-center">
          <Welcome
            items={items}
            onPick={(q) => {
              setText(q)
              inputRef.current?.focus()
            }}
          />
        </div>
      ) : (
        <div className="flex-1 space-y-8 pb-6">
          {messages.map((m) => (
            <ChatMessage key={m.id} msg={m} onFeedback={(v) => patch(m.id, { feedback: v })} />
          ))}
        </div>
      )}
      <div ref={endRef} />

      <div className="sticky bottom-0 bg-bg pb-1 pt-2">
        <ChatInput busy={busy} text={text} onText={setText} inputRef={inputRef} onSend={send} onStop={stop} />
        <p className="mt-2 text-center text-xs text-ink/60">
          답변은 내가 업로드한 자료만 근거로 만들어져요. 자료에 없는 내용은 추측하지 않아요.
        </p>
      </div>

      <div aria-live="polite" className="sr-only">
        {liveText(messages.at(-1))}
      </div>
    </div>
  )
}
