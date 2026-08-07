#!/usr/bin/env python3
"""
doc_qa.py — 文档问答工具

支持: 对 PDF/Word/TXT/MD 文件进行问答，基于 rag-knowledge-base + LLM

用法:
  python3 doc_qa.py ask --file contract.pdf "违约金条款是什么？"
  python3 doc_qa.py ask --dir ./docs "Q3 销售目标是多少？"
  python3 doc_qa.py index --file report.pdf
  python3 doc_qa.py --check
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path.home() / ".openclaw" / "output" / "doc_qa"
SKILLS_DIR = Path(__file__).resolve().parents[3]

def _get_llm_config() -> tuple:
    import sys as _sys
    _sd = str(Path(__file__).resolve().parents[3] / "scripts")
    if _sd not in _sys.path:
        _sys.path.insert(0, _sd)
    try:
        from skill_utils import get_llm_config
        k, u, m = get_llm_config()
        return k, f"{u}/chat/completions", m
    except ImportError:
        key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        return key, "https://api.deepseek.com/v1/chat/completions", "deepseek-chat"

SUPPORTED_EXT = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx"}


def _get_api_key() -> str:
    return _get_llm_config()[0]


def _extract_text(file_path: str) -> str:
    """从各类文件提取纯文本"""
    fp = Path(file_path)
    ext = fp.suffix.lower()

    if ext in (".txt", ".md"):
        return fp.read_text(encoding="utf-8", errors="ignore")

    if ext == ".pdf":
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                return "\n\n".join(p.extract_text() or "" for p in pdf.pages)
        except ImportError:
            pass
        # fallback: pdf-reader skill
        pdf_reader = SKILLS_DIR / "pdf-reader" / "scripts" / "pdf_reader.py"
        if pdf_reader.exists():
            r = subprocess.run(["python3", str(pdf_reader), "extract", "--file", file_path],
                               capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                return json.loads(r.stdout).get("text", "")
        return ""

    if ext in (".docx", ".doc"):
        word_tool = SKILLS_DIR / "word-docx-1.0.0" / "scripts" / "word_tool.py"
        if word_tool.exists():
            r = subprocess.run(["python3", str(word_tool), "read", "--file", file_path, "--json"],
                               capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                return json.loads(r.stdout).get("text", "")
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            return ""

    if ext in (".xlsx", ".csv"):
        try:
            import csv as csv_mod
            with open(file_path, encoding="utf-8") as f:
                rows = list(csv_mod.reader(f))
            return "\n".join(",".join(r) for r in rows[:500])
        except Exception:
            return ""

    return ""


def _chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> list:
    """按固定大小分块，带重叠"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def _find_relevant_chunks(chunks: list, question: str, top_k: int = 5) -> list:
    """简单关键词相关度排序（不依赖向量数据库）"""
    import re
    # 提取问题关键词
    keywords = [w for w in re.split(r'\s+|[，。？！,.!?]', question) if len(w) > 1]

    scored = []
    for i, chunk in enumerate(chunks):
        score = sum(chunk.count(kw) for kw in keywords)
        scored.append((score, i, chunk))

    scored.sort(reverse=True)
    return [c[2] for c in scored[:top_k]]


