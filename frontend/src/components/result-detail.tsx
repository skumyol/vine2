import { useState } from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ConfidenceBar } from '@/components/confidence-bar'
import { FieldMatchesTable } from '@/components/field-matches-table'
import { VerdictBadge } from '@/components/verdict-badge'
import type { AnalyzeResponse } from '@/types'
import { ChevronDown, ChevronUp, ExternalLink, ImageOff, Wine } from 'lucide-react'

interface Props {
  result: AnalyzeResponse
  index?: number
}

export function ResultDetail({ result, index }: Props) {
  const [showDebug, setShowDebug] = useState(false)
  const pi = result.parsed_identity
  const pipelineNote = result.debug.notes.find((note) => note.startsWith('pipeline:'))
  const pipelineName = pipelineNote?.split(':')[1] ?? 'voter'

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              {index !== undefined && (
                <span className="text-xs font-mono text-muted-foreground">#{index + 1}</span>
              )}
              <h3 className="text-base font-semibold truncate">{result.input.wine_name}</h3>
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">
              {result.input.vintage} &middot; {result.input.format}
              {result.input.region ? ` \u00B7 ${result.input.region}` : ''}
            </p>
          </div>
          <VerdictBadge verdict={result.verdict} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Image */}
          <div className="flex items-center justify-center rounded-lg bg-muted min-h-[200px] overflow-hidden">
            {result.selected_image_url ? (
              <img
                src={result.selected_image_url}
                alt={result.input.wine_name}
                className="max-h-[300px] object-contain"
                onError={(e) => {
                  const target = e.target as HTMLImageElement
                  target.style.display = 'none'
                  target.parentElement!.innerHTML =
                    '<div class="flex flex-col items-center gap-2 text-muted-foreground"><svg class="h-12 w-12" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg><span class="text-xs">Failed to load</span></div>'
                }}
              />
            ) : (
              <div className="flex flex-col items-center gap-2 text-muted-foreground">
                {result.verdict === 'PASS' ? (
                  <Wine className="h-12 w-12" />
                ) : (
                  <ImageOff className="h-12 w-12" />
                )}
                <span className="text-xs">No image</span>
              </div>
            )}
          </div>

          {/* Details */}
          <div className="lg:col-span-2 space-y-4">
            {/* Confidence */}
            <div>
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Confidence</span>
              <ConfidenceBar value={result.confidence} className="mt-1" />
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge variant="muted">Pipeline: {pipelineName}</Badge>
                {result.debug.module_votes.map((vote) => (
                  <Badge key={`${vote.module}-${vote.weight}`} variant={vote.passed ? 'success' : 'muted'}>
                    {vote.module}: {(vote.confidence * 100).toFixed(0)}%
                  </Badge>
                ))}
              </div>
            </div>

            {/* Reason */}
            <div>
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Reason</span>
              <p className="text-sm mt-1">{result.reason}</p>
            </div>

            {result.fail_reason && (
              <div>
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Fail Reason</span>
                <p className="mt-1">
                  <Badge variant="destructive">{result.fail_reason.replace(/_/g, ' ')}</Badge>
                </p>
              </div>
            )}

            {/* Parsed Identity */}
            <div>
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Parsed Identity</span>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {pi.producer && <Badge variant="muted">Producer: {pi.producer}</Badge>}
                {pi.appellation && <Badge variant="muted">Appellation: {pi.appellation}</Badge>}
                {pi.vineyard_or_cuvee && <Badge variant="muted">Vineyard: {pi.vineyard_or_cuvee}</Badge>}
                {pi.classification && <Badge variant="muted">Class: {pi.classification}</Badge>}
                {pi.vintage && <Badge variant="muted">Vintage: {pi.vintage}</Badge>}
              </div>
            </div>

            {/* Source */}
            {result.selected_source_page && (
              <div>
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Source</span>
                <p className="mt-1">
                  <a
                    href={result.selected_source_page}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-primary hover:underline inline-flex items-center gap-1"
                  >
                    {new URL(result.selected_source_page).hostname}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </p>
              </div>
            )}

            {/* Field Matches */}
            <div>
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Field Verification</span>
              <div className="mt-2">
                <FieldMatchesTable fieldMatches={result.field_matches} />
              </div>
            </div>
          </div>
        </div>

        {/* Debug Toggle */}
        <div className="mt-4 pt-4 border-t border-border">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDebug(!showDebug)}
            className="text-muted-foreground"
          >
            {showDebug ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            Debug Info ({result.debug.candidates_considered} candidates, {result.debug.queries.length} queries)
          </Button>

          {showDebug && (
            <div className="mt-3 space-y-3 text-xs">
              {/* Queries */}
              <div>
                <p className="font-medium text-muted-foreground uppercase tracking-wider mb-1">Queries</p>
                <div className="flex flex-wrap gap-1">
                  {result.debug.queries.map((q, i) => (
                    <span key={i} className="bg-muted px-2 py-1 rounded font-mono">{q}</span>
                  ))}
                </div>
              </div>

              {/* Score Breakdown */}
              <div>
                <p className="font-medium text-muted-foreground uppercase tracking-wider mb-1">Score Breakdown</p>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {Object.entries(result.debug.score_breakdown).map(([k, v]) => (
                    <div key={k} className="bg-muted px-2 py-1.5 rounded">
                      <span className="text-muted-foreground">{k.replace(/_/g, ' ')}</span>
                      <span className="block font-mono font-medium">{(v * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* OCR Snippets */}
              {result.debug.ocr_snippets.length > 0 && (
                <div>
                  <p className="font-medium text-muted-foreground uppercase tracking-wider mb-1">OCR Snippets</p>
                  {result.debug.ocr_snippets.map((s, i) => (
                    <pre key={i} className="bg-muted p-2 rounded font-mono whitespace-pre-wrap break-words mt-1">
                      {s.slice(0, 300)}{s.length > 300 ? '...' : ''}
                    </pre>
                  ))}
                </div>
              )}

              {/* Candidate Summaries */}
              {result.debug.candidate_summaries.length > 0 && (
                <div>
                  <p className="font-medium text-muted-foreground uppercase tracking-wider mb-1">Candidates</p>
                  <div className="space-y-1">
                    {result.debug.candidate_summaries.map((c) => (
                      <div key={c.candidate_id} className="bg-muted px-2 py-1.5 rounded space-y-2">
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="font-mono">{c.source_domain}</span>
                          <span className="font-mono">{(c.confidence * 100).toFixed(0)}%</span>
                          {c.should_fail ? (
                            <Badge variant="destructive">{(c.fail_reason ?? 'failed').replace(/_/g, ' ')}</Badge>
                          ) : (
                            <Badge variant="success">survived</Badge>
                          )}
                          <a
                            href={c.image_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline inline-flex items-center gap-1"
                          >
                            image
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        </div>
                        {c.module_votes && c.module_votes.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {c.module_votes.map((vote) => (
                              <Badge
                                key={`${c.candidate_id}-${vote.module}`}
                                variant={vote.passed ? 'success' : 'muted'}
                              >
                                {vote.module}: {(vote.confidence * 100).toFixed(0)}%
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Hard Fail Reasons */}
              {result.debug.hard_fail_reasons.length > 0 && (
                <div>
                  <p className="font-medium text-muted-foreground uppercase tracking-wider mb-1">Hard Fail Reasons</p>
                  <div className="flex flex-wrap gap-1">
                    {result.debug.hard_fail_reasons.map((r, i) => (
                      <Badge key={i} variant="destructive">{r.replace(/_/g, ' ')}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
