from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4


class PPTXRenderError(RuntimeError):
    pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _safe_filename(title: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\s]+", "_", title).strip("._")
    cleaned = cleaned[:48] or "teaching_deck"
    return f"{cleaned}_{uuid4().hex[:8]}.pptx"


def render_pptx_deck(payload: dict, output_dir: Path | None = None, timeout: int = 90) -> dict:
    node_bin = shutil.which("node")
    if not node_bin:
        raise PPTXRenderError("Node.js is not available, cannot render PPTX")

    root = _repo_root()
    script = root / "tools" / "pptx-renderer" / "render-pptx.mjs"
    if not script.exists():
        raise PPTXRenderError(f"PPTX renderer script not found: {script}")

    output_dir = output_dir or root / "backend" / "generated" / "pptx"
    output_dir.mkdir(parents=True, exist_ok=True)
    title = str(payload.get("title") or "teaching_deck")
    filename = _safe_filename(title)
    target = output_dir / filename

    proc = subprocess.run(
        [node_bin, str(script), "--output", str(target)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=timeout,
        cwd=str(script.parent),
        check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "unknown renderer error").strip()
        raise PPTXRenderError(detail[:1000])
    if not target.exists() or target.stat().st_size <= 0:
        raise PPTXRenderError("PPTX renderer finished without a valid output file")

    return {
        "artifact_path": str(target),
        "artifact_filename": filename,
        "artifact_url": f"/api/artifacts/{quote(filename)}",
    }
