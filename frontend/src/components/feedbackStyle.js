// 피드백 칩(질문 기록)과 피드백 버튼(채팅)이 함께 쓰는 모양 · 크기 — 한쪽만 바뀌지 않도록 여기서만 정의
export const PILL = 'inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full border px-2.5 py-1 text-xs'
export const ICON = 'size-3.5'

// 채팅 피드백 버튼: 선택된 버튼은 값과 상관없이 초록 강조 / 선택 안 된 버튼은 흰 배경 + 연한 테두리
export const BUTTON_ON = 'border-accent bg-ready-bg font-semibold text-accent'
export const BUTTON_OFF = 'border-ink/15 bg-white text-ink/80 hover:border-ink/30'

// 질문 기록 피드백 칩: 값마다 다른 색
export const TONE = {
  HELPFUL: 'border-accent bg-ready-bg font-semibold text-accent',
  NOT_HELPFUL: 'border-ink/60 bg-white font-semibold text-ink',
  NONE: 'border-ink/20 bg-white text-ink/60',
}

export const THUMB_UP =
  'M7 10v12M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z'
export const THUMB_DOWN =
  'M17 14V2M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z'
