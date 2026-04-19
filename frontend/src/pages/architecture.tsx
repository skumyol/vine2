import { Card, CardContent, CardHeader } from '@/components/ui/card'

const assignmentQuestions = [
  {
    title: 'How do you confirm the label text matches exactly?',
    body:
      'The system parses target identity into producer, appellation, vineyard or cuvee, classification, and vintage. OCR and VLM votes are compared against those fields independently. Producer and appellation are treated as hard identity fields, while vineyard, cru, and vintage can upgrade or veto the decision depending on evidence strength.',
  },
  {
    title: 'How do you automatically filter low quality, watermarked, or lifestyle images?',
    body:
      'OpenCV-based prefilters and image quality heuristics reject obvious non-product images. The pipeline checks bottle visibility, label visibility, blur, glare, clutter, and watermark-like overlays before allowing a candidate to survive to verification.',
  },
  {
    title: 'What is your confidence scoring mechanism?',
    body:
      'Each module emits its own confidence. The voter pipeline aggregates OCR, VLM, OCR+VLM joint evidence, and source trust with explicit weights. The final response records both module-level confidence and the aggregated final confidence for the selected verdict.',
  },
  {
    title: 'What is your fallback when no verified photo can be found?',
    body:
      'The system returns No Image rather than taking a weak match. That preserves precision and makes the failure mode explicit for downstream users. Fail reasons are captured in the response so the operator can see whether quality, identity, or retrieval coverage caused the miss.',
  },
  {
    title: 'How do you handle wines with near-zero online photo coverage?',
    body:
      'The retrieval layer supports multiple sources and can fall back from SerpAPI to Playwright scraping when credits or coverage are limited. If evidence is still insufficient, the conservative answer remains No Image with low confidence instead of a guessed bottle shot.',
  },
]

const pipelines = [
  {
    title: 'Voter Pipeline',
    steps: [
      'retrieval from Playwright or SerpAPI',
      'OCR extraction with multi-pass Tesseract and optional EasyOCR',
      'field matcher and hard fail rules',
      'OpenRouter VLM vote',
      'weighted voting across OCR, VLM, OCR+VLM, and source trust',
    ],
  },
  {
    title: 'Paddle + Qwen Pipeline',
    steps: [
      'retrieval from Playwright or SerpAPI',
      'OpenCV quality gate and label cropper',
      'PaddleOCR extraction for structured text evidence',
      'ambiguity gate to decide whether VLM is needed',
      'OpenRouter-hosted Qwen multimodal verification for ambiguous survivors',
    ],
  },
]

export function ArchitecturePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Assignment Coverage And Pipeline Architecture</h1>
        <p className="text-muted-foreground text-sm mt-1">
          This page explains how the demo answers the assignment questions and what each backend pipeline is doing.
        </p>
      </div>

      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold">Assignment Questions Addressed</h2>
        </CardHeader>
        <CardContent className="space-y-4">
          {assignmentQuestions.map((item) => (
            <div key={item.title} className="rounded-lg border border-border p-4">
              <h3 className="font-medium">{item.title}</h3>
              <p className="text-sm text-muted-foreground mt-2">{item.body}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold">Pipeline Variants</h2>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          {pipelines.map((pipeline) => (
            <div key={pipeline.title} className="rounded-lg border border-border p-4">
              <h3 className="font-medium">{pipeline.title}</h3>
              <ul className="mt-3 space-y-2 text-sm text-muted-foreground list-disc pl-5">
                {pipeline.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold">Frontend Demo Modes</h2>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            Single job mode accepts a manual wine request and lets the user pick the pipeline before running a live backend call.
          </p>
          <p>
            Batch job mode runs the full 10-SKU assignment set and returns the photo URL, confidence score, and pass or fail verdict for each SKU.
          </p>
          <p>
            Both modes surface per-module confidence so the demo shows why a result passed, failed, or ended in No Image.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
