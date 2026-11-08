import ErrorIcon from './ErrorIcon'

export default function FormAlert({ children, className = 'mb-5' }) {
  return (
    <div role="alert" className={`flex gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800 ${className}`}>
      <ErrorIcon />
      <div>{children}</div>
    </div>
  )
}
