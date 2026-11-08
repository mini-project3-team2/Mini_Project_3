// API 설계서 3.1 · Backend SignupRequest 와 같은 규칙
export const EMAIL_MAX = 100
export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const PW_RE = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z\d\s])\S{8,20}$/

export const isEmail = (v) => typeof v === 'string' && v.length <= EMAIL_MAX && EMAIL_RE.test(v)
export const isPassword = (v) => typeof v === 'string' && PW_RE.test(v)

export const MAX_FILE = 10 * 1024 * 1024

// 화면 검사는 보조 — 최종 검증은 서버(PdfValidator: 확장자 + %PDF- 내용 확인)
export function checkPdf(file) {
  if (!file) return '파일을 선택해 주세요.'
  if (file.size === 0) return '빈 파일은 올릴 수 없어요.'
  if (file.size > MAX_FILE) return '10MB 이하의 PDF만 올릴 수 있어요.'
  if (!file.name.trim().toLowerCase().endsWith('.pdf')) return 'PDF 파일만 올릴 수 있어요.'
  return ''
}

export function checkEmail(v) {
  if (!v) return '이메일을 입력해 주세요.'
  return isEmail(v) ? '' : '이메일 형식을 확인해 주세요.'
}

export function checkPassword(v) {
  if (!v) return '비밀번호를 입력해 주세요.'
  return isPassword(v) ? '' : '비밀번호는 8~20자이며 영문, 숫자, 특수문자를 모두 포함해야 해요.'
}
