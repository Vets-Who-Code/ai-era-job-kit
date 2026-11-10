"""Turn a resume (PDF, DOCX, TXT, MD) into plain text with no extra installs.

PDF uses `pdftotext` (poppler) when present. If it is missing, export the
resume to .txt or .docx instead.
"""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import zipfile


def read_text(path: str, layout: bool = True) -> str:
    """layout=False reads a PDF in reading order instead of keeping side-by-side columns side by side."""
    p = pathlib.Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(p)
    ext = p.suffix.lower()
    if ext in (".txt", ".md", ".markdown"):
        return p.read_text(errors="replace")
    if ext == ".docx":
        with zipfile.ZipFile(p) as z:
            xml = z.read("word/document.xml").decode("utf8", "replace")
        xml = re.sub(r"</w:p>", "\n", xml)
        xml = re.sub(r"<w:tab/>", "\t", xml)
        return re.sub(r"<[^>]+>", "", xml)
    if ext == ".pdf":
        exe = shutil.which("pdftotext")
        if not exe:
            raise RuntimeError("pdftotext not found. Install poppler, or save the resume as .txt or .docx.")
        out = subprocess.run([exe, *(["-layout"] if layout else []), str(p), "-"], capture_output=True, text=True, check=True)
        return out.stdout
    raise ValueError(f"Unsupported resume format: {ext}")


SECTION_RE = re.compile(r"^\s*(technical\s+)?skills?\b|^\s*(core\s+)?competencies|^\s*technologies|^\s*tools",
                        re.I)
HEADING_RE = re.compile(r"^\s*[A-Z][A-Za-z &/]{2,40}\s*$")


def split_skills_section(text: str) -> tuple[str, str]:
    """Return (skills_section_text, everything_else). Heuristic, line-based."""
    skills, rest, in_skills = [], [], False
    for line in text.splitlines():
        if SECTION_RE.match(line):
            in_skills = True
            skills.append(line)
            continue
        if in_skills and HEADING_RE.match(line) and not SECTION_RE.match(line) and len(line.split()) <= 4:
            in_skills = False
        (skills if in_skills else rest).append(line)
    return "\n".join(skills), "\n".join(rest)
