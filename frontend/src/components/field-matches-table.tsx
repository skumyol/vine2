import { Badge } from '@/components/ui/badge'
import type { FieldMatch, FieldStatus } from '@/types'

const STATUS_CONFIG: Record<FieldStatus, { variant: 'success' | 'destructive' | 'warning' | 'muted'; label: string }> = {
  match: { variant: 'success', label: 'Match' },
  conflict: { variant: 'destructive', label: 'Conflict' },
  no_signal: { variant: 'warning', label: 'No Signal' },
  unverified: { variant: 'muted', label: 'Unverified' },
}

const FIELD_LABELS: Record<string, string> = {
  producer: 'Producer',
  appellation: 'Appellation',
  vineyard_or_cuvee: 'Vineyard / Cuvée',
  classification: 'Classification',
  vintage: 'Vintage',
}

interface Props {
  fieldMatches: Record<string, FieldMatch>
}

export function FieldMatchesTable({ fieldMatches }: Props) {
  const entries = Object.entries(fieldMatches)
  if (entries.length === 0) return null

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left">
            <th className="py-2 pr-4 font-medium text-muted-foreground">Field</th>
            <th className="py-2 pr-4 font-medium text-muted-foreground">Target</th>
            <th className="py-2 pr-4 font-medium text-muted-foreground">Extracted</th>
            <th className="py-2 pr-4 font-medium text-muted-foreground">Status</th>
            <th className="py-2 font-medium text-muted-foreground text-right">Conf.</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([key, fm]) => {
            const sc = STATUS_CONFIG[fm.status]
            return (
              <tr key={key} className="border-b border-border/50 last:border-0">
                <td className="py-2 pr-4 font-medium">{FIELD_LABELS[key] ?? key}</td>
                <td className="py-2 pr-4 text-muted-foreground font-mono text-xs">
                  {fm.target ?? '—'}
                </td>
                <td className="py-2 pr-4 text-muted-foreground font-mono text-xs">
                  {fm.extracted ?? '—'}
                </td>
                <td className="py-2 pr-4">
                  <Badge variant={sc.variant}>{sc.label}</Badge>
                </td>
                <td className="py-2 text-right font-mono text-xs">
                  {Math.round(fm.confidence * 100)}%
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
