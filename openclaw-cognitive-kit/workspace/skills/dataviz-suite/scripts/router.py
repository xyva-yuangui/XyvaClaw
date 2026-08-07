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
        "key": "chart",
        "title": "静态图表生成",
        "script": SKILLS_ROOT / "chart-image" / "scripts" / "chart.py",
        "keywords": ["图表", "柱状图", "折线图", "饼图", "散点图", "热力图", "chart"],
        "aliases": ["chart-image", "static-chart"],
        "examples": [
            "python3 scripts/router.py run chart -- --type bar --data 10,20,30 --labels A,B,C --title 销量",
            "python3 scripts/router.py run chart -- --type heatmap --data '[[1,2],[3,4]]' --labels 一列,二列",
        ],
        "notes": "统一进入 chart-image，负责参数化生成各类静态图表。",
    },
    {
        "key": "interactive",
        "title": "交互式可视化示例",
        "script": SUITE_ROOT / "scripts" / "interactive_adapter.py",
        "keywords": ["交互图", "plotly", "interactive", "交互式图表", "html图表"],
        "aliases": ["plotly", "interactive-chart"],
        "examples": [
            "python3 scripts/router.py run interactive -- check --json",
            "python3 scripts/router.py run interactive -- run",
        ],
        "notes": "统一进入 python-dataviz 的交互式 Plotly 示例，生成可在浏览器中查看的 HTML 图表。",
    },
    {
        "key": "diagram",
        "title": "架构图与流程图环境检查",
        "script": SKILLS_ROOT / "diagram-generator" / "scripts" / "check.py",
        "keywords": ["架构图", "流程图", "mermaid", "drawio", "excalidraw", "diagram"],
        "aliases": ["flowchart", "architecture-diagram"],
        "examples": [
            "python3 scripts/router.py run diagram -- --json",
        ],
        "notes": "统一进入 diagram-generator 的环境检测，确认外部 MCP 图形能力是否就绪。",
    },
]


def main() -> int:
    return run_suite_cli(
        suite_name="dataviz-suite",
        suite_root=SUITE_ROOT,
        description="Dataviz Suite 超级技能路由：统一编排静态图表、交互式图表与图形环境能力。",
        routes=ROUTES,
    )


if __name__ == "__main__":
    raise SystemExit(main())
