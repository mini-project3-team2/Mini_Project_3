import { useEffect } from 'react'
import { useDocumentStore } from '../store/documentStore'

// 화면에 들어올 때마다 목록을 새로 불러온다 (이미 있던 목록은 그대로 보여 주며 갱신)
export default function useDocuments() {
  const items = useDocumentStore((s) => s.items)
  const loadError = useDocumentStore((s) => s.loadError)
  const load = useDocumentStore((s) => s.load)

  useEffect(() => {
    load()
  }, [load])

  return { items, loadError, load, loading: items === null && !loadError }
}
