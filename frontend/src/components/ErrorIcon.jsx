// 높이를 부모 글자의 줄 높이(1lh)에 맞춰 첫 줄과 세로 가운데 정렬
export default function ErrorIcon() {
  return (
    <span className="flex h-[1lh] shrink-0 items-center" aria-hidden="true">
      <svg
        viewBox="0 0 24 24"
        className="size-4"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 7v6" />
        <circle cx="12" cy="16.5" r="1.25" fill="currentColor" stroke="none" />
      </svg>
    </span>
  )
}
