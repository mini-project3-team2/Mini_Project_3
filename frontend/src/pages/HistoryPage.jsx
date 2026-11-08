import { useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import FormAlert from '../components/FormAlert'
import HistoryItem from '../components/HistoryItem'
import LoadingSpinner from '../components/LoadingSpinner'
import Pagination from '../components/Pagination'
import useHistory from '../hooks/useHistory'

// URL ?page=N 은 1부터 (뒤로 가기 · 새로고침에도 같은 페이지). 잘못된 값은 1페이지로
function readPage(raw) {
  return raw && /^\d{1,6}$/.test(raw) && Number(raw) >= 1 ? Number(raw) - 1 : 0
}

export default function HistoryPage() {
  const [params, setParams] = useSearchParams()
  const raw = params.get('page')
  const page = readPage(raw)
  const { data, loading, error, retry } = useHistory(page)

  const go = (p, replace = false) => {
    setParams(p > 0 ? { page: String(p + 1) } : {}, { replace })
    if (!replace) window.scrollTo({ top: 0 })
  }

  // 주소의 page 값 정리: 잘못된 값 → 1페이지, 범위 밖 → 서버가 알려 준 마지막 페이지
  useEffect(() => {
    if (raw != null && raw !== String(page + 1)) {
      setParams(page > 0 ? { page: String(page + 1) } : {}, { replace: true })
      return
    }
    if (!data || loading || data.page !== page) return
    const last = Math.max(0, data.totalPages - 1)
    if (page > last) setParams(last > 0 ? { page: String(last + 1) } : {}, { replace: true })
  }, [raw, page, data, loading, setParams])

  return (
    <div className="mx-auto w-full max-w-4xl">
      <h1 className="text-2xl font-bold">질문 기록</h1>
      <p className="mt-2 text-sm text-ink/70">내가 했던 질문과 받은 답변을 다시 볼 수 있어요.</p>

      <div className="mt-6" aria-busy={loading}>
        {error ? (
          <FormAlert>
            <p>{error}</p>
            <button type="button" onClick={retry} className="mt-2 min-h-11 rounded-md border border-red-300 bg-white px-4 font-semibold">
              다시 시도
            </button>
          </FormAlert>
        ) : !data ? (
          <LoadingSpinner />
        ) : data.totalElements === 0 ? (
          <div className="flex flex-col items-center rounded-xl border border-line bg-white px-6 py-12 text-center">
            <p className="font-semibold">아직 질문 기록이 없어요</p>
            <p className="mt-2 text-sm text-ink/70">AI 학습 채팅에서 질문하면 여기에 기록이 남아요</p>
            <Link
              to="/chat"
              className="mt-5 inline-flex min-h-11 items-center rounded-md bg-accent px-5 text-sm font-semibold text-white hover:bg-accent/90"
            >
              AI 학습 채팅으로 가기
            </Link>
          </div>
        ) : (
          <>
            {loading && <LoadingSpinner />}
            <ul className={`space-y-3 ${loading ? 'opacity-60' : ''}`}>
              {data.content.map((c) => (
                <HistoryItem key={c.id} item={c} />
              ))}
            </ul>
            <Pagination page={data.page} totalPages={data.totalPages} disabled={loading} onChange={(p) => go(p)} />
          </>
        )}
      </div>
    </div>
  )
}
