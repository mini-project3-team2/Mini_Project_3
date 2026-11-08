// Backend ChatStreamService.isRefusal 과 같은 기준 (공백 제거 후 80자 이하 + 거절 문구 포함). 문구는 서버 문구 그대로
export const REFUSAL_PHRASE = '올린자료에서관련내용을찾지못했어요'
export const REFUSAL_MAX_LENGTH = 80

// Java 의 \s 처럼 ASCII 공백만 지운다
export function isRefusal(answer) {
  if (typeof answer !== 'string') return false
  const compact = answer.replace(/[ \t\n\v\f\r]+/g, '')
  return compact.length <= REFUSAL_MAX_LENGTH && compact.includes(REFUSAL_PHRASE)
}
