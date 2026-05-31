from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from xml.sax.saxutils import escape


EMU_PER_INCH = 914400
SLIDE_WIDTH = 13.333 * EMU_PER_INCH
SLIDE_HEIGHT = 7.5 * EMU_PER_INCH


@dataclass
class SlideSpec:
    title: str
    body: str
    speaker_note: str = ""


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", value, flags=re.UNICODE).strip("_")
    return (cleaned or "teaching_ppt")[:80]


def _text_runs(text: str, font_size: int = 2400) -> str:
    normalized = re.sub(r"<br\s*/?>", "\n", str(text or ""), flags=re.IGNORECASE)
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    if not lines:
        lines = [""]
    paragraphs = []
    for line in lines:
        paragraphs.append(
            "<a:p>"
            f"<a:r><a:rPr lang=\"zh-CN\" sz=\"{font_size}\" dirty=\"0\"/><a:t>{escape(line)}</a:t></a:r>"
            "</a:p>"
        )
    return "".join(paragraphs)


def _shape_xml(shape_id: int, name: str, x: int, y: int, cx: int, cy: int, text: str, font_size: int) -> str:
    return (
        "<p:sp>"
        "<p:nvSpPr>"
        f"<p:cNvPr id=\"{shape_id}\" name=\"{escape(name)}\"/>"
        "<p:cNvSpPr txBox=\"1\"/>"
        "<p:nvPr/>"
        "</p:nvSpPr>"
        "<p:spPr>"
        "<a:xfrm>"
        f"<a:off x=\"{x}\" y=\"{y}\"/>"
        f"<a:ext cx=\"{cx}\" cy=\"{cy}\"/>"
        "</a:xfrm>"
        "<a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom>"
        "<a:noFill/><a:ln><a:noFill/></a:ln>"
        "</p:spPr>"
        "<p:txBody>"
        "<a:bodyPr wrap=\"square\" rtlCol=\"0\"/>"
        "<a:lstStyle/>"
        f"{_text_runs(text, font_size)}"
        "</p:txBody>"
        "</p:sp>"
    )


def _slide_xml(slide: SlideSpec, index: int) -> str:
    title = _shape_xml(
        2,
        "Title",
        int(0.72 * EMU_PER_INCH),
        int(0.42 * EMU_PER_INCH),
        int(11.85 * EMU_PER_INCH),
        int(0.82 * EMU_PER_INCH),
        slide.title,
        3400,
    )
    body = _shape_xml(
        3,
        "Content",
        int(0.84 * EMU_PER_INCH),
        int(1.45 * EMU_PER_INCH),
        int(8.1 * EMU_PER_INCH),
        int(4.95 * EMU_PER_INCH),
        slide.body,
        2100,
    )
    note = _shape_xml(
        4,
        "Speaker note",
        int(9.15 * EMU_PER_INCH),
        int(1.45 * EMU_PER_INCH),
        int(3.3 * EMU_PER_INCH),
        int(4.95 * EMU_PER_INCH),
        f"讲者提示\n{slide.speaker_note}".strip(),
        1800,
    )
    footer = _shape_xml(
        5,
        "Footer",
        int(0.84 * EMU_PER_INCH),
        int(6.75 * EMU_PER_INCH),
        int(11.7 * EMU_PER_INCH),
        int(0.35 * EMU_PER_INCH),
        f"{index:02d}",
        1400,
    )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<p:sld xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">"
        "<p:cSld>"
        "<p:bg><p:bgPr><a:solidFill><a:srgbClr val=\"F8FBFD\"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>"
        "<p:spTree>"
        "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
        "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/>"
        "<a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
        f"{title}{body}{note}{footer}"
        "</p:spTree>"
        "</p:cSld>"
        "<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>"
        "</p:sld>"
    )


def _presentation_xml(slide_count: int) -> str:
    ids = []
    for index in range(1, slide_count + 1):
        ids.append(f"<p:sldId id=\"{255 + index}\" r:id=\"rId{index}\"/>")
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<p:presentation xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">"
        "<p:sldMasterIdLst><p:sldMasterId id=\"2147483648\" "
        f"r:id=\"rId{slide_count + 1}\"/></p:sldMasterIdLst>"
        f"<p:sldIdLst>{''.join(ids)}</p:sldIdLst>"
        "<p:sldSz cx=\"12192000\" cy=\"6858000\" type=\"wide\"/>"
        "<p:notesSz cx=\"6858000\" cy=\"9144000\"/>"
        "<p:defaultTextStyle>"
        "<a:defPPr><a:defRPr lang=\"zh-CN\"/></a:defPPr>"
        "<a:lvl1pPr marL=\"0\" algn=\"l\" defTabSz=\"914400\"><a:defRPr sz=\"1800\"/></a:lvl1pPr>"
        "</p:defaultTextStyle>"
        "</p:presentation>"
    )


