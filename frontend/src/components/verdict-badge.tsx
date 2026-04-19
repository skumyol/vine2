import { Badge } from '@/components/ui/badge'
import type { Verdict } from '@/types'
import { CheckCircle, ImageOff, AlertTriangle } from 'lucide-react'

const config: Record<Verdict, { variant: 'success' | 'muted' | 'destructive'; icon: React.ReactNode; label: string }> = {
  PASS: { variant: 'success', icon: <CheckCircle className="h-3.5 w-3.5" />, label: 'PASS' },
  NO_IMAGE: { variant: 'muted', icon: <ImageOff className="h-3.5 w-3.5" />, label: 'NO IMAGE' },
  ERROR: { variant: 'destructive', icon: <AlertTriangle className="h-3.5 w-3.5" />, label: 'ERROR' },
}

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const c = config[verdict]
  return (
    <Badge variant={c.variant} className="gap-1">
      {c.icon}
      {c.label}
    </Badge>
  )
}
