#!/usr/bin/env python3

import sys
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parents[2] / "_shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))

from suite_router import run_suite_cli

SUITE_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = SUITE_ROOT.parent

ROUTES = [
    {
        "key": "pdf-read",
        "title": "PDF 读取解析",
        "script": SKILLS_ROOT / "pdf-reader" / "scripts" / "pdf_reader.py",
        "keywords": ["读pdf", "读取pdf", "pdf解析", "pdf内容", "pdf元数据"],
        "aliases": ["pdf-reader", "read-pdf"],
        "examples": [
            "python3 scripts/router.py run pdf-read -- --read contract.pdf --meta",
            "python3 scripts/router.py run pdf-read -- --read report.pdf --pages 1-5",
        ],
        "notes": "统一进入 pdf-reader，负责 PDF 文本、表格和元信息提取。",
    },
    {
        "key": "pdf-generate",
        "title": "PDF 生成导出",
        "script": SKILLS_ROOT / "pdf-generator" / "scripts" / "generate_pdf.py",
        "keywords": ["生成pdf", "导出pdf", "markdown转pdf", "pdf生成"],
        "aliases": ["pdf-export", "make-pdf"],
        "examples": [
            "python3 scripts/router.py run pdf-generate -- --input article.md --output article.pdf --title 文档标题",
        ],
        "notes": "统一进入 pdf-generator，负责 Markdown/HTML 到 PDF 的导出。",
    },
    {
        "key": "excel",
        "title": "Excel/XLSX 处理",
        "script": SKILLS_ROOT / "excel-xlsx" / "scripts" / "excel_tool.py",
        "check_args": ["--check"],
        "keywords": ["excel", "xlsx", "表格分析", "读取表格", "生成excel", "转换excel"],
        "aliases": ["xlsx", "spreadsheet"],
        "examples": [
            "python3 scripts/router.py run excel -- read sales.xlsx --rows 20 --json",
            "python3 scripts/router.py run excel -- analyze sales.xlsx",
        ],
        "notes": "统一进入 excel-xlsx，负责读取、创建、分析和转换 Excel 文件。",
    },
    {
        "key": "word",
        "title": "Word/DOCX 处理",
        "script": SKILLS_ROOT / "word-docx-1.0.0" / "scripts" / "word_tool.py",
        "check_args": ["--check"],
        "keywords": ["word", "docx", "word文档", "生成word", "读取word", "插入表格"],
        "aliases": ["docx", "word-doc"],
        "examples": [
            "python3 scripts/router.py run word -- create --title 周报 --content '# 标题'",
            "python3 scripts/router.py run word -- read report.docx --json",
        ],
        "notes": "统一进入 word-docx，负责读取、创建、转换、插图和表格。",
    },
    {
        "key": "ppt-generate",
        "title": "AI 生成 PPT",
        "script": SKILLS_ROOT / "ppt-agent" / "scripts" / "ppt_agent.py",
        "check_args": ["check"],
        "keywords": ["生成ppt", "ai生成ppt", "幻灯片生成", "pptagent", "做个ppt"],
        "aliases": ["ppt-agent", "slides-generate"],
        "examples": [
            "python3 scripts/router.py run ppt-generate -- generate --template-pptx style.pptx --topic 2026年AI行业趋势",
            "python3 scripts/router.py run ppt-generate -- check",
        ],
        "notes": "统一进入 ppt-agent，负责基于模板和主题自动生成演示文稿。",
    },
    {
        "key": "pptx",
        "title": "PPTX 读写",
        "script": SKILLS_ROOT / "pptx-reader-writer" / "scripts" / "pptx_tool.py",
        "keywords": ["读取ppt", "pptx读写", "ppt转结构化", "创建pptx", "powerpoint"],
        "aliases": ["pptx-reader", "pptx-writer"],
        "examples": [
            "python3 scripts/router.py run pptx -- --read presentation.pptx --text-only",
            "python3 scripts/router.py run pptx -- --create --input outline.md --output out.pptx",
        ],
        "notes": "统一进入 pptx-reader-writer，负责读取现有 PPTX 和从 Markdown/JSON 创建 PPTX。",
    },
    {
        "key": "qa",
        "title": "文档问答",
        "script": SKILLS_ROOT / "document-qa" / "scripts" / "doc_qa.py",
        "check_args": ["--check"],
        "keywords": ["文档问答", "问答", "根据文档回答", "根据合同回答", "合同问答", "合同文档", "回答问题", "pdf问答", "document qa"],
        "aliases": ["document-qa", "ask-doc"],
        "examples": [
            "python3 scripts/router.py run qa -- ask 违约金条款是什么？ --file contract.pdf",
            "python3 scripts/router.py run qa -- --check",
        ],
        "notes": "统一进入 document-qa，负责基于文件或目录内容做问答检索。",
    },
]


def main() -> int:
    return run_suite_cli(
        suite_name="document-suite",
        suite_root=SUITE_ROOT,
        description="Document Suite 超级技能路由：统一编排 PDF、Excel、Word、PPT 与文档问答能力。",
        routes=ROUTES,
    )


if __name__ == "__main__":
    raise SystemExit(main())
