import { Card, CardContent } from '@/components/ui/card'
import type { AnalyzeResponse } from '@/types'
import { CheckCircle, ImageOff, AlertTriangle, Wine } from 'lucide-react'

interface Props {
  results: AnalyzeResponse[]
}

export function BatchSummary({ results }: Props) {
  const total = results.length
  const pass = results.filter((r) => r.verdict === 'PASS').length
  const noImage = results.filter((r) => r.verdict === 'NO_IMAGE').length
  const error = results.filter((r) => r.verdict === 'ERROR').length
  const avgConfidence = total > 0 ? results.reduce((s, r) => s + r.confidence, 0) / total : 0

  const stats = [
    { label: 'Total', value: total, icon: <Wine className="h-5 w-5" />, color: 'text-foreground' },
    { label: 'Pass', value: pass, icon: <CheckCircle className="h-5 w-5" />, color: 'text-emerald-600' },
    { label: 'No Image', value: noImage, icon: <ImageOff className="h-5 w-5" />, color: 'text-gray-500' },
    { label: 'Error', value: error, icon: <AlertTriangle className="h-5 w-5" />, color: 'text-red-600' },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {stats.map((s) => (
        <Card key={s.label}>
          <CardContent className="flex items-center gap-3 py-3">
            <div className={s.color}>{s.icon}</div>
            <div>
              <p className="text-2xl font-bold">{s.value}</p>
              <p className="text-xs text-muted-foreground">{s.label}</p>
            </div>
          </CardContent>
        </Card>
      ))}
      <Card>
        <CardContent className="flex items-center gap-3 py-3">
          <div className="text-primary font-bold text-lg">%</div>
          <div>
            <p className="text-2xl font-bold">{Math.round(avgConfidence * 100)}</p>
            <p className="text-xs text-muted-foreground">Avg Confidence</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
