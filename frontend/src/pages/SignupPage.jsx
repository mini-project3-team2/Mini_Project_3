import { useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AuthCard, { Field, FormAlert, SubmitButton } from '../components/AuthCard'
import { signup } from '../services/api'
import { errorMessage } from '../utils/errorMessage'
import { checkEmail, checkPassword } from '../utils/validate'

const errors = {
  DUPLICATE_EMAIL: '이미 가입된 이메일이에요. 다른 이메일을 쓰거나 로그인해 주세요.',
  409: '이미 가입된 이메일이에요. 다른 이메일을 쓰거나 로그인해 주세요.',
  400: '입력한 내용을 확인해 주세요. 이메일 형식과 비밀번호 규칙(8~20자, 영문·숫자·특수문자 포함)을 확인해 주세요.',
}

function validate(email, pw, pw2) {
  return {
    email: checkEmail(email),
    password: checkPassword(pw),
    confirm: !pw2 ? '비밀번호를 한 번 더 입력해 주세요.' : pw2 !== pw ? '비밀번호가 일치하지 않아요.' : '',
  }
}

export default function SignupPage() {
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [pw, setPw] = useState('')
  const [pw2, setPw2] = useState('')
  const [tried, setTried] = useState(false)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const lock = useRef(false)

  const fe = tried ? validate(email.trim(), pw, pw2) : {}

  const onSubmit = async (e) => {
    e.preventDefault()
    if (lock.current) return
    setTried(true)
    setErr('')
    const v = validate(email.trim(), pw, pw2)
    if (v.email || v.password || v.confirm) return

    lock.current = true
    setBusy(true)
    try {
      await signup(email.trim(), pw)
      nav('/login', { replace: true, state: { signedUp: true, email: email.trim() } })
    } catch (e2) {
      setErr(errorMessage(e2, errors))
      lock.current = false
      setBusy(false)
    }
  }

  return (
    <AuthCard
      title="회원가입"
      subtitle="계정을 만들고 내 수업 자료를 올려 보세요"
      footer={
        <>
          이미 계정이 있으신가요?{' '}
          <Link to="/login" className="font-semibold text-accent underline">
            로그인
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate>
        {err && <FormAlert>{err}</FormAlert>}
        <Field
          id="email"
          label="이메일"
          type="email"
          autoComplete="email"
          maxLength={100}
          placeholder="example@email.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={fe.email}
        />
        <Field
          id="password"
          label="비밀번호"
          type="password"
          autoComplete="new-password"
          maxLength={20}
          placeholder="비밀번호를 입력하세요"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          error={fe.password}
        />
        <Field
          id="password-confirm"
          label="비밀번호 확인"
          type="password"
          autoComplete="new-password"
          maxLength={20}
          placeholder="비밀번호를 한 번 더 입력하세요"
          value={pw2}
          onChange={(e) => setPw2(e.target.value)}
          error={fe.confirm}
        />
        <SubmitButton busy={busy} busyText="가입 중...">
          가입하기
        </SubmitButton>
      </form>
    </AuthCard>
  )
}
