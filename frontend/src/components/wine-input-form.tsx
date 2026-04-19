import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import type { AnalyzeRequest, AnalyzerMode, PipelineName } from '@/types'
import { Search } from 'lucide-react'

interface Props {
  onSubmit: (req: AnalyzeRequest, pipeline: PipelineName) => void
  isLoading: boolean
}

export function WineInputForm({ onSubmit, isLoading }: Props) {
  const [wineName, setWineName] = useState('')
  const [vintage, setVintage] = useState('')
  const [format, setFormat] = useState('750ml')
  const [region, setRegion] = useState('')
  const [mode, setMode] = useState<AnalyzerMode>('strict')
  const [pipeline, setPipeline] = useState<PipelineName>('voter')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!wineName.trim() || !vintage.trim()) return
    onSubmit(
      {
        wine_name: wineName.trim(),
        vintage: vintage.trim(),
        format,
        region: region.trim(),
        analyzer_mode: mode,
      },
      pipeline,
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="md:col-span-2">
          <Input
            id="wine-name"
            label="Wine Name"
            placeholder="e.g. Domaine Arlaud Morey-St-Denis 'Monts Luisants' 1er Cru"
            value={wineName}
            onChange={(e) => setWineName(e.target.value)}
            required
          />
        </div>
        <Input
          id="vintage"
          label="Vintage"
          placeholder="e.g. 2019 or NV"
          value={vintage}
          onChange={(e) => setVintage(e.target.value)}
          required
        />
        <Input
          id="region"
          label="Region"
          placeholder="e.g. Burgundy"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
        />
        <Select
          id="format"
          label="Format"
          value={format}
          onChange={(e) => setFormat(e.target.value)}
          options={[
            { value: '750ml', label: '750ml' },
            { value: '375ml', label: '375ml' },
            { value: '1500ml', label: '1500ml (Magnum)' },
          ]}
        />
        <Select
          id="mode"
          label="Analyzer Mode"
          value={mode}
          onChange={(e) => setMode(e.target.value as AnalyzerMode)}
          options={[
            { value: 'strict', label: 'Strict' },
            { value: 'balanced', label: 'Balanced' },
          ]}
        />
        <Select
          id="pipeline"
          label="Pipeline"
          value={pipeline}
          onChange={(e) => setPipeline(e.target.value as PipelineName)}
          options={[
            { value: 'voter', label: 'Voter: OCR + VLM + source voting' },
            { value: 'paddle_qwen', label: 'Paddle + Qwen gated verifier' },
          ]}
        />
      </div>
      <Button type="submit" disabled={isLoading || !wineName.trim() || !vintage.trim()} className="w-full md:w-auto">
        {isLoading ? (
          <>
            <Spinner className="h-4 w-4" />
            Analyzing...
          </>
        ) : (
          <>
            <Search className="h-4 w-4" />
            Analyze Wine
          </>
        )}
      </Button>
    </form>
  )
}