def _llm_qa(question: str, context: str, file_name: str = "") -> str:
    import urllib.request
    api_key, _chat_url, _model_id = _get_llm_config()
    if not api_key:
        return "[错误] 未配置 API Key，请在 openclaw.json 配置 deepseek 或 bailian"

    system = ("你是文档分析专家。根据提供的文档内容回答用户问题。"
              "回答要准确、简洁，直接引用文档原文支撑答案。"
              "如果文档中没有相关信息，明确说明'文档中未找到相关信息'。")

    user_msg = f"""文档: {file_name}

相关内容:
{context}

问题: {question}"""

    payload = {
        "model": _model_id,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.1,
        "max_tokens": 2000,
    }
    req = urllib.request.Request(
        _chat_url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def cmd_ask(question: str, file_path: str = None, directory: str = None,
            top_k: int = 5) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 收集文件列表
    files = []
    if file_path:
        files = [file_path]
    elif directory:
        d = Path(directory)
        files = [str(f) for f in d.rglob("*") if f.suffix.lower() in SUPPORTED_EXT]

    if not files:
        return {"status": "fail", "message": "没有找到可分析的文件"}

    all_chunks = []
    file_names = []
    for fp in files:
        if not Path(fp).exists():
            continue
        text = _extract_text(fp)
        if not text.strip():
            continue
        chunks = _chunk_text(text)
        all_chunks.extend(chunks)
        file_names.append(Path(fp).name)
        print(f"  📄 {Path(fp).name}: {len(text)} 字符 → {len(chunks)} 块", flush=True)

    if not all_chunks:
        return {"status": "fail", "message": "文件内容为空或无法提取"}

    relevant = _find_relevant_chunks(all_chunks, question, top_k)
    context = "\n\n---\n\n".join(relevant)

    answer = _llm_qa(question, context, ", ".join(file_names))

    result = {
        "status": "ok",
        "question": question,
        "answer": answer,
        "files": file_names,
        "chunks_searched": len(all_chunks),
        "chunks_used": len(relevant),
    }

    # 保存对话历史
    history_file = OUTPUT_DIR / "qa_history.jsonl"
    with open(history_file, "a", encoding="utf-8") as f:
        from datetime import datetime
        f.write(json.dumps({
            "time": datetime.now().isoformat(),
            "files": file_names,
            "question": question,
            "answer": answer,
        }, ensure_ascii=False) + "\n")

    return result


def health_check() -> dict:
    checks = []
    checks.append({"name": "DEEPSEEK_API_KEY", "status": "ok" if _get_api_key() else "fail",
                   "message": "已配置" if _get_api_key() else "未配置"})

    try:
        import pdfplumber
        checks.append({"name": "pdfplumber (PDF读取)", "status": "ok", "message": "已安装"})
    except ImportError:
        checks.append({"name": "pdfplumber (PDF读取)", "status": "warn",
                       "message": "未安装 (pip install pdfplumber)"})

    try:
        from docx import Document
        checks.append({"name": "python-docx (Word读取)", "status": "ok", "message": "已安装"})
    except ImportError:
        checks.append({"name": "python-docx (Word读取)", "status": "warn",
                       "message": "未安装 (pip install python-docx)"})

    checks.append({"name": "支持格式", "status": "ok",
                   "message": ", ".join(SUPPORTED_EXT)})

    overall = "fail" if any(c["status"] == "fail" for c in checks) else "ok"
    return {"skill": "document-qa", "version": "1.0.0", "status": overall, "checks": checks}


def main():
    parser = argparse.ArgumentParser(description="文档问答工具")
    parser.add_argument("command", nargs="?", choices=["ask", "index"])
    parser.add_argument("question", nargs="?", default="")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--file", default="")
    parser.add_argument("--dir", default="")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    if args.check:
        result = health_check()
    elif args.command == "ask":
        question = args.question
        if not question:
            print("错误: 请提供问题", file=sys.stderr); sys.exit(1)
        result = cmd_ask(question, args.file or None, args.dir or None, args.top_k)
    else:
        parser.print_help(); sys.exit(0)

    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result.get("status") == "ok":
            if "answer" in result:
                print(f"📄 文件: {', '.join(result['files'])}")
                print(f"❓ 问题: {result['question']}")
                print(f"\n💡 回答:\n{result['answer']}")
                print(f"\n(共检索 {result['chunks_searched']} 块，使用 {result['chunks_used']} 块)")
            elif "checks" in result:
                for c in result["checks"]:
                    icon = "✅" if c["status"] == "ok" else ("⚠️" if c["status"] == "warn" else "❌")
                    print(f"  {icon} {c['name']}: {c['message']}")
        else:
            print(f"❌ {result.get('message','失败')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
