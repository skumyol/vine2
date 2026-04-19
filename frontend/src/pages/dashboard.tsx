import { useState, useCallback } from 'react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { WineInputForm } from '@/components/wine-input-form'
import { ResultDetail } from '@/components/result-detail'
import { ResultsTable } from '@/components/results-table'
import { BatchSummary } from '@/components/batch-summary'
import { analyzeSkuWithPipeline, analyzeBatchWithPipeline } from '@/api/client'
import { TEST_SKUS } from '@/data/test-skus'
import type { AnalyzeRequest, AnalyzeResponse, PipelineName } from '@/types'
import { FlaskConical, ListChecks, Download } from 'lucide-react'

export function Dashboard() {
  const [results, setResults] = useState<AnalyzeResponse[]>([])
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [batchLoading, setBatchLoading] = useState(false)
  const [batchProgress, setBatchProgress] = useState({ done: 0, total: 0 })
  const [error, setError] = useState<string | null>(null)
  const [singlePipeline, setSinglePipeline] = useState<PipelineName>('voter')
  const [batchPipeline, setBatchPipeline] = useState<PipelineName>('voter')

  const handleSingle = useCallback(async (req: AnalyzeRequest, pipeline: PipelineName) => {
    setLoading(true)
    setError(null)
    setSinglePipeline(pipeline)
    try {
      const res = await analyzeSkuWithPipeline(req, pipeline)
      setResults((prev) => [res, ...prev])
      setSelectedIdx(0)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleBatch = useCallback(async () => {
    setBatchLoading(true)
    setError(null)
    setBatchProgress({ done: 0, total: TEST_SKUS.length })
    try {
      const items: AnalyzeRequest[] = TEST_SKUS.map((s) => ({
        wine_name: s.wine_name,
        vintage: s.vintage,
        format: s.format,
        region: s.region,
        analyzer_mode: 'strict' as const,
      }))
      const res = await analyzeBatchWithPipeline(items, batchPipeline)
      setResults(res.results)
      setBatchProgress({ done: res.results.length, total: TEST_SKUS.length })
      setSelectedIdx(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Batch analysis failed')
    } finally {
      setBatchLoading(false)
    }
  }, [batchPipeline])

  const handleExportJson = useCallback(() => {
    if (results.length === 0) return
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `vinobuzz-results-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }, [results])

  const handleExportCsv = useCallback(() => {
    if (results.length === 0) return
    const header = 'Wine Name,Vintage,Region,Verdict,Confidence,Image URL,Reason\n'
    const rows = results
      .map(
        (r) =>
          `"${r.input.wine_name}","${r.input.vintage}","${r.input.region}","${r.verdict}","${Math.round(r.confidence * 100)}%","${r.selected_image_url ?? ''}","${r.reason.replace(/"/g, '""')}"`,
      )
      .join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `vinobuzz-results-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }, [results])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Wine Photo Pipeline</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Real frontend demo for single-SKU analysis and full 10-SKU batch assignment runs
        </p>
      </div>

      {/* Single Analysis */}
      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold flex items-center gap-2">
            <FlaskConical className="h-4 w-4 text-primary" />
            Analyze Single Wine
          </h2>
        </CardHeader>
        <CardContent>
          <WineInputForm onSubmit={handleSingle} isLoading={loading} />
        </CardContent>
      </Card>

      {/* Batch Test SKUs */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold flex items-center gap-2">
              <ListChecks className="h-4 w-4 text-primary" />
              Assignment Test SKUs
            </h2>
            <div className="flex items-end gap-2">
              <div className="w-64">
                <Select
                  id="batch-pipeline"
                  label="Batch Pipeline"
                  value={batchPipeline}
                  onChange={(e) => setBatchPipeline(e.target.value as PipelineName)}
                  options={[
                    { value: 'voter', label: 'Voter: OCR + VLM + source voting' },
                    { value: 'paddle_qwen', label: 'Paddle + Qwen gated verifier' },
                  ]}
                />
              </div>
              <Button
                onClick={handleBatch}
                disabled={batchLoading}
                variant="outline"
                size="sm"
              >
                {batchLoading ? (
                  <>
                    <Spinner className="h-3.5 w-3.5" />
                    Running {batchProgress.done}/{batchProgress.total}...
                  </>
                ) : (
                  <>Run All 10 Test SKUs</>
                )}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="py-2 pr-3 font-medium text-muted-foreground w-8">#</th>
                  <th className="py-2 pr-3 font-medium text-muted-foreground">Wine Name</th>
                  <th className="py-2 pr-3 font-medium text-muted-foreground w-20">Vintage</th>
                  <th className="py-2 pr-3 font-medium text-muted-foreground w-28">Region</th>
                  <th className="py-2 font-medium text-muted-foreground w-24">Difficulty</th>
                </tr>
              </thead>
              <tbody>
                {TEST_SKUS.map((s, i) => (
                  <tr key={i} className="border-b border-border/50 last:border-0">
                    <td className="py-2 pr-3 text-muted-foreground font-mono text-xs">{i + 1}</td>
                    <td className="py-2 pr-3">{s.wine_name}</td>
                    <td className="py-2 pr-3 text-muted-foreground">{s.vintage}</td>
                    <td className="py-2 pr-3 text-muted-foreground">{s.region}</td>
                    <td className="py-2">
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                          s.difficulty === 'Very Hard'
                            ? 'bg-red-100 text-red-700'
                            : s.difficulty === 'Hard'
                              ? 'bg-amber-100 text-amber-700'
                              : 'bg-blue-100 text-blue-700'
                        }`}
                      >
                        {s.difficulty}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <>
          {/* Summary */}
          <BatchSummary results={results} />

          {/* Export buttons */}
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={handleExportJson}>
              <Download className="h-3.5 w-3.5" />
              Export JSON
            </Button>
            <Button variant="outline" size="sm" onClick={handleExportCsv}>
              <Download className="h-3.5 w-3.5" />
              Export CSV
            </Button>
            <div className="flex items-center rounded-md border border-border px-3 text-xs text-muted-foreground">
              Active pipelines: single `{singlePipeline}`, batch `{batchPipeline}`
            </div>
          </div>

          {/* Results Table */}
          <Card>
            <CardHeader>
              <h2 className="text-base font-semibold">Results ({results.length})</h2>
            </CardHeader>
            <CardContent>
              <ResultsTable
                results={results}
                onSelect={setSelectedIdx}
                selectedIndex={selectedIdx}
              />
            </CardContent>
          </Card>

          {/* Selected Detail */}
          {selectedIdx !== null && results[selectedIdx] && (
            <ResultDetail result={results[selectedIdx]} index={selectedIdx} />
          )}
        </>
      )}
    </div>
  )
}
