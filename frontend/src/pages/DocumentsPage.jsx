import { FormNotice } from '../components/AuthCard'
import DocumentList from '../components/DocumentList'
import FileUploader, { UploadIcon } from '../components/FileUploader'
import FormAlert from '../components/FormAlert'
import LoadingSpinner from '../components/LoadingSpinner'
import useDocuments from '../hooks/useDocuments'
import { useDocumentStore } from '../store/documentStore'

export default function DocumentsPage() {
  const { items, loadError, load, loading } = useDocuments()
  const uploading = useDocumentStore((s) => s.uploading)
  const uploadError = useDocumentStore((s) => s.uploadError)
  const deletingId = useDocumentStore((s) => s.deletingId)
  const actionError = useDocumentStore((s) => s.actionError)
  const notice = useDocumentStore((s) => s.notice)
  const upload = useDocumentStore((s) => s.upload)
  const remove = useDocumentStore((s) => s.remove)
  const setUploadError = useDocumentStore((s) => s.setUploadError)

  return (
    <div className="mx-auto w-full max-w-4xl">
      <h1 className="text-2xl font-bold">내 자료</h1>
      <p className="mt-2 text-sm text-ink/70">여기에 올린 자료만 질문의 근거로 쓰여요. 다른 사람은 내 자료를 볼 수 없어요.</p>

      <div className="mt-6">
        <FileUploader busy={!!uploading} onFile={upload} onError={setUploadError} />
      </div>

      <div className="mt-4">
        {uploadError && <FormAlert className="mb-4">{uploadError}</FormAlert>}
        {actionError && <FormAlert className="mb-4">{actionError}</FormAlert>}
        {notice && <FormNotice>{notice}</FormNotice>}
      </div>

      {loading && <LoadingSpinner />}

      {!items && loadError && (
        <FormAlert>
          <p>{loadError}</p>
          <button type="button" onClick={load} className="mt-2 min-h-11 rounded-md border border-red-300 bg-white px-4 font-semibold">
            다시 시도
          </button>
        </FormAlert>
      )}

      {items && (items.length > 0 || uploading) && (
        <DocumentList items={items} uploading={uploading} deletingId={deletingId} onDelete={remove} />
      )}

      {items && items.length === 0 && !uploading && (
        <div className="flex flex-col items-center rounded-xl border border-line bg-white px-6 py-12 text-center">
          <span className="flex size-11 items-center justify-center rounded-full bg-ready-bg text-accent">
            <UploadIcon className="size-5" />
          </span>
          <p className="mt-4 font-semibold">아직 올린 자료가 없어요</p>
          <p className="mt-2 text-sm text-ink/70">PDF 자료를 올리면 그 내용으로 질문할 수 있어요</p>
        </div>
      )}
    </div>
  )
}
