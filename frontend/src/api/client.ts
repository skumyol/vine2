import type {
  AnalyzeRequest,
  AnalyzeResponse,
  BatchAnalyzeResponse,
  PipelineName,
} from '@/types'

const BASE = window.location.pathname.startsWith('/vine2') ? '/vine2' : ''  // '' for local dev, '/vine2' for production

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`
  console.log('API request:', url, options?.method || 'GET')
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  console.log('API response:', url, res.status)
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    console.error('API error:', url, res.status, text)
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
