import { useRef, useState } from 'react'

export function UploadIcon({ className = 'size-6' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M12 15V3M7 8l5-5 5 5M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    </svg>
  )
}

// 파일 선택 · 드래그 앤 드롭 (한 번에 1개). 검사는 onFile 쪽(store)에서 한다
export default function FileUploader({ busy, onFile, onError }) {
  const input = useRef(null)
  const [over, setOver] = useState(false)

  const pick = (files) => {
    if (busy || !files?.length) return
    if (files.length > 1) return onError('파일은 한 번에 하나씩 올려 주세요.')
    onFile(files[0])
  }

  const onDrop = (e) => {
    e.preventDefault()
    setOver(false)
    pick(e.dataTransfer.files)
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault()
        if (!busy) setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
      className={`flex flex-col items-center rounded-xl border-2 border-dashed px-6 py-8 text-center ${
        over ? 'border-accent bg-ready-bg' : 'border-ink/30 bg-white'
      }`}
    >
      <span className="text-accent">
        <UploadIcon />
      </span>
      {busy ? (
        <>
          <p className="mt-3 flex items-center gap-2 text-sm font-semibold">
            <span className="size-4 rounded-full border-2 border-accent border-t-transparent motion-safe:animate-spin" aria-hidden="true" />
            자료를 올리고 정리하는 중이에요
          </p>
          <p className="mt-2 text-xs text-ink/70">자료 크기에 따라 몇 분 걸릴 수 있어요. 끝날 때까지 기다려 주세요.</p>
        </>
      ) : (
        <>
          <p className="mt-3 text-sm font-semibold">PDF 파일을 여기로 끌어다 놓으세요</p>
          <p className="mt-2 text-xs text-ink/70">PDF만 올릴 수 있고, 파일 하나당 10MB까지 가능해요</p>
        </>
      )}
      <input
        ref={input}
        id="file"
        type="file"
        accept=".pdf,application/pdf"
        className="sr-only"
        tabIndex={-1}
        onChange={(e) => {
          pick(e.target.files)
          e.target.value = ''
        }}
      />
      <button
        type="button"
        onClick={() => input.current?.click()}
        disabled={busy}
        aria-busy={busy}
        className="mt-4 min-h-11 rounded-md bg-accent px-5 text-sm font-semibold text-white hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {busy ? '올리는 중...' : '파일 선택'}
      </button>
    </div>
  )
}
