import { useEffect, useRef } from 'react'
import ChatInput from '../components/ChatInput'
import ChatMessage, { BookIcon } from '../components/ChatMessage'
import useChatStream from '../hooks/useChatStream'
import { useChatStore } from '../store/chatStore'

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
          <span className="flex size-11 items-center justify-center rounded-full bg-ready-bg text-accent">
            <BookIcon className="size-5" />
          </span>
          <p className="mt-4 text-2xl font-bold">무엇이 궁금한가요?</p>
          <p className="mt-2 text-sm text-ink/70">올린 자료를 근거로 찾아서 답해 드려요</p>
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
        <ChatInput busy={busy} onSend={send} onStop={stop} />
        <p className="mt-2 text-center text-xs text-ink/60">
          답변은 내가 올린 자료만 근거로 만들어져요. 자료에 없는 내용은 추측하지 않아요.
        </p>
      </div>

      <div aria-live="polite" className="sr-only">
        {liveText(messages.at(-1))}
      </div>
    </div>
  )
}
