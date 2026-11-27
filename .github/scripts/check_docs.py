#!/usr/bin/env python3
"""文档卫生检查：死链、文档头、文件清单。

三条规则，对应 docs/process/doc-rules.md：

1. 相对链接必须可达（文档里断链比没文档更糟）；
2. `docs/` 下的正式文档必须有文档头（状态 + 最后更新）；
3. `docs/` 下只允许白名单里的文件——文件名不带版本号、不带日期，
   新增文件必须先改这份白名单，顺手回答“为什么不能并进现有文件”。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ALLOWED = {
    "docs/README.md",
    "docs/requirements/requirements.md",
    "docs/tech/protocol.md",
    "docs/tech/decisions.md",
    "docs/tech/sdk.md",
    "docs/tech/mobile.md",
    "docs/tech/key-registry.md",
    "docs/test/test-plan.md",
    "docs/test/acceptance.md",
    "docs/process/iteration.md",
    "docs/process/doc-rules.md",
}

SCAN = [
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "docs/**/*.md",
    "testvectors/README.md",
    ".github/pull_request_template.md",
]

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SKIP_PREFIX = ("http://", "https://", "mailto:", "#")


def markdown_files() -> list[Path]:
    files: list[Path] = []
    for pattern in SCAN:
        files.extend(sorted(ROOT.glob(pattern)))
    return [p for p in files if p.is_file()]


def check_links(path: Path) -> list[str]:
    errors: list[str] = []
    for target in LINK_RE.findall(path.read_text(encoding="utf-8")):
        if target.startswith(SKIP_PREFIX):
            continue
        clean = target.split("#", 1)[0]
        if not clean:
            continue
        resolved = (path.parent / clean).resolve()
        if not resolved.exists():
            errors.append(f"{path.relative_to(ROOT)}: 死链 -> {target}")
    return errors


HEADER_LINES = 15


def check_header(path: Path) -> list[str]:
    head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:HEADER_LINES])
    if "| 项 | 值 |" not in head:
        return [f"{path.relative_to(ROOT)}: 开头缺少文档头表格（| 项 | 值 | 状态 | 最后更新 |）"]
    return [
        f"{path.relative_to(ROOT)}: 文档头缺少 {key}"
        for key in ("| 状态 |", "| 最后更新 |")
        if key not in head
    ]


def main() -> int:
    errors: list[str] = []
    files = markdown_files()

    for path in files:
        errors.extend(check_links(path))

    present = {p.relative_to(ROOT).as_posix() for p in (ROOT / "docs").rglob("*.md")}
    for extra in sorted(present - ALLOWED):
        errors.append(f"{extra}: 不在白名单里。文件名不带版本号/日期；先改 check_docs.py 再解释为什么不并进现有文件")
    for missing in sorted(ALLOWED - present):
        errors.append(f"{missing}: 白名单里登记了但文件不存在")

    for relative in sorted(ALLOWED - {"docs/README.md"}):
        path = ROOT / relative
        if path.is_file():
            errors.extend(check_header(path))

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print(f"\n{len(errors)} 个问题")
        return 1

    print(f"OK: {len(files)} 个 Markdown 文件，{len(ALLOWED)} 个正式文档，无死链")
    return 0


if __name__ == "__main__":
    sys.exit(main())
