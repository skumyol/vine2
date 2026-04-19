import { VerdictBadge } from '@/components/verdict-badge'
import { ConfidenceBar } from '@/components/confidence-bar'
import type { AnalyzeResponse } from '@/types'

interface Props {
  results: AnalyzeResponse[]
  onSelect: (index: number) => void
  selectedIndex: number | null
}

export function ResultsTable({ results, onSelect, selectedIndex }: Props) {
  if (results.length === 0) return null

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left">
            <th className="py-3 pr-3 font-medium text-muted-foreground w-8">#</th>
            <th className="py-3 pr-3 font-medium text-muted-foreground">Wine</th>
            <th className="py-3 pr-3 font-medium text-muted-foreground w-24">Vintage</th>
            <th className="py-3 pr-3 font-medium text-muted-foreground w-24">Region</th>
            <th className="py-3 pr-3 font-medium text-muted-foreground">Photo URL</th>
            <th className="py-3 pr-3 font-medium text-muted-foreground w-28">Verdict</th>
            <th className="py-3 font-medium text-muted-foreground w-36">Confidence</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r, i) => (
            <tr
              key={i}
              onClick={() => onSelect(i)}
              className={`border-b border-border/50 last:border-0 cursor-pointer transition-colors hover:bg-accent ${
                selectedIndex === i ? 'bg-accent' : ''
              }`}
            >
              <td className="py-3 pr-3 text-muted-foreground font-mono text-xs">{i + 1}</td>
              <td className="py-3 pr-3 font-medium truncate max-w-[300px]">
                {r.input.wine_name}
              </td>
              <td className="py-3 pr-3 text-muted-foreground">{r.input.vintage}</td>
              <td className="py-3 pr-3 text-muted-foreground">{r.input.region || '—'}</td>
              <td className="py-3 pr-3 max-w-[260px] truncate text-xs text-muted-foreground">
                {r.selected_image_url ? (
                  <a
                    href={r.selected_image_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {r.selected_image_url}
                  </a>
                ) : (
                  'No Image'
                )}
              </td>
              <td className="py-3 pr-3">
                <VerdictBadge verdict={r.verdict} />
              </td>
              <td className="py-3">
                <ConfidenceBar value={r.confidence} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
