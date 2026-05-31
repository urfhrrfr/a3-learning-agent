from __future__ import annotations

import json
import re
from html import escape

from ..base import WorkflowState, parse_llm_json
from ...providers.base import BaseLLMProvider
from .base import ResourceAgent


class PPTDraftAgent(ResourceAgent):
    name = "PPTDraftAgent"
    resource_type = "html_ppt"
    content_format = "json"
    title_prefix = "HTML PPT 课件"
    stage = "producer"
    boundary = "生成可在前端 iframe 内直接预览的 HTML 幻灯片课件，不导出 pptx 文件"
    depends_on = ["PlannerAgent", "KnowledgeAgent"]

    allowed_layouts = {"cover", "agenda", "concept", "flow", "compare", "case", "quiz", "code", "summary"}

    def __init__(self, llm: BaseLLMProvider | None = None):
        super().__init__(llm)
        self.last_deck_spec: dict | None = None

    def _clean_text(self, value, max_len: int = 160) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        return text[: max_len - 1] + "…" if len(text) > max_len else text

    def _list_item(self, values: list, index: int, fallback: str) -> str:
        if not values:
            return fallback
        return str(values[min(index, len(values) - 1)])

    def _fallback_slide_specs(self, state: WorkflowState) -> list[dict]:
        concepts = state.chapter["concepts"]
        details = state.chapter["detailed_concepts"]
        cases = state.chapter["real_cases"]
        misconceptions = state.chapter["misconceptions"]
        labs = state.chapter["code_labs"]
        objectives = state.chapter["objectives"]
        title = state.chapter["title"]
        return [
            {
                "title": f"{title} 教学课件",
                "subtitle": "面向课堂讲解、案例演示与互动练习",
                "layout": "cover",
                "bullets": objectives[:3] or ["建立核心概念", "理解应用流程", "完成课堂练习"],
                "speaker_note": "用一个真实应用问题导入，说明本节课完成后学生能做什么。",
                "visual_type": "hero",
                "accent": title,
            },
            {
                "title": "学习路线",
                "subtitle": "从概念到实践的课堂节奏",
                "layout": "agenda",
                "bullets": ["问题导入", "核心概念", "流程拆解", "案例判断", "代码实验与复盘"],
                "speaker_note": "先给出路线，降低学生对抽象概念的陌生感。",
                "visual_type": "timeline",
                "accent": "课堂路径",
            },
            {
                "title": f"核心概念：{self._list_item(concepts, 0, '关键概念')}",
                "subtitle": self._list_item(details, 0, "概念定义、适用条件与边界"),
                "layout": "concept",
                "bullets": [self._list_item(details, 0, "解释定义"), "关注输入、输出和目标", "说明它解决的问题", "给出一个反例帮助区分"],
                "speaker_note": "先讲定义，再用反例澄清边界。",
                "visual_type": "concept_card",
                "accent": "抓住边界",
            },
            {
                "title": "从数据到反馈的流程",
                "subtitle": f"围绕 {self._list_item(concepts, 1, '模型训练')} 搭建完整链路",
                "layout": "flow",
                "bullets": ["明确任务", "准备数据", "选择方法", "训练与预测", "评估并修正"],
                "speaker_note": "强调流程不是线性的，评估结果会反过来推动修正。",
                "visual_type": "process",
                "accent": "形成学习闭环",
            },
            {
                "title": "容易混淆的判断",
                "subtitle": self._list_item(misconceptions, 0, "常见误区与正确理解"),
                "layout": "compare",
                "bullets": [
                    self._list_item(misconceptions, 0, "只看表面指标"),
                    self._list_item(misconceptions, 1, "忽略数据边界"),
                    "先确认任务目标",
                    "再检查评价证据",
                ],
                "speaker_note": "让学生先判断，再揭示纠正逻辑。",
                "visual_type": "two_column",
                "accent": "误区 vs 抓法",
            },
            {
                "title": "真实案例分析",
                "subtitle": "把抽象概念落到可判断的场景",
                "layout": "case",
                "bullets": [str(cases[0]), "识别任务目标和输入数据", "讨论失败时先排查哪里", "总结可迁移的判断标准"],
                "speaker_note": "用提问驱动案例，而不是直接给结论。",
                "visual_type": "case_panel",
                "accent": "真实场景",
            },
            {
                "title": "课堂快问快答",
                "subtitle": "确认是否真正理解关键边界",
                "layout": "quiz",
                "bullets": [
                    f"如果 {self._list_item(concepts, 2, '模型')} 在训练集很好、在新数据很差，优先怀疑什么？",
                    "A. 数据划分或过拟合",
                    "B. 代码行数太少",
                    "C. 概念一定错误",
                    "D. 不需要评估",
                ],
                "speaker_note": "先投票，再解释每个选项为什么成立或不成立。",
                "visual_type": "quiz",
                "accent": "先判断，再纠正",
            },
            {
                "title": "代码实验",
                "subtitle": "用最小实现验证概念",
                "layout": "code",
                "bullets": [
                    "加载数据并划分训练/测试集",
                    "选择一个简单模型",
                    "fit 后 predict",
                    "计算并解释准确率",
                    self._list_item(labs, 0, "观察不同参数对结果的影响"),
                ],
                "speaker_note": "鼓励学生跟着敲代码，观察参数变化带来的结果差异。",
                "visual_type": "code",
                "accent": "最小可运行实验",
            },
            {
                "title": "复盘与迁移任务",
                "subtitle": "把本节课变成可复述、可实践的能力",
                "layout": "summary",
                "bullets": [
                    f"用自己的话解释 {self._list_item(concepts, 0, '核心概念')}",
                    "画出任务流程图",
                    "找一个专业场景迁移应用",
                    "记录一个仍然不确定的问题",
                ],
                "speaker_note": "最后留出 3 分钟写下迁移场景和疑问。",
                "visual_type": "takeaway",
                "accent": "带走三个判断",
            },
        ]

    def _normalize_slide_specs(self, raw_slides, state: WorkflowState) -> list[dict]:
        if not isinstance(raw_slides, list):
            return self._fallback_slide_specs(state)
        normalized: list[dict] = []
        for index, raw in enumerate(raw_slides[:12]):
            if not isinstance(raw, dict):
                continue
            layout = str(raw.get("layout") or "").strip()
            if layout not in self.allowed_layouts:
                layout = "cover" if index == 0 else "concept"
            bullets_value = raw.get("bullets") or raw.get("body") or raw.get("content") or []
            if isinstance(bullets_value, str):
                bullets = [item.strip() for item in re.split(r"[；;、\n]", bullets_value) if item.strip()]
            elif isinstance(bullets_value, list):
                bullets = [self._clean_text(item, 90) for item in bullets_value if str(item).strip()]
            else:
                bullets = []
            fallback_title = f"第 {index + 1} 页"
            normalized.append(
                {
                    "title": self._clean_text(raw.get("title") or fallback_title, 72),
                    "subtitle": self._clean_text(raw.get("subtitle") or "", 120),
                    "layout": layout,
                    "bullets": bullets[:5] or ["关键概念", "课堂案例", "互动练习"],
                    "speaker_note": self._clean_text(raw.get("speaker_note") or raw.get("speakerNote") or "", 180),
                    "visual_type": self._clean_text(raw.get("visual_type") or raw.get("visualType") or "", 32),
                    "accent": self._clean_text(raw.get("accent") or "", 36),
                }
            )
        return normalized or self._fallback_slide_specs(state)

    def _deck_spec(self, state: WorkflowState, slides: list[dict] | None = None) -> dict:
        return {
            "title": f"{state.chapter['title']} 教学课件",
            "theme": "html-ppt-classroom",
            "slides": slides or self._fallback_slide_specs(state),
        }

    def _sanitize_html_document(self, html: str) -> str:
        html = str(html or "").strip()
        if not html:
            return ""
        html = re.sub(r"<\s*script[\s\S]*?<\s*/\s*script\s*>", "", html, flags=re.IGNORECASE)
        html = re.sub(r"\s+on[a-z]+\s*=\s*(['\"])[\s\S]*?\1", "", html, flags=re.IGNORECASE)
        html = re.sub(r"\s+on[a-z]+\s*=\s*[^\s>]+", "", html, flags=re.IGNORECASE)
        html = re.sub(r"javascript\s*:", "", html, flags=re.IGNORECASE)
        if "<html" not in html.lower():
            html = f"<!doctype html><html><head><meta charset=\"utf-8\"></head><body>{html}</body></html>"
        if "<meta charset" not in html.lower():
            html = html.replace("<head>", "<head><meta charset=\"utf-8\">", 1)
        return html[:80000]

    def _html_document_from_specs(self, deck_spec: dict) -> str:
        title = escape(str(deck_spec.get("title") or "HTML PPT"))
        slides = deck_spec.get("slides") if isinstance(deck_spec.get("slides"), list) else []
        slide_markup = []
        for index, slide in enumerate(slides[:12], start=1):
            layout = escape(str(slide.get("layout") or "concept"))
            slide_title = escape(str(slide.get("title") or f"第 {index} 页"))
            subtitle = escape(str(slide.get("subtitle") or ""))
            accent = escape(str(slide.get("accent") or slide_title))
            note = escape(str(slide.get("speaker_note") or ""))
            bullets = slide.get("bullets") if isinstance(slide.get("bullets"), list) else []
            bullet_markup = "".join(f"<li>{escape(str(item))}</li>" for item in bullets[:5])
            slide_markup.append(
                f"""
      <section class="slide layout-{layout}">
        <div class="slide-number">{index:02d}</div>
        <p class="kicker">{accent}</p>
        <h2>{slide_title}</h2>
        <p class="subtitle">{subtitle}</p>
        <ul>{bullet_markup}</ul>
        <aside>{note}</aside>
      </section>"""
            )
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light; --ink:#182431; --paper:#f8f4ea; --teal:#0f766e; --red:#b94a3a; --gold:#b98324; --blue:#355c9f; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: "Microsoft YaHei", "PingFang SC", sans-serif; color: var(--ink); background: #151b22; }}
    .deck {{ display: grid; gap: 22px; padding: 24px; }}
    .slide {{ position: relative; aspect-ratio: 16 / 9; min-height: 420px; overflow: hidden; padding: 54px 62px; background:
      linear-gradient(90deg, rgba(15,118,110,.08) 1px, transparent 1px),
      linear-gradient(0deg, rgba(15,118,110,.08) 1px, transparent 1px),
      radial-gradient(circle at 85% 12%, rgba(185,74,58,.22), transparent 24%),
      radial-gradient(circle at 8% 88%, rgba(53,92,159,.18), transparent 27%),
      var(--paper); background-size: 32px 32px, 32px 32px, auto, auto; box-shadow: 0 24px 60px rgba(0,0,0,.30); }}
    .slide::after {{ content: ""; position: absolute; right: -80px; bottom: -90px; width: 260px; height: 260px; border: 38px solid rgba(15,118,110,.12); transform: rotate(18deg); }}
    .slide-number {{ position: absolute; right: 38px; top: 30px; color: rgba(24,36,49,.32); font-size: 28px; font-weight: 900; }}
    .kicker {{ margin: 0 0 18px; color: var(--teal); font-size: 15px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }}
    h1, h2 {{ max-width: 780px; margin: 0; font-size: 48px; line-height: 1.08; letter-spacing: 0; }}
    .subtitle {{ max-width: 760px; margin: 16px 0 0; color: #51606f; font-size: 21px; line-height: 1.5; }}
    ul {{ position: relative; z-index: 2; display: grid; gap: 13px; max-width: 720px; margin: 34px 0 0; padding: 0; list-style: none; }}
    li {{ padding: 13px 16px; border-left: 5px solid var(--gold); background: rgba(255,255,255,.68); font-size: 20px; line-height: 1.45; font-weight: 700; }}
    aside {{ position: absolute; left: 62px; right: 62px; bottom: 34px; color: #5e5140; font-size: 14px; line-height: 1.6; }}
    .layout-cover h2 {{ font-size: 60px; }}
    .layout-compare li:nth-child(odd) {{ border-left-color: var(--red); }}
    .layout-flow li {{ border-left-color: var(--teal); }}
    .layout-code li {{ font-family: Consolas, "Microsoft YaHei", monospace; }}
    @media (max-width: 760px) {{ .deck {{ padding: 12px; }} .slide {{ min-height: 0; padding: 28px; }} h1, h2 {{ font-size: 30px; }} .subtitle, li {{ font-size: 16px; }} aside {{ position: static; margin-top: 22px; }} }}
  </style>
</head>
<body>
  <main class="deck" aria-label="{title}">
    {"".join(slide_markup)}
  </main>
</body>
</html>"""

    def _payload_from_deck(self, deck_spec: dict, html_document: str | None = None) -> dict:
        html = self._sanitize_html_document(html_document or "") or self._html_document_from_specs(deck_spec)
        return {
            "schema_version": 1,
            "kind": "html_ppt",
            "title": str(deck_spec.get("title") or "HTML PPT"),
            "theme": str(deck_spec.get("theme") or "html-ppt-classroom"),
            "slides": deck_spec.get("slides") if isinstance(deck_spec.get("slides"), list) else [],
            "html_document": html,
        }

    def _extract_html_document(self, content: str) -> str:
        text = str(content or "").strip()
        fence = re.search(r"```(?:html)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
        if fence:
            text = fence.group(1).strip()
        if "<html" in text.lower() or "<!doctype" in text.lower() or "<body" in text.lower():
            return self._sanitize_html_document(text)
        try:
            parsed = parse_llm_json(text)
        except json.JSONDecodeError:
            return ""
        if isinstance(parsed, dict):
            return self._sanitize_html_document(str(parsed.get("html_document") or parsed.get("html") or ""))
        return ""

    def content(self, state: WorkflowState) -> str:
        deck_spec = self._deck_spec(state)
        self.last_deck_spec = deck_spec
        return json.dumps(self._payload_from_deck(deck_spec), ensure_ascii=False, indent=2)

    def generate_content(self, state: WorkflowState) -> tuple[str, bool, str]:
        fallback_deck = self._deck_spec(state)
        fallback = json.dumps(self._payload_from_deck(fallback_deck), ensure_ascii=False, indent=2)
        self.last_deck_spec = fallback_deck
        prompt = (
            "你是一个资深的计算机教授和教学课件设计专家。"
            "请基于给定的课程章节、核心概念、详细知识点和真实案例，生成一份可直接嵌入 iframe srcdoc 的 HTML PPT。\n\n"
            "输出要求：\n"
            "1. 优先输出严格 JSON，不要 Markdown，不要代码块。\n"
            "2. JSON 顶层字段必须包含 kind、title、theme、slides、html_document，kind 固定为 html_ppt。\n"
            "3. html_document 必须是一份完整 HTML 文档，包含 <!doctype html> 或 <html>、内联 <style> 和 16:9 幻灯片页面。\n"
            "4. HTML 不要使用 script、onclick 等事件属性、外链资源、表单、iframe 或外部字体。\n"
            "5. slides 每页固定字段：title、subtitle、layout、bullets、speaker_note、visual_type、accent。\n"
            "6. layout 只能从 cover, agenda, concept, flow, compare, case, quiz, code, summary 中选择。\n"
            "7. 结构应覆盖导入、核心概念、流程、对比、案例、快问快答、代码实验、复盘。\n"
            "8. 每一页必须适合单页 16:9 放映：同一页内标题、正文、图片/图形、页脚必须分区摆放，不要互相覆盖或压在一起。\n"
            "9. 不要把多页 slide 使用绝对定位叠在同一屏；deck 应纵向排列多页，单页放映时每页都能独立完整显示。\n"
            "10. 每页文字使用短句和不超过 5 条要点，字号克制，避免超长段落导致折叠、截断或溢出。\n\n"
            f"课程章节标题：{state.chapter['title']}\n"
            f"核心概念：{state.chapter['concepts']}\n"
            f"详细知识点：{state.chapter['detailed_concepts']}\n"
            f"真实案例：{state.chapter['real_cases']}\n"
            f"常见误区：{state.chapter['misconceptions']}\n"
            f"代码实操任务：{state.chapter['code_labs']}\n"
            f"学生知识基础与偏好：{state.profile.knowledge_base}\n"
            f"可参考的 JSON 草案：{json.dumps(fallback_deck, ensure_ascii=False)}\n"
        )
        content, used_llm, reason = self.use_llm_or_fallback(prompt, json.dumps(fallback_deck, ensure_ascii=False))
        if used_llm:
            html_document = self._extract_html_document(content)
            try:
                parsed = parse_llm_json(content)
                if not isinstance(parsed, dict):
                    raise ValueError("top-level JSON is not an object")
                slides = self._normalize_slide_specs(parsed.get("slides"), state)
                deck_spec = {
                    "title": self._clean_text(parsed.get("title") or fallback_deck["title"], 80),
                    "theme": "html-ppt-classroom",
                    "slides": slides,
                }
                self.last_deck_spec = deck_spec
                html_document = self._sanitize_html_document(str(parsed.get("html_document") or "")) or html_document
                return json.dumps(self._payload_from_deck(deck_spec, html_document), ensure_ascii=False, indent=2), True, ""
            except (json.JSONDecodeError, ValueError) as exc:
                if html_document:
                    self.last_deck_spec = fallback_deck
                    return json.dumps(self._payload_from_deck(fallback_deck, html_document), ensure_ascii=False, indent=2), True, ""
                self.last_deck_spec = fallback_deck
                return fallback, False, f"LLM returned invalid HTML PPT JSON: {exc}"

        try:
            parsed = parse_llm_json(content)
            if isinstance(parsed, dict) and isinstance(parsed.get("slides"), list):
                self.last_deck_spec = {
                    "title": self._clean_text(parsed.get("title") or fallback_deck["title"], 80),
                    "theme": "html-ppt-classroom",
                    "slides": self._normalize_slide_specs(parsed.get("slides"), state),
                }
                return json.dumps(self._payload_from_deck(self.last_deck_spec), ensure_ascii=False, indent=2), False, reason
        except json.JSONDecodeError:
            pass
        self.last_deck_spec = fallback_deck
        return fallback, False, reason
