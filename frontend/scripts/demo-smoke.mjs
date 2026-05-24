import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

const API_BASE = process.env.VITE_API_BASE || 'http://127.0.0.1:8000'
const userId = `frontend_demo_smoke_${Date.now()}`

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': userId,
      ...(options.headers || {})
    }
  })
  const body = await response.json()
  assert(response.ok, `${path} HTTP ${response.status}`)
  assert(body.ok === true, `${path} returned error envelope`)
  return body.data
}

async function readSseOnce(jobId) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 4000)
  try {
    const response = await fetch(`${API_BASE}/api/jobs/${jobId}/events`, {
      headers: { 'X-User-Id': userId },
      signal: controller.signal
    })
    assert(response.ok, 'SSE endpoint is not reachable')
    const reader = response.body?.getReader()
    assert(reader, 'SSE response has no readable stream')
    const chunk = await reader.read()
    const text = new TextDecoder('utf-8').decode(chunk.value || new Uint8Array())
    await reader.cancel()
    return text
  } catch (error) {
    if (error?.name === 'AbortError') return ''
    throw error
  } finally {
    clearTimeout(timeout)
  }
}

async function waitJob(jobId) {
  for (let i = 0; i < 50; i += 1) {
    const job = await api(`/api/jobs/${jobId}`)
    if (job.status === 'completed' || job.status === 'failed') return job
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  throw new Error(`job ${jobId} did not finish in time`)
}

function checkBuildArtifact() {
  const indexPath = join(process.cwd(), 'dist', 'index.html')
  assert(existsSync(indexPath), 'dist/index.html missing; run npm run build first')
  const assetDir = join(process.cwd(), 'dist', 'assets')
  assert(existsSync(assetDir), 'dist/assets missing; run npm run build first')
  const jsPayload = readdirSync(assetDir)
    .filter(name => name.endsWith('.js'))
    .map(name => readFileSync(join(assetDir, name), 'utf8'))
    .join('\n')
  assert(jsPayload.includes('127.0.0.1:8000') || process.env.VITE_API_BASE, 'built frontend does not contain a demo API base')
}

async function main() {
  checkBuildArtifact()

  const health = await api('/api/health')
  assert(health.status === 'healthy', 'backend health is not healthy')

  const profileUpdate = await api('/api/profile/chat', {
    method: 'POST',
    body: JSON.stringify({ message: '我想用图解和代码学习机器学习基础，过拟合和评估指标容易混淆。' })
  })
  assert(profileUpdate.profile?.version >= 2, 'profile update did not return a valid profile')

  const createdJob = await api('/api/resources/generate/background', {
    method: 'POST',
    body: JSON.stringify({
      course: '人工智能导论',
      chapter: '机器学习基础',
      goal: '前端完整演示 smoke 检查',
      pain_points: ['过拟合', '模型评估指标'],
      resource_types: ['lecture_doc', 'quiz', 'code_case']
    })
  })
  assert(createdJob.id, 'background generation did not return job id')

  const sseSample = await readSseOnce(createdJob.id)
  assert(!sseSample || sseSample.includes('event:'), 'SSE endpoint returned unexpected content')

  const finalJob = await waitJob(createdJob.id)
  assert(finalJob.status === 'completed', `generation job ended as ${finalJob.status}`)
  assert(finalJob.resources.length > 0, 'generation job returned no resources')
  assert(finalJob.traces.length >= 6, 'generation traces are incomplete')

  const resources = await api('/api/resources')
  assert(resources.length > 0, 'resource library is empty after generation')
  const resourceIds = new Set(resources.map(resource => resource.id))

  const path = await api('/api/learning-path/current')
  assert(path.steps.length > 0, 'learning path has no steps')
  const missingRefs = path.steps
    .flatMap(step => step.recommended_resource_ids || [])
    .filter(id => !resourceIds.has(id))
  assert(missingRefs.length === 0, `learning path references missing resources: ${missingRefs.join(', ')}`)

  const tutor = await api('/api/tutor/chat', {
    method: 'POST',
    body: JSON.stringify({ question: '过拟合为什么会让新数据表现变差？', history: [] })
  })
  assert(tutor.answer && tutor.next_step && tutor.exercise, 'tutor response is missing answer/next_step/exercise')

  const assessment = await api('/api/quiz/submit', {
    method: 'POST',
    body: JSON.stringify({
      answers: ['题目：为什么只看训练准确率可能误导？\n回答：过拟合会让训练集表现好，但泛化到新数据变差，需要看测试集和评估指标。']
    })
  })
  assert(typeof assessment.score === 'number', 'assessment score missing')
  assert(Array.isArray(assessment.weak_points), 'assessment weak_points missing')
  assert(Array.isArray(assessment.mistake_patterns), 'assessment mistake_patterns missing')
  assert(assessment.adjusted_path?.steps?.length > 0, 'assessment adjusted_path missing')

  const report = await api('/api/assessment/report')
  assert(report.id === assessment.id, 'assessment report did not reflect the latest quiz submission')

  console.log('demo-smoke passed', JSON.stringify({
    resources: resources.length,
    path_steps: path.steps.length,
    traces: finalJob.traces.length,
    score: assessment.score
  }))
}

main().catch(error => {
  console.error('demo-smoke failed:', error.message)
  process.exit(1)
})
