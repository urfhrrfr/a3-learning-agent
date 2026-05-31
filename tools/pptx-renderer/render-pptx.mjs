import fs from 'node:fs/promises'
import path from 'node:path'
import pptxgen from 'pptxgenjs'

const COLORS = {
  ink: '13212D',
  muted: '5B6B7A',
  teal: '176C7A',
  tealDark: '0D5C68',
  gold: 'D69B2D',
  paper: 'F8FBFD',
  soft: 'E8F6EF',
  line: 'CFE2E8',
  white: 'FFFFFF',
  slate: '304557'
}

const LAYOUTS = new Set(['cover', 'agenda', 'concept', 'flow', 'compare', 'case', 'quiz', 'code', 'summary'])
const PAGE = { w: 13.333, h: 7.5 }
const MARGIN = 0.55

function parseArgs(argv) {
  const args = {}
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i]
    if (key.startsWith('--')) {
      args[key.slice(2)] = argv[i + 1]
      i += 1
    }
  }
  return args
}

async function readStdin() {
  const chunks = []
  for await (const chunk of process.stdin) chunks.push(chunk)
  return Buffer.concat(chunks).toString('utf8')
}

function cleanText(value, max = 220) {
  const text = String(value ?? '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/[ \t\r\f\v]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
  return text.length > max ? `${text.slice(0, max - 1)}...` : text
}

function cleanLines(values, maxItems = 5, maxLen = 84) {
  const source = Array.isArray(values) ? values : String(values ?? '').split(/[;；、\n]/)
  return source.map(item => cleanText(item, maxLen)).filter(Boolean).slice(0, maxItems)
}

function normalizeSlide(raw, index, deckTitle) {
  const layout = LAYOUTS.has(raw?.layout) ? raw.layout : index === 0 ? 'cover' : 'concept'
  const title = cleanText(raw?.title || (index === 0 ? deckTitle : `Slide ${index + 1}`), 72)
  const bullets = cleanLines(raw?.bullets || raw?.body || raw?.content, layout === 'cover' ? 3 : 5)
  return {
    title,
    subtitle: cleanText(raw?.subtitle || '', 120),
    layout,
    bullets: bullets.length ? bullets : ['Key idea', 'Example', 'Class activity'],
    speaker_note: cleanText(raw?.speaker_note || raw?.speakerNote || '', 180),
    visual_type: cleanText(raw?.visual_type || raw?.visualType || '', 32),
    accent: cleanText(raw?.accent || '', 36)
  }
}

function addShape(slide, type, options) {
  slide.addShape(type, options)
}

function addDeckChrome(pptx, slide, slideNo, section = 'TEACHING DECK') {
  slide.background = { color: COLORS.paper }
  addShape(slide, pptx.ShapeType.rect, { x: 0, y: 0, w: 0.12, h: PAGE.h, fill: { color: COLORS.teal }, line: { color: COLORS.teal } })
  slide.addText(section, {
    x: MARGIN,
    y: 0.22,
    w: 4.2,
    h: 0.22,
    fontFace: 'Arial',
    fontSize: 7,
    bold: true,
    color: COLORS.tealDark,
    margin: 0
  })
  slide.addText(String(slideNo).padStart(2, '0'), {
    x: 12.2,
    y: 6.92,
    w: 0.55,
    h: 0.24,
    fontSize: 8,
    bold: true,
    color: COLORS.muted,
    align: 'right',
    margin: 0
  })
}

function addTitle(slide, title, subtitle = '') {
  slide.addText(title, {
    x: MARGIN,
    y: 0.55,
    w: 8.7,
    h: 0.72,
    fontFace: 'Microsoft YaHei',
    fontSize: title.length > 24 ? 24 : 29,
    bold: true,
    color: COLORS.ink,
    margin: 0,
    fit: 'shrink'
  })
  if (subtitle) {
    slide.addText(subtitle, {
      x: MARGIN,
      y: 1.25,
      w: 8.6,
      h: 0.38,
      fontSize: 10.5,
      color: COLORS.muted,
      margin: 0,
      fit: 'shrink'
    })
  }
}

function addSpeakerNote(slide, text) {
  if (!text) return
  addShape(slide, 'rect', { x: 0.78, y: 6.25, w: 11.55, h: 0.44, fill: { color: 'FFF7E8' }, line: { color: 'F0D9A7', transparency: 100 } })
  addShape(slide, 'rect', { x: 0.78, y: 6.25, w: 0.03, h: 0.44, fill: { color: COLORS.gold }, line: { color: COLORS.gold } })
  slide.addText(text, { x: 0.94, y: 6.32, w: 11.0, h: 0.22, fontSize: 8.5, color: '714B08', margin: 0, fit: 'shrink' })
}

function addBullets(slide, bullets, x, y, w, gap = 0.56) {
  bullets.slice(0, 5).forEach((item, idx) => {
    const top = y + idx * gap
    addShape(slide, 'ellipse', { x, y: top + 0.06, w: 0.16, h: 0.16, fill: { color: idx % 2 ? COLORS.gold : COLORS.teal }, line: { color: idx % 2 ? COLORS.gold : COLORS.teal } })
    slide.addText(item, { x: x + 0.28, y: top, w, h: 0.38, fontSize: 13, color: COLORS.slate, margin: 0, fit: 'shrink' })
  })
}

function renderCover(_pptx, slide, spec, _idx, deckTitle) {
  slide.background = { color: 'F4FAFB' }
  addShape(slide, 'rect', { x: 0, y: 0, w: PAGE.w, h: PAGE.h, fill: { color: 'F4FAFB' }, line: { color: 'F4FAFB' } })
  addShape(slide, 'rect', { x: 0, y: 0, w: 4.2, h: PAGE.h, fill: { color: COLORS.teal }, line: { color: COLORS.teal } })
  addShape(slide, 'ellipse', { x: 9.0, y: -1.55, w: 4.9, h: 4.9, fill: { color: 'E4F2F5', transparency: 35 }, line: { color: 'B8DCE2', transparency: 60 } })
  addShape(slide, 'ellipse', { x: 9.65, y: 3.7, w: 2.35, h: 2.35, fill: { color: 'FFF3D5', transparency: 15 }, line: { color: COLORS.gold, transparency: 45 } })
  slide.addText('PERSONAL LEARNING STUDIO', { x: 0.6, y: 0.62, w: 2.95, h: 0.26, fontSize: 8, bold: true, color: COLORS.white, margin: 0 })
  slide.addText(spec.title || deckTitle, { x: 0.6, y: 1.62, w: 7.4, h: 1.45, fontSize: 33, bold: true, color: COLORS.ink, margin: 0, fit: 'shrink' })
  slide.addText(spec.subtitle || 'Teaching deck draft', { x: 0.66, y: 3.1, w: 6.3, h: 0.45, fontSize: 14, color: COLORS.slate, margin: 0, fit: 'shrink' })
  addShape(slide, 'rect', { x: 0.66, y: 4.05, w: 5.7, h: 0.04, fill: { color: COLORS.gold }, line: { color: COLORS.gold } })
  addBullets(slide, spec.bullets, 0.7, 4.45, 6.8, 0.46)
  slide.addText('A3', { x: 10.95, y: 6.55, w: 0.6, h: 0.26, fontSize: 8, bold: true, color: COLORS.tealDark, margin: 0 })
}

function renderAgenda(pptx, slide, spec, idx) {
  addDeckChrome(pptx, slide, idx, 'LEARNING PATH')
  addTitle(slide, spec.title, spec.subtitle || 'Learning route')
  spec.bullets.slice(0, 5).forEach((item, i) => {
    const y = 1.95 + i * 0.78
    addShape(slide, 'roundRect', { x: 0.9, y, w: 0.52, h: 0.52, fill: { color: i === 0 ? COLORS.teal : 'EAF3F5' }, line: { color: i === 0 ? COLORS.teal : COLORS.line } })
    slide.addText(String(i + 1), { x: 0.9, y: y + 0.14, w: 0.52, h: 0.18, fontSize: 11, bold: true, color: i === 0 ? COLORS.white : COLORS.tealDark, align: 'center', margin: 0 })
    slide.addText(item, { x: 1.7, y: y + 0.1, w: 8.6, h: 0.28, fontSize: 14.5, bold: true, color: COLORS.ink, margin: 0, fit: 'shrink' })
  })
  addSpeakerNote(slide, spec.speaker_note)
}

function renderConcept(pptx, slide, spec, idx) {
  addDeckChrome(pptx, slide, idx, 'CONCEPT')
  addTitle(slide, spec.title, spec.subtitle)
  addShape(slide, 'roundRect', { x: 0.78, y: 1.78, w: 5.8, h: 3.8, fill: { color: COLORS.white }, line: { color: COLORS.line } })
  slide.addText(spec.bullets[0], { x: 1.08, y: 2.05, w: 5.1, h: 0.76, fontSize: 21, bold: true, color: COLORS.tealDark, margin: 0, fit: 'shrink' })
  addBullets(slide, spec.bullets.slice(1), 1.08, 3.15, 4.95, 0.52)
  addShape(slide, 'rect', { x: 7.05, y: 1.82, w: 4.65, h: 3.7, fill: { color: COLORS.soft }, line: { color: COLORS.soft } })
  addShape(slide, 'chevron', { x: 8.42, y: 2.55, w: 1.65, h: 1.15, fill: { color: COLORS.teal }, line: { color: COLORS.teal } })
  slide.addText(spec.accent || 'Key boundary', { x: 7.55, y: 4.05, w: 3.65, h: 0.46, fontSize: 19, bold: true, align: 'center', color: COLORS.ink, margin: 0, fit: 'shrink' })
  addSpeakerNote(slide, spec.speaker_note)
}

function renderFlow(pptx, slide, spec, idx) {
  addDeckChrome(pptx, slide, idx, 'FLOW')
  addTitle(slide, spec.title, spec.subtitle)
  const steps = spec.bullets.slice(0, 5)
  steps.forEach((item, i) => {
    const x = 0.85 + i * 2.28
    addShape(slide, 'roundRect', { x, y: 2.35, w: 1.72, h: 1.06, fill: { color: i % 2 ? 'FFF7E8' : COLORS.soft }, line: { color: i % 2 ? 'F0D9A7' : COLORS.line } })
    slide.addText(item, { x: x + 0.16, y: 2.62, w: 1.4, h: 0.38, fontSize: 12.2, bold: true, align: 'center', color: COLORS.ink, margin: 0, fit: 'shrink' })
    if (i < steps.length - 1) {
      addShape(slide, 'rightArrow', { x: x + 1.78, y: 2.7, w: 0.42, h: 0.34, fill: { color: COLORS.teal }, line: { color: COLORS.teal } })
    }
  })
  slide.addText(spec.accent || 'From input to feedback loop', { x: 1.0, y: 4.35, w: 9.8, h: 0.4, fontSize: 18, bold: true, color: COLORS.tealDark, margin: 0, fit: 'shrink' })
  addSpeakerNote(slide, spec.speaker_note)
}

function renderCompare(pptx, slide, spec, idx) {
  addDeckChrome(pptx, slide, idx, 'COMPARE')
  addTitle(slide, spec.title, spec.subtitle)
  const left = spec.bullets.slice(0, Math.ceil(spec.bullets.length / 2))
  const right = spec.bullets.slice(Math.ceil(spec.bullets.length / 2))
  addShape(slide, 'roundRect', { x: 0.82, y: 1.92, w: 5.05, h: 3.7, fill: { color: COLORS.white }, line: { color: COLORS.line } })
  addShape(slide, 'roundRect', { x: 6.2, y: 1.92, w: 5.05, h: 3.7, fill: { color: 'FFF9ED' }, line: { color: 'F0D9A7' } })
  slide.addText(spec.accent || 'Common confusion', { x: 1.12, y: 2.2, w: 2.5, h: 0.26, fontSize: 13, bold: true, color: COLORS.tealDark, margin: 0, fit: 'shrink' })
  slide.addText('Better framing', { x: 6.5, y: 2.2, w: 2.0, h: 0.26, fontSize: 13, bold: true, color: '714B08', margin: 0 })
  addBullets(slide, left, 1.12, 2.72, 3.9, 0.58)
  addBullets(slide, right.length ? right : left, 6.5, 2.72, 3.9, 0.58)
  addSpeakerNote(slide, spec.speaker_note)
}

function renderCase(pptx, slide, spec, idx) {
  addDeckChrome(pptx, slide, idx, 'CASE')
  addTitle(slide, spec.title, spec.subtitle)
  addShape(slide, 'rect', { x: 0.85, y: 1.85, w: 3.2, h: 3.7, fill: { color: COLORS.teal }, line: { color: COLORS.teal } })
  slide.addText(spec.accent || 'Real scenario', { x: 1.15, y: 2.32, w: 2.5, h: 0.56, fontSize: 23, bold: true, color: COLORS.white, align: 'center', margin: 0, fit: 'shrink' })
  slide.addText('Turn an abstract idea into a classroom decision.', { x: 1.18, y: 3.35, w: 2.45, h: 0.66, fontSize: 12.2, color: 'E9FAF7', align: 'center', margin: 0, fit: 'shrink' })
  addBullets(slide, spec.bullets, 4.55, 2.0, 6.45, 0.58)
  addSpeakerNote(slide, spec.speaker_note)
}

function renderQuiz(pptx, slide, spec, idx) {
  addDeckChrome(pptx, slide, idx, 'CHECK')
  addTitle(slide, spec.title, spec.subtitle || 'Check understanding')
  addShape(slide, 'roundRect', { x: 0.95, y: 1.95, w: 9.65, h: 1.08, fill: { color: COLORS.white }, line: { color: COLORS.line } })
  slide.addText(spec.bullets[0], { x: 1.25, y: 2.24, w: 9.0, h: 0.36, fontSize: 17, bold: true, color: COLORS.ink, margin: 0, fit: 'shrink' })
  addBullets(slide, spec.bullets.slice(1), 1.25, 3.58, 8.4, 0.55)
  slide.addText(spec.accent || 'Judge first, then reveal.', { x: 1.25, y: 5.3, w: 8.2, h: 0.32, fontSize: 15, bold: true, color: COLORS.gold, margin: 0, fit: 'shrink' })
  addSpeakerNote(slide, spec.speaker_note)
}

function renderCode(pptx, slide, spec, idx) {
  addDeckChrome(pptx, slide, idx, 'CODE')
  addTitle(slide, spec.title, spec.subtitle)
  addShape(slide, 'rect', { x: 0.88, y: 1.9, w: 5.4, h: 3.55, fill: { color: '101827' }, line: { color: '101827' } })
  slide.addText(spec.bullets.slice(0, 4).map((item, i) => `${i + 1}. ${item}`).join('\n'), { x: 1.15, y: 2.25, w: 4.85, h: 2.75, fontFace: 'Consolas', fontSize: 12, color: 'E6EDF3', margin: 0.02, fit: 'shrink' })
  slide.addText(spec.accent || 'Minimal runnable lab', { x: 6.8, y: 2.4, w: 3.8, h: 0.54, fontSize: 21, bold: true, color: COLORS.tealDark, margin: 0, fit: 'shrink' })
  addBullets(slide, spec.bullets.slice(4), 6.85, 3.35, 4.2, 0.55)
  addSpeakerNote(slide, spec.speaker_note)
}

function renderSummary(pptx, slide, spec, idx) {
  addDeckChrome(pptx, slide, idx, 'SUMMARY')
  addTitle(slide, spec.title, spec.subtitle || 'Takeaways')
  spec.bullets.slice(0, 4).forEach((item, i) => {
    const x = 0.86 + (i % 2) * 5.45
    const y = 2.0 + Math.floor(i / 2) * 1.42
    addShape(slide, 'roundRect', { x, y, w: 4.85, h: 1.0, fill: { color: i % 2 ? 'FFF7E8' : COLORS.white }, line: { color: i % 2 ? 'F0D9A7' : COLORS.line } })
    slide.addText(item, { x: x + 0.25, y: y + 0.28, w: 4.35, h: 0.3, fontSize: 14, bold: true, color: COLORS.ink, margin: 0, fit: 'shrink' })
  })
  addSpeakerNote(slide, spec.speaker_note)
}

const renderers = {
  cover: renderCover,
  agenda: renderAgenda,
  concept: renderConcept,
  flow: renderFlow,
  compare: renderCompare,
  case: renderCase,
  quiz: renderQuiz,
  code: renderCode,
  summary: renderSummary
}

async function main() {
  const args = parseArgs(process.argv)
  if (!args.output) {
    throw new Error('Missing --output <pptx path>')
  }
  const payload = JSON.parse(await readStdin())
  const deckTitle = cleanText(payload.title || 'Teaching Deck', 80)
  const rawSlides = Array.isArray(payload.slides) ? payload.slides : []
  const slides = rawSlides.map((slide, idx) => normalizeSlide(slide, idx, deckTitle))
  if (!slides.length) {
    slides.push(normalizeSlide({ layout: 'cover', title: deckTitle }, 0, deckTitle))
  }

  await fs.mkdir(path.dirname(args.output), { recursive: true })
  const pptx = new pptxgen()
  pptx.defineLayout({ name: 'LAYOUT_WIDE', width: PAGE.w, height: PAGE.h })
  pptx.layout = 'LAYOUT_WIDE'
  pptx.author = 'A3 PPT Agent'
  pptx.company = 'Personal Learning Studio'
  pptx.subject = deckTitle
  pptx.title = deckTitle
  pptx.lang = 'zh-CN'
  pptx.theme = {
    headFontFace: 'Microsoft YaHei',
    bodyFontFace: 'Microsoft YaHei',
    lang: 'zh-CN'
  }

  slides.forEach((spec, idx) => {
    const slide = pptx.addSlide()
    const renderer = renderers[spec.layout] || renderConcept
    renderer(pptx, slide, spec, idx + 1, deckTitle)
  })

  await pptx.writeFile({ fileName: args.output })
  process.stdout.write(JSON.stringify({ ok: true, output: args.output, slide_count: slides.length }))
}

main().catch(error => {
  process.stderr.write(`${error.stack || error.message}\n`)
  process.exit(1)
})
