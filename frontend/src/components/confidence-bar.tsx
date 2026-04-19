import { cn } from '@/lib/utils'

export function ConfidenceBar({ value, className }: { value: number; className?: string }) {
  const pct = Math.round(value * 100)
  const color =
    pct >= 85 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500'

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="h-2 flex-1 rounded-full bg-gray-200 overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono font-medium text-muted-foreground w-10 text-right">
        {pct}%
      </span>
    </div>
  )
}
