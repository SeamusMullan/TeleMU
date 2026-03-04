/** Page loading skeleton — pulsing dark blocks. */

export default function PageSkeleton() {
  return (
    <div className="p-4">
      <div className="mb-4 h-6 w-48 animate-pulse rounded bg-neutral-800" />
      <div className="grid grid-cols-3 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-32 animate-pulse rounded-lg bg-neutral-800" />
        ))}
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded-lg bg-neutral-800" />
        ))}
      </div>
    </div>
  );
}
