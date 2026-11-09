import { useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import AuthCard, { Field, FormNotice, SubmitButton } from '../components/AuthCard'
import FormAlert from '../components/FormAlert'
import { login } from '../services/api'
import { useAuthStore } from '../store/authStore'
import { errorMessage, lockedText } from '../utils/errorMessage'

// 서버 message 가 없을 때만 쓰는 문구
const BAD = '이메일 또는 비밀번호가 올바르지 않아요.'

const errors = {
  INVALID_CREDENTIALS: BAD,
  401: BAD,
  ACCOUNT_LOCKED: '로그인에 여러 번 실패해 계정이 잠겼어요.',
  423: '로그인에 여러 번 실패해 계정이 잠겼어요.',
  400: '이메일과 비밀번호를 입력해 주세요.',
}

export default function LoginPage() {
  const loc = useLocation()
  const expired = useAuthStore((s) => s.expired)
  const [email, setEmail] = useState(loc.state?.email ?? '')
  const [pw, setPw] = useState('')
  const [fieldErr, setFieldErr] = useState({})
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const lock = useRef(false)

  const onSubmit = async (e) => {
    e.preventDefault()
    if (lock.current) return
    const fe = {
      email: email.trim() ? '' : '이메일을 입력해 주세요.',
      password: pw ? '' : '비밀번호를 입력해 주세요.',
    }
    setFieldErr(fe)
    setErr(null)
    if (fe.email || fe.password) return

    lock.current = true
    setBusy(true)
    try {
      await login(email.trim(), pw)
    } catch (e2) {
      setErr({ text: errorMessage(e2, errors), sub: lockedText(e2) })
      lock.current = false
      setBusy(false)
    }
  }

  return (
    <AuthCard
      title="AskNote"
      subtitle="내가 업로드한 수업 자료로 복습 질문에 답해 드려요"
      footer={
        <>
          계정이 없으신가요?{' '}
          <Link to="/signup" className="font-semibold text-accent underline">
            회원가입
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate>
        {err && (
          <FormAlert>
            {err.text}
            {err.sub && <span className="mt-1 block">{err.sub}</span>}
          </FormAlert>
        )}
        {!err && loc.state?.signedUp && <FormNotice>회원가입이 완료되었어요. 로그인해 주세요.</FormNotice>}
        {!err && !loc.state?.signedUp && expired && (
          <FormNotice tone="info">세션이 만료되었어요. 다시 로그인해 주세요.</FormNotice>
        )}
        <Field
          id="email"
          label="이메일"
          type="email"
          autoComplete="email"
          placeholder="example@email.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fieldErr.email}
        />
        <Field
          id="password"
          label="비밀번호"
          type="password"
          autoComplete="current-password"
          placeholder="비밀번호를 입력하세요"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          error={fieldErr.password}
        />
        <SubmitButton busy={busy} busyText="로그인 중...">
          로그인
        </SubmitButton>
      </form>
    </AuthCard>
  )
}
