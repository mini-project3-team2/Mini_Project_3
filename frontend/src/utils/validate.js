// API 설계서 3.1 · Backend SignupRequest 와 같은 규칙
export const EMAIL_MAX = 100
export const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
export const PW_RE = /^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z\d\s])\S{8,20}$/

export const isEmail = (v) => typeof v === 'string' && v.length <= EMAIL_MAX && EMAIL_RE.test(v)
export const isPassword = (v) => typeof v === 'string' && PW_RE.test(v)

export function checkEmail(v) {
  if (!v) return '이메일을 입력해 주세요.'
  return isEmail(v) ? '' : '이메일 형식을 확인해 주세요.'
}

export function checkPassword(v) {
  if (!v) return '비밀번호를 입력해 주세요.'
  return isPassword(v) ? '' : '비밀번호는 8~20자이며 영문, 숫자, 특수문자를 모두 포함해야 해요.'
}
