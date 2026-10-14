export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="status" role="status">
      <span className="spinner" aria-hidden /> {label}
    </div>
  )
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="status error" role="alert">
      Something went wrong: {message}. Is the backend running on port 8000?
    </div>
  )
}
