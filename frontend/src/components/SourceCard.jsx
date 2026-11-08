function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-4 shrink-0 text-accent" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M8 13h8M8 17h5" />
    </svg>
  )
}

export default function SourceCard({ documentName, page }) {
  return (
    <li className="flex min-h-11 max-w-full items-center gap-2 rounded-lg border border-line bg-white px-3 py-2">
      <FileIcon />
      <div className="min-w-0">
        <p className="truncate text-sm" title={documentName}>
          {documentName || '이름 없는 자료'}
        </p>
        {page != null && <p className="text-xs text-ink/60">{page}쪽</p>}
      </div>
    </li>
  )
}