def _presentation_rels(slide_count: int) -> str:
    rels = []
    for index in range(1, slide_count + 1):
        rels.append(
            f"<Relationship Id=\"rId{index}\" "
            "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide\" "
            f"Target=\"slides/slide{index}.xml\"/>"
        )
    rels.extend(
        [
            f"<Relationship Id=\"rId{slide_count + 1}\" "
            "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster\" "
            "Target=\"slideMasters/slideMaster1.xml\"/>",
            f"<Relationship Id=\"rId{slide_count + 2}\" "
            "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/presProps\" "
            "Target=\"presProps.xml\"/>",
            f"<Relationship Id=\"rId{slide_count + 3}\" "
            "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/viewProps\" "
            "Target=\"viewProps.xml\"/>",
            f"<Relationship Id=\"rId{slide_count + 4}\" "
            "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/tableStyles\" "
            "Target=\"tableStyles.xml\"/>",
        ]
    )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        f"{''.join(rels)}"
        "</Relationships>"
    )


def _content_types(slide_count: int) -> str:
    overrides = [
        "<Override PartName=\"/ppt/presentation.xml\" "
        "ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml\"/>",
        "<Override PartName=\"/ppt/slideMasters/slideMaster1.xml\" "
        "ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml\"/>",
        "<Override PartName=\"/ppt/slideLayouts/slideLayout1.xml\" "
        "ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml\"/>",
        "<Override PartName=\"/ppt/theme/theme1.xml\" "
        "ContentType=\"application/vnd.openxmlformats-officedocument.theme+xml\"/>",
        "<Override PartName=\"/ppt/presProps.xml\" "
        "ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.presProps+xml\"/>",
        "<Override PartName=\"/ppt/viewProps.xml\" "
        "ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml\"/>",
        "<Override PartName=\"/ppt/tableStyles.xml\" "
        "ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml\"/>",
        "<Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package.core-properties+xml\"/>",
        "<Override PartName=\"/docProps/app.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.extended-properties+xml\"/>",
    ]
    for index in range(1, slide_count + 1):
        overrides.append(
            f"<Override PartName=\"/ppt/slides/slide{index}.xml\" "
            "ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slide+xml\"/>"
        )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        f"{''.join(overrides)}"
        "</Types>"
    )


def _root_rels() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"ppt/presentation.xml\"/>"
        "<Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties\" Target=\"docProps/core.xml\"/>"
        "<Relationship Id=\"rId3\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties\" Target=\"docProps/app.xml\"/>"
        "</Relationships>"
    )


def _doc_props(title: str, slide_count: int) -> tuple[str, str]:
    core = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<cp:coreProperties xmlns:cp=\"http://schemas.openxmlformats.org/package/2006/metadata/core-properties\" "
        "xmlns:dc=\"http://purl.org/dc/elements/1.1/\" "
        "xmlns:dcterms=\"http://purl.org/dc/terms/\" "
        "xmlns:dcmitype=\"http://purl.org/dc/dcmitype/\" "
        "xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">"
        f"<dc:title>{escape(title)}</dc:title>"
        "<dc:creator>A3 PPT Agent</dc:creator>"
        "</cp:coreProperties>"
    )
    app = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties\" "
        "xmlns:vt=\"http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes\">"
        "<Application>A3 Personalized Learning</Application>"
        f"<Slides>{slide_count}</Slides>"
        "</Properties>"
    )
    return core, app


def _slide_rels() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" "
        "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" "
        "Target=\"../slideLayouts/slideLayout1.xml\"/>"
        "</Relationships>"
    )


def _slide_master_xml() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<p:sldMaster xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">"
        "<p:cSld><p:spTree>"
        "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
        "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/>"
        "<a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
        "</p:spTree></p:cSld>"
        "<p:clrMap bg1=\"lt1\" tx1=\"dk1\" bg2=\"lt2\" tx2=\"dk2\" accent1=\"accent1\" accent2=\"accent2\" "
        "accent3=\"accent3\" accent4=\"accent4\" accent5=\"accent5\" accent6=\"accent6\" hlink=\"hlink\" folHlink=\"folHlink\"/>"
        "<p:sldLayoutIdLst><p:sldLayoutId id=\"2147483649\" r:id=\"rId1\"/></p:sldLayoutIdLst>"
        "<p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles>"
        "</p:sldMaster>"
    )


def _slide_master_rels() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" "
        "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" "
        "Target=\"../slideLayouts/slideLayout1.xml\"/>"
        "<Relationship Id=\"rId2\" "
        "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme\" "
        "Target=\"../theme/theme1.xml\"/>"
        "</Relationships>"
    )


def _slide_layout_xml() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<p:sldLayout xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" "
        "xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" "
        "xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\" type=\"blank\" preserve=\"1\">"
        "<p:cSld name=\"Blank\"><p:spTree>"
        "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
        "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/>"
        "<a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
        "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>"
    )


