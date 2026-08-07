#!/usr/bin/env python3
"""
translate.py — 专业翻译工具

支持: 文本翻译 / 文件翻译 / 批量 CSV / 电商专项翻译

用法:
  python3 translate.py text "Hello World" --to zh
  python3 translate.py file contract.pdf --to en --domain legal
  python3 translate.py batch products.csv --col description --to en
  python3 translate.py ecommerce --input listing_zh.json --platform amazon --to en
  python3 translate.py --check
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[3]
GLOSSARY_DIR = Path(__file__).parent / "glossaries"
OUTPUT_DIR = Path.home() / ".openclaw" / "output" / "translations"

def _get_llm_config() -> tuple:
    """返回 (api_key, chat_url, model_id) — 从 openclaw.json models.providers 读取"""
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

CHUNK_SIZE = 1500  # characters per chunk

LANG_NAMES = {
    "zh": "中文（简体）",
    "zh-tw": "中文（繁體）",
    "en": "英文",
    "ja": "日文",
    "ko": "韩文",
    "fr": "法文",
    "de": "德文",
    "es": "西班牙文",
    "pt": "葡萄牙文",
    "ar": "阿拉伯文",
    "th": "泰文",
    "vi": "越南文",
    "id": "印尼文",
    "ms": "马来文",
}

DOMAINS = ["ecommerce", "legal", "logistics", "tech", "medical", "general"]


def _get_api_key() -> str:
    return _get_llm_config()[0]


def _load_glossary(domain: str, from_lang: str, to_lang: str) -> dict:
    path = GLOSSARY_DIR / f"{domain}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        key = f"{from_lang}_to_{to_lang}"
        return data.get(key, {})
    except Exception:
        return {}


def _llm_translate(text: str, to_lang: str, from_lang: str, domain: str,
                   glossary: dict, context: str = "") -> str:
    import urllib.request
    api_key, _chat_url, _model_id = _get_llm_config()
    if not api_key:
        return "[错误] 未配置 API Key，请在 openclaw.json 配置 deepseek 或 bailian"

    to_name = LANG_NAMES.get(to_lang, to_lang)
    from_name = LANG_NAMES.get(from_lang, "自动检测")

    system = f"你是一位专业翻译，精通{from_name}和{to_name}。翻译时保持原文格式结构，专业术语准确，语言自然流畅。直接输出译文，不要添加任何解释或前缀。"

    glossary_note = ""
    if glossary:
        pairs = [f"{k}→{v}" for k, v in list(glossary.items())[:20]]
        glossary_note = f"\n\n术语对照表（请严格按此翻译）:\n" + "\n".join(pairs)

    context_note = f"\n\n翻译背景: {context}" if context else ""
    domain_note = f"\n翻译领域: {domain}" if domain and domain != "general" else ""

    user_msg = f"请将以下内容翻译为{to_name}：{domain_note}{context_note}{glossary_note}\n\n{text}"

    payload = {
        "model": _model_id,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }
    req = urllib.request.Request(
        _chat_url,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]


def _split_chunks(text: str, chunk_size: int = CHUNK_SIZE) -> list:
    """按段落/句子边界分块，保持语义完整"""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    current = ""
    for para in text.split("\n"):
        if len(current) + len(para) + 1 <= chunk_size:
            current += para + "\n"
        else:
            if current:
                chunks.append(current.rstrip())
            if len(para) > chunk_size:
                # 超长段落按句子分割
                sentences = para.replace("。", "。\n").replace(". ", ". \n").split("\n")
                for sent in sentences:
                    if len(current) + len(sent) <= chunk_size:
                        current = sent
                    else:
                        if current:
                            chunks.append(current)
                        current = sent
            else:
                current = para + "\n"
    if current:
        chunks.append(current.rstrip())
    return chunks


def cmd_text(text: str, to_lang: str, from_lang: str = "auto",
             domain: str = "general", context: str = "") -> dict:
    glossary = _load_glossary(domain, from_lang if from_lang != "auto" else "zh", to_lang)
    result = _llm_translate(text, to_lang, from_lang, domain, glossary, context)
    return {
        "status": "ok",
        "original": text,
        "translated": result,
        "to_lang": to_lang,
        "domain": domain,
        "char_count": len(result),
    }


def cmd_file(file_path: str, to_lang: str, from_lang: str = "auto",
             domain: str = "general", output_path: str = None) -> dict:
    fp = Path(file_path)
    if not fp.exists():
        return {"status": "fail", "message": f"文件不存在: {file_path}"}

    suffix = fp.suffix.lower()

    # 提取文本
    if suffix == ".txt" or suffix == ".md":
        text = fp.read_text(encoding="utf-8")
    elif suffix == ".pdf":
        # 尝试用 pdf-reader skill 或 pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                text = "\n\n".join(page.extract_text() or "" for page in pdf.pages)
        except ImportError:
            try:
                import subprocess
                result = subprocess.run(
                    ["python3", str(SKILLS_DIR / "pdf-reader" / "scripts" / "pdf_reader.py"),
                     "extract", "--file", file_path],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    text = data.get("text", "")
                else:
                    return {"status": "fail", "message": "PDF 提取失败，请安装 pdfplumber: pip install pdfplumber"}
            except Exception as e:
                return {"status": "fail", "message": f"PDF 提取失败: {e}"}
    elif suffix in (".docx", ".doc"):
        try:
            import subprocess
            result = subprocess.run(
                ["python3", str(SKILLS_DIR / "word-docx-1.0.0" / "scripts" / "word_tool.py"),
                 "read", "--file", file_path, "--json"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                text = data.get("text", "")
            else:
                return {"status": "fail", "message": "DOCX 读取失败"}
        except Exception as e:
            return {"status": "fail", "message": f"DOCX 读取失败: {e}"}
    elif suffix == ".csv":
        return {"status": "fail", "message": "CSV 文件请使用 batch 命令"}
    else:
        try:
            text = fp.read_text(encoding="utf-8")
        except Exception:
            return {"status": "fail", "message": f"不支持的文件格式: {suffix}"}

    if not text.strip():
        return {"status": "fail", "message": "文件内容为空"}

    # 分块翻译
    chunks = _split_chunks(text)
    glossary = _load_glossary(domain, from_lang if from_lang != "auto" else "zh", to_lang)
    translated_parts = []
    print(f"  文件共 {len(text)} 字符，分 {len(chunks)} 块翻译...", flush=True)

    for i, chunk in enumerate(chunks):
        print(f"  翻译进度: {i+1}/{len(chunks)}", flush=True)
        t = _llm_translate(chunk, to_lang, from_lang, domain, glossary)
        translated_parts.append(t)

    translated = "\n\n".join(translated_parts)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not output_path:
        output_path = str(OUTPUT_DIR / f"{fp.stem}_{to_lang}{fp.suffix}")

    Path(output_path).write_text(translated, encoding="utf-8")
    return {
        "status": "ok",
        "original_file": file_path,
        "output": output_path,
        "to_lang": to_lang,
        "domain": domain,
        "original_chars": len(text),
        "translated_chars": len(translated),
        "chunks": len(chunks),
    }


def cmd_batch(input_file: str, col: str, to_lang: str, from_lang: str = "auto",
              domain: str = "ecommerce", output_file: str = None) -> dict:
    if not Path(input_file).exists():
        return {"status": "fail", "message": f"文件不存在: {input_file}"}

    with open(input_file, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return {"status": "fail", "message": "CSV 文件为空"}

    if col not in rows[0]:
        available = list(rows[0].keys())
        return {"status": "fail", "message": f"列 '{col}' 不存在，可用列: {available}"}

    glossary = _load_glossary(domain, from_lang if from_lang != "auto" else "zh", to_lang)
    new_col = f"{col}_{to_lang}"
    fail_count = 0

    for i, row in enumerate(rows):
        text = row.get(col, "")
        if not text.strip():
            row[new_col] = ""
            continue
        print(f"  [{i+1}/{len(rows)}] 翻译...", flush=True)
        try:
            row[new_col] = _llm_translate(text, to_lang, from_lang, domain, glossary)
        except Exception as e:
            row[new_col] = f"[翻译失败: {e}]"
            fail_count += 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not output_file:
        p = Path(input_file)
        output_file = str(OUTPUT_DIR / f"{p.stem}_{to_lang}.csv")

    fieldnames = list(rows[0].keys())
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "status": "ok",
        "total": len(rows),
        "success": len(rows) - fail_count,
        "fail": fail_count,
        "output": output_file,
        "new_col": new_col,
    }


def cmd_ecommerce(input_file: str, platform: str, to_lang: str = "en",
                  from_lang: str = "zh", output_file: str = None) -> dict:
    if not Path(input_file).exists():
        return {"status": "fail", "message": f"文件不存在: {input_file}"}

    with open(input_file, encoding="utf-8") as f:
        listing = json.load(f)

    glossary = _load_glossary("ecommerce", from_lang, to_lang)

    PLATFORM_LIMITS = {
        "amazon":  {"title": 200, "bullet_max": 500, "desc": 2000},
        "shopify": {"title": 255, "seo_title": 60, "seo_desc": 160},
        "lazada":  {"title": 255},
        "shopee":  {"title": 120},
    }
    limits = PLATFORM_LIMITS.get(platform, {})

    translated = {}
    fields_to_translate = ["title", "description", "selling_points", "bullets",
                            "seo_title", "seo_description", "tags"]

    for field in fields_to_translate:
        if field not in listing:
            continue
        val = listing[field]
        if isinstance(val, str):
            t = _llm_translate(val, to_lang, from_lang, "ecommerce", glossary)
            # 字数校验
            limit_key = "title" if field == "title" else field.replace("_", "")
            max_len = limits.get(field) or limits.get(limit_key)
            if max_len and len(t) > max_len:
                compress_prompt = f"以下{platform}平台文案超过{max_len}字符限制，请压缩至{max_len}字符内，保留核心意思：\n\n{t}"
                t = _llm_translate(compress_prompt, to_lang, from_lang, "ecommerce", {})
            translated[field] = t
        elif isinstance(val, list):
            translated[field] = [_llm_translate(item, to_lang, from_lang, "ecommerce", glossary) for item in val]
        else:
            translated[field] = val

    # 保留未翻译字段
    for k, v in listing.items():
        if k not in translated:
            translated[k] = v

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not output_file:
        p = Path(input_file)
        output_file = str(OUTPUT_DIR / f"{p.stem}_{platform}_{to_lang}.json")

    Path(output_file).write_text(json.dumps(translated, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "ok",
        "platform": platform,
        "to_lang": to_lang,
        "output": output_file,
        "fields_translated": list(translated.keys()),
    }


def health_check() -> dict:
    checks = []
    api_key = _get_api_key()
    checks.append({"name": "DEEPSEEK_API_KEY", "status": "ok" if api_key else "fail",
                    "message": "已配置" if api_key else "未设置 DEEPSEEK_API_KEY"})

    glossaries = list(GLOSSARY_DIR.glob("*.json")) if GLOSSARY_DIR.exists() else []
    checks.append({"name": "glossaries", "status": "ok",
                    "message": f"已加载 {len(glossaries)} 个词汇表: {[g.stem for g in glossaries]}"})

    checks.append({"name": "languages", "status": "ok",
                    "message": f"支持 {len(LANG_NAMES)} 种语言"})

    overall = "fail" if any(c["status"] == "fail" for c in checks) else "ok"
    return {"skill": "translation", "version": "1.0.0", "status": overall, "checks": checks}


def main():
    parser = argparse.ArgumentParser(description="专业翻译工具")
    parser.add_argument("command", nargs="?", choices=["text", "file", "batch", "ecommerce"])
    parser.add_argument("content", nargs="?", default="")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--to", default="en", help="目标语言: zh/en/ja/ko/fr/de/es...")
    parser.add_argument("--from", dest="from_lang", default="auto", help="源语言（默认自动检测）")
    parser.add_argument("--domain", default="general",
                        choices=DOMAINS, help="翻译领域")
    parser.add_argument("--context", default="")
    parser.add_argument("--col", default="description")
    parser.add_argument("--input", default="")
    parser.add_argument("--platform", default="amazon")
    parser.add_argument("--output", default=None)
    parser.add_argument("--json", dest="as_json", action="store_true")
    args = parser.parse_args()

    if args.check:
        result = health_check()
    elif args.command == "text":
        text = args.content or args.input
        if not text:
            print("错误: 请提供要翻译的文本", file=sys.stderr); sys.exit(1)
        result = cmd_text(text, args.to, args.from_lang, args.domain, args.context)
    elif args.command == "file":
        fp = args.content or args.input
        if not fp:
            print("错误: 请提供文件路径", file=sys.stderr); sys.exit(1)
        result = cmd_file(fp, args.to, args.from_lang, args.domain, args.output)
    elif args.command == "batch":
        fp = args.content or args.input
        if not fp:
            print("错误: 请提供 CSV 文件路径", file=sys.stderr); sys.exit(1)
        result = cmd_batch(fp, args.col, args.to, args.from_lang, args.domain, args.output)
    elif args.command == "ecommerce":
        fp = args.content or args.input
        if not fp:
            print("错误: 请提供 Listing JSON 文件路径", file=sys.stderr); sys.exit(1)
        result = cmd_ecommerce(fp, args.platform, args.to, args.from_lang, args.output)
    else:
        parser.print_help(); sys.exit(0)

    if args.as_json:
        out = {k: v for k, v in result.items() if k not in ("original",)}
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        if result.get("status") == "ok":
            if "translated" in result:
                print(f"✅ 翻译完成 ({len(result['translated'])} 字符)")
                print("\n" + result["translated"])
            elif "output" in result:
                print(f"✅ 已保存: {result['output']}")
                if "total" in result:
                    print(f"   {result.get('success',0)}/{result.get('total',0)} 行成功")
                if "chunks" in result:
                    print(f"   共 {result['chunks']} 块，{result['original_chars']} → {result['translated_chars']} 字符")
            elif "checks" in result:
                print(f"健康检查: {result['status']}")
                for c in result.get("checks", []):
                    icon = "✅" if c["status"] == "ok" else "❌"
                    print(f"  {icon} {c['name']}: {c.get('message','')}")
        else:
            print(f"❌ {result.get('message','失败')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
