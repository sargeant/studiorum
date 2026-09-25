"""PDF compilation with latexmk.

latexmk runs the engine as many times as cross-references and the table of
contents need. ``build_pdf`` tries the configured engines in turn and, when
they all fail, returns the first error from each log with a hint.
"""

from __future__ import annotations

import re
import shutil

# latexmk is resolved to a full path with get_safe_executable
import subprocess  # nosec B404
from pathlib import Path

from studiorum.core.config.unified_config import LaTeXEngineConfig
from studiorum.core.result import Error, Result, Success
from studiorum.core.security import ExecutableNotFoundError, get_safe_executable

_ENGINE_FLAGS = {"xelatex": "-xelatex", "lualatex": "-lualatex", "pdflatex": "-pdf"}

# With -file-line-error an error reads "file:line: message"; some start with "!".
_ERROR = re.compile(r"^(?:\S.*?:\d+: |! )(.+)")

_HINTS = (
    (
        re.compile(r"File `(dndbook\.cls|dnd\.sty)' not found"),
        "Install the DND 5e LaTeX template (the dndbook class) under your "
        "TEXMFHOME, e.g. ~/Library/texmf/tex/latex/dnd.",
    ),
    (
        re.compile(r"fontspec package requires either XeTeX or"),
        "The template's fonts need xelatex or lualatex: set "
        "rendering.latex.engine.primary_engine.",
    ),
    (
        re.compile(r'The font "[^"]+" cannot be found'),
        "Install the font, or choose a font scheme that doesn't use it.",
    ),
    (
        re.compile(r"File `[^']+' not found"),
        "Install the TeX package that provides the file (tlmgr search --file).",
    ),
    (
        re.compile(r"Undefined control sequence"),
        "A macro is undefined: the installed template may be older than "
        "Studiorum's templates expect.",
    ),
)


def build_pdf(tex: Path, engines: LaTeXEngineConfig) -> Result[Path, str]:
    """Compile ``tex`` to a PDF beside it, trying each configured engine in turn."""
    try:
        latexmk = get_safe_executable("latexmk")
    except ExecutableNotFoundError:
        return Error("latexmk is not installed; it comes with TeX Live and MacTeX")

    failures = []
    for engine in dict.fromkeys([engines.primary_engine, *engines.fallback_engines]):
        if shutil.which(engine) is None:
            failures.append(f"{engine}: not installed")
            continue
        command = [
            latexmk,
            _ENGINE_FLAGS[engine],
            "-interaction=nonstopmode",
            "-file-line-error",
            "-halt-on-error",
            f"-outdir={tex.parent}",
            tex.name,
        ]
        try:
            run = subprocess.run(  # nosec B603
                command,
                cwd=tex.parent,
                capture_output=True,
                text=True,
                timeout=engines.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            failures.append(f"{engine}: timed out after {engines.timeout} s")
            continue
        pdf = tex.with_suffix(".pdf")
        if run.returncode == 0 and pdf.exists():
            return Success(pdf)
        failures.append(f"{engine}: {summarise_log(tex.with_suffix('.log'))}")
    return Error("\n".join(failures))


def summarise_log(log: Path) -> str:
    """The first error in a LaTeX log, with the source line and a hint if one fits."""
    if not log.exists():
        return f"no log was written ({log.name})"
    lines = _unwrap(log.read_text(encoding="utf-8", errors="replace").splitlines())
    for index, line in enumerate(lines):
        match = _ERROR.match(line)
        if not match:
            continue
        # A message can continue on the lines after it.
        message = " ".join([match.group(1), *lines[index + 1 : index + 3]])
        summary = [line]
        source = next(
            (s for s in lines[index + 1 : index + 12] if s.startswith("l.")), None
        )
        if source:
            summary.append(source)
        hint = next((h for pattern, h in _HINTS if pattern.search(message)), None)
        if hint:
            summary.append(f"Hint: {hint}")
        summary.append(f"See {log}")
        return "\n".join(summary)
    return f"no error found in the log; see {log}"


def _unwrap(lines: list[str]) -> list[str]:
    """Join the lines TeX broke at its 79-character log width."""
    joined: list[str] = []
    pending = ""
    for line in lines:
        pending += line
        if len(line) != 79:
            joined.append(pending)
            pending = ""
    if pending:
        joined.append(pending)
    return joined