def _slide_layout_rels() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" "
        "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster\" "
        "Target=\"../slideMasters/slideMaster1.xml\"/>"
        "</Relationships>"
    )


def _theme_xml() -> str:
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<a:theme xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" name=\"A3 Education\">"
        "<a:themeElements><a:clrScheme name=\"A3\">"
        "<a:dk1><a:srgbClr val=\"13212D\"/></a:dk1><a:lt1><a:srgbClr val=\"FFFFFF\"/></a:lt1>"
        "<a:dk2><a:srgbClr val=\"304557\"/></a:dk2><a:lt2><a:srgbClr val=\"F8FBFD\"/></a:lt2>"
        "<a:accent1><a:srgbClr val=\"176C7A\"/></a:accent1><a:accent2><a:srgbClr val=\"D69B2D\"/></a:accent2>"
        "<a:accent3><a:srgbClr val=\"425466\"/></a:accent3><a:accent4><a:srgbClr val=\"8BB8C2\"/></a:accent4>"
        "<a:accent5><a:srgbClr val=\"6B7280\"/></a:accent5><a:accent6><a:srgbClr val=\"E8F6EF\"/></a:accent6>"
        "<a:hlink><a:srgbClr val=\"176C7A\"/></a:hlink><a:folHlink><a:srgbClr val=\"425466\"/></a:folHlink>"
        "</a:clrScheme><a:fontScheme name=\"A3 Fonts\">"
        "<a:majorFont><a:latin typeface=\"Arial\"/><a:ea typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Arial\"/></a:majorFont>"
        "<a:minorFont><a:latin typeface=\"Arial\"/><a:ea typeface=\"Microsoft YaHei\"/><a:cs typeface=\"Arial\"/></a:minorFont>"
        "</a:fontScheme><a:fmtScheme name=\"A3 Format\"><a:fillStyleLst><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>"
        "<a:gradFill rotWithShape=\"1\"><a:gsLst><a:gs pos=\"0\"><a:schemeClr val=\"phClr\"/></a:gs>"
        "<a:gs pos=\"100000\"><a:schemeClr val=\"phClr\"/></a:gs></a:gsLst><a:lin ang=\"5400000\" scaled=\"0\"/></a:gradFill>"
        "<a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill></a:fillStyleLst>"
        "<a:lnStyleLst><a:ln w=\"6350\" cap=\"flat\" cmpd=\"sng\" algn=\"ctr\"><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill></a:ln>"
        "<a:ln w=\"12700\" cap=\"flat\" cmpd=\"sng\" algn=\"ctr\"><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill></a:ln>"
        "<a:ln w=\"19050\" cap=\"flat\" cmpd=\"sng\" algn=\"ctr\"><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill></a:ln></a:lnStyleLst>"
        "<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>"
        "<a:bgFillStyleLst><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill></a:bgFillStyleLst>"
        "</a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>"
    )


def _pres_props_xml() -> str:
    return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><p:presentationPr xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\"/>"


def _view_props_xml() -> str:
    return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><p:viewPr xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\"/>"


def _table_styles_xml() -> str:
    return "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><a:tblStyleLst xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" def=\"{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}\"/>"


def export_pptx(slides: list[SlideSpec], output_dir: Path, title: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{_safe_filename(title)}_{uuid4().hex[:8]}.pptx"
    target = output_dir / filename
    slide_count = max(len(slides), 1)
    if not slides:
        slides = [SlideSpec(title=title, body="暂无内容", speaker_note="请补充讲者提示")]
    core, app = _doc_props(title, slide_count)
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", _content_types(slide_count))
        package.writestr("_rels/.rels", _root_rels())
        package.writestr("docProps/core.xml", core)
        package.writestr("docProps/app.xml", app)
        package.writestr("ppt/presentation.xml", _presentation_xml(slide_count))
        package.writestr("ppt/_rels/presentation.xml.rels", _presentation_rels(slide_count))
        package.writestr("ppt/slideMasters/slideMaster1.xml", _slide_master_xml())
        package.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", _slide_master_rels())
        package.writestr("ppt/slideLayouts/slideLayout1.xml", _slide_layout_xml())
        package.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", _slide_layout_rels())
        package.writestr("ppt/theme/theme1.xml", _theme_xml())
        package.writestr("ppt/presProps.xml", _pres_props_xml())
        package.writestr("ppt/viewProps.xml", _view_props_xml())
        package.writestr("ppt/tableStyles.xml", _table_styles_xml())
        for index, slide in enumerate(slides, start=1):
            package.writestr(f"ppt/slides/slide{index}.xml", _slide_xml(slide, index))
            package.writestr(f"ppt/slides/_rels/slide{index}.xml.rels", _slide_rels())
    return target
