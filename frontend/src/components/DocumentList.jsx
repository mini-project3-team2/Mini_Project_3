import { useState } from 'react'
import { formatDateTime } from '../utils/errorMessage'
import { formatBytes } from '../utils/format'
import StatusBadge from './StatusBadge'

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-4 shrink-0 text-accent" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M8 13h8M8 17h5" />
    </svg>
  )
}

const btn = 'min-h-11 whitespace-nowrap rounded-md border px-3 text-sm disabled:cursor-not-allowed disabled:opacity-50'
// 이름 외 열은 줄바꿈 없이 내용 폭만, 이름 열은 w-full + max-w-0 로 남는 폭을 모두 차지하고 말줄임
const cell = 'whitespace-nowrap px-3 py-3 sm:px-5'
// 좁은 화면에서는 크기(640px 미만) · 올린 시각(768px 미만) 열을 숨긴다
const sizeCol = 'hidden sm:table-cell'
const timeCol = 'hidden md:table-cell'

function NameCell({ name }) {
  return (
    <td className="w-full max-w-0 px-3 py-3">
      <div className="flex items-center gap-2">
        <FileIcon />
        <span className="min-w-0 truncate" title={name}>
          {name}
        </span>
      </div>
    </td>
  )
}

// 삭제는 화면 안에서 한 번 더 확인 (INDEXING 도 삭제 가능 — API 설계서 4.2)
// 확인 영역은 행 아래 전체 폭 줄에 열어 표 폭을 넓히지 않는다
function Row({ doc, deleting, locked, onDelete }) {
  const [ask, setAsk] = useState(false)
  const name = doc.originalFilename

  return (
    <>
      <tr className="border-t border-line">
        <NameCell name={name} />
        <td className={cell}>
          <StatusBadge status={doc.status} />
        </td>
        <td className={`${cell} ${sizeCol}`}>{formatBytes(doc.fileSize)}</td>
        <td className={`${cell} ${timeCol} text-ink/70`}>{formatDateTime(doc.createdAt)}</td>
        <td className="px-3 py-2 text-right sm:pl-5">
          {deleting ? (
            <button type="button" disabled aria-busy="true" className={`${btn} border-line`}>
              삭제 중
            </button>
          ) : (
            <button
              type="button"
              disabled={locked || ask}
              onClick={() => setAsk(true)}
              aria-label={`${name} 삭제`}
              aria-expanded={ask}
              className={`${btn} border-red-700 bg-white text-red-700`}
            >
              삭제
            </button>
          )}
        </td>
      </tr>
      {ask && !deleting && (
        <tr className="bg-red-50">
          <td colSpan={5} className="px-3 py-2">
            <div role="group" aria-label={`${name} 삭제 확인`} className="flex flex-wrap items-center justify-end gap-x-4 gap-y-2">
              <span className="text-sm text-red-800">이 자료를 삭제할까요?</span>
              <div className="flex gap-2">
                <button type="button" autoFocus onClick={() => setAsk(false)} className={`${btn} border-ink/30 bg-white`}>
                  취소
                </button>
                <button
                  type="button"
                  disabled={locked}
                  onClick={() => {
                    setAsk(false)
                    onDelete(doc.id)
                  }}
                  className={`${btn} border-red-700 bg-red-700 font-semibold text-white`}
                >
                  삭제
                </button>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

export default function DocumentList({ items, uploading, deletingId, onDelete }) {
  return (
    <section className="overflow-hidden rounded-xl border border-line bg-white">
      <h2 className="px-4 py-4 text-sm font-semibold">자료 목록</h2>
      <table className="w-full text-left text-sm">
        <thead className="bg-bg/60 text-xs text-ink/70">
          <tr className="whitespace-nowrap">
            <th scope="col" className="px-3 py-2.5 font-semibold">파일 이름</th>
            <th scope="col" className="px-3 py-2.5 sm:px-5 font-semibold">상태</th>
            <th scope="col" className={`px-3 py-2.5 sm:px-5 font-semibold ${sizeCol}`}>크기</th>
            <th scope="col" className={`px-3 py-2.5 sm:px-5 font-semibold ${timeCol}`}>업로드 시각</th>
            <th scope="col" className="px-3 py-2.5 sm:pl-5">
              <span className="sr-only">삭제</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {uploading && (
            <tr className="border-t border-line" aria-busy="true">
              <NameCell name={uploading.name} />
              <td className={cell}>
                <StatusBadge status="INDEXING" />
              </td>
              <td className={`${cell} ${sizeCol}`}>{formatBytes(uploading.size)}</td>
              <td className={`${cell} ${timeCol} text-ink/70`}>업로드 중</td>
              <td className="px-3 py-2 sm:pl-5" />
            </tr>
          )}
          {items.map((d) => (
            <Row
              key={d.id}
              doc={d}
              deleting={deletingId === d.id}
              locked={deletingId != null}
              onDelete={onDelete}
            />
          ))}
        </tbody>
      </table>
    </section>
  )
}
