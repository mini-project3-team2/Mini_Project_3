import { ICON, PILL, THUMB_DOWN, THUMB_UP, TONE } from './feedbackStyle'

const kinds = {
  HELPFUL: ['도움됨', THUMB_UP, TONE.HELPFUL],
  NOT_HELPFUL: ['도움 안 됨', THUMB_DOWN, TONE.NOT_HELPFUL],
}
const NONE = ['평가하지 않음', null, TONE.NONE]

// 질문 기록용 읽기 전용 피드백 표시 (클릭 · 호버 · 포커스 없음). 색 외에 글자로도 구분하고, 스크린리더에는 "피드백: …"으로 읽힌다
export default function FeedbackChip({ value }) {
  const [label, icon, tone] = kinds[value] ?? NONE
  return (
    <span className={`${PILL} ${tone}`}>
      {icon && (
        <svg viewBox="0 0 24 24" className={ICON} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d={icon} />
        </svg>
      )}
      <span className="sr-only">피드백: </span>
      {label}
    </span>
  )
}
