import { useEffect } from 'react'
import { useHistoryStore } from '../store/historyStore'

// page(0부터)가 바뀌거나 화면에 들어올 때마다 서버에서 다시 불러온다
// 화면을 떠나면 비워서, 다음에 들어올 때 이전 값(예: 채팅에서 바꾸기 전 피드백)이 잠깐 보이지 않게 한다
export default function useHistory(page) {
  const data = useHistoryStore((s) => s.data)
  const loading = useHistoryStore((s) => s.loading)
  const error = useHistoryStore((s) => s.error)
  const load = useHistoryStore((s) => s.load)
  const reset = useHistoryStore((s) => s.reset)

  useEffect(() => {
    load(page)
  }, [page, load])

  useEffect(() => reset, [reset])

  return { data, loading, error, retry: () => load(page) }
}
