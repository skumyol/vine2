import type {
  AnalyzeRequest,
  AnalyzeResponse,
  BatchAnalyzeResponse,
  PipelineName,
} from '@/types'

const BASE = '/vine2'  // Matches host nginx location /vine2/

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}

export async function checkHealth(): Promise<{ status: string }> {
  return request('/api/health')  // Maps to /vine/api/health via BASE prefix
}

export async function analyzeSku(payload: AnalyzeRequest): Promise<AnalyzeResponse> {
  return request('/api/analyze', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function analyzeBatch(items: AnalyzeRequest[]): Promise<BatchAnalyzeResponse> {
  return request('/api/analyze/batch', {
    method: 'POST',
    body: JSON.stringify({ items }),
  })
}

export async function analyzeSkuWithPipeline(
  payload: AnalyzeRequest,
  pipeline: PipelineName,
): Promise<AnalyzeResponse> {
  return request(`/api/analyze?pipeline=${encodeURIComponent(pipeline)}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function analyzeBatchWithPipeline(
  items: AnalyzeRequest[],
  pipeline: PipelineName,
): Promise<BatchAnalyzeResponse> {
  return request(`/api/analyze/batch?pipeline=${encodeURIComponent(pipeline)}`, {
    method: 'POST',
    body: JSON.stringify({ items }),
  })
}
