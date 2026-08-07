#!/usr/bin/env python3
"""
OpenClaw 打包密钥清洗脚本（最终关卡）
全仓扫描文本文件，将密钥字段和常见密钥格式替换为语义化占位符。
不内置任何真实密钥值，仅按字段名和格式识别，可安全随包分发。

用法:
    python3 scrub-secrets.py <package_dir>          # 就地清洗
    python3 scrub-secrets.py <package_dir> --check  # 只检测，发现疑似密钥退出码 1（供 pack.sh 打包前校验）
"""
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "pdf_venv", "__pycache__"}
BINARY_EXT = {
    ".db", ".sqlite", ".db-shm", ".db-wal", ".sqlite-shm", ".sqlite-wal",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz",
    ".tar", ".pyc", ".so", ".dylib", ".woff", ".woff2", ".ttf", ".otf",
    ".mp4", ".mp3", ".opus", ".wav", ".pickle", ".pkl", ".bin",
}

# ── 通用文本规则（适用于所有文本文件：md / py / sh / jsonl …）──
# 说明:
#   sk-*        OpenAI / DashScope / DeepSeek 系密钥格式
#   JWT         三段式 eyJ 开头 token
#   rt_*        OAuth refresh token 格式
#   AYjC*       飞书 appSecret 格式
#   44-64位hex  gateway token / tushare token 等长 hex 密钥（git SHA-1 为 40 位，不会误伤）
GENERIC_RULES = [
    (re.compile(rb"sk-[A-Za-z0-9_\-]{20,}"), b"REDACTED_API_KEY"),
    (re.compile(rb"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}"), b"REDACTED_JWT"),
    (re.compile(rb"rt_[A-Za-z0-9_\-\.]{40,}"), b"REDACTED_OAUTH_REFRESH"),
    (re.compile(rb"AYjC[A-Za-z0-9]{28,}"), b"YOUR_FEISHU_APP_SECRET"),
    (re.compile(rb"\b[a-f0-9]{44,64}\b"), b"REDACTED_HEX_TOKEN"),
]

# 占位符/示例值不清洗（.env.template、文档示例等）
WHITELIST_RE = re.compile(rb"your[-_]|YOUR_|REDACTED_|xxx|example|placeholder", re.IGNORECASE)

# ── JSON 结构化规则（auth-profiles.json / models.json / openclaw.json …）──
# 全局无歧义密钥字段（任何 JSON 文件都清洗）
GLOBAL_SECRET_FIELDS = {"apiKey", "appSecret", "token"}
# 泛用字段名（仅在 auth-profiles 文件中按密钥处理，避免误伤普通配置）
AUTH_PROFILE_FIELDS = {"key", "access", "refresh"}
PROVIDER_PLACEHOLDER = {
    "bailian": "YOUR_BAILIAN_API_KEY",
    "deepseek": "YOUR_DEEPSEEK_API_KEY",
    "wanxiang": "YOUR_WANXIANG_API_KEY",
    "openai": "YOUR_OPENAI_API_KEY",
    "openai-codex": "YOUR_OPENAI_API_KEY",
    "minimax-cn": "YOUR_MINIMAX_API_KEY",
    "kimi-coding": "YOUR_KIMI_API_KEY",
    "qwen-portal": "YOUR_QWEN_PORTAL_KEY",
    "amap": "YOUR_AMAP_API_KEY",
}

findings = []
# 二进制文件（db/sqlite/pickle 等）中的密钥：无法就地改写，必须从包中排除
binary_hits = []


def looks_secret(value: str) -> bool:
    """长度 ≥16、无空格、非占位符的字符串视为疑似密钥"""
    if not isinstance(value, str) or len(value) < 16 or " " in value:
        return False
    if WHITELIST_RE.search(value.encode()):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_\-\.%=+/]{16,}", value))


def placeholder_for(field: str, provider_hint: str, file_path: Path) -> str:
    if field == "appSecret":
        return "YOUR_FEISHU_APP_SECRET"
    if field == "access":
        return "REDACTED_OAUTH_ACCESS"
    if field == "refresh":
        return "REDACTED_OAUTH_REFRESH"
    if field == "token":
        if file_path.name == "tushare.json":
            return "YOUR_TUSHARE_TOKEN"
        return "YOUR_GATEWAY_TOKEN"
    # apiKey / key: 按 provider 上下文给语义化占位符
    for name, ph in PROVIDER_PLACEHOLDER.items():
        if name in provider_hint:
            return ph
    return "YOUR_API_KEY"


def scrub_json_obj(obj, file_path: Path, provider_hint=""):
    """递归清洗 JSON，利用父级 key / provider 字段推断占位符语义"""
    secret_fields = set(GLOBAL_SECRET_FIELDS)
    if file_path.name.startswith("auth-profiles"):
        secret_fields |= AUTH_PROFILE_FIELDS
    changed = False
    if isinstance(obj, dict):
        hint = str(obj.get("provider", "")) or provider_hint
        for k, v in obj.items():
            if k in secret_fields and looks_secret(v):
                obj[k] = placeholder_for(k, hint, file_path)
                findings.append(f"{file_path}: 字段 {k}")
                changed = True
            elif isinstance(v, (dict, list)):
                # 父级 key（如 providers 下的 "bailian"）作为 provider 提示
                child_hint = k if k in PROVIDER_PLACEHOLDER else hint
                if scrub_json_obj(v, file_path, child_hint):
                    changed = True
    elif isinstance(obj, list):
        for item in obj:
            if scrub_json_obj(item, file_path, provider_hint):
                changed = True
    return changed


def scrub_text(data: bytes, file_path: Path) -> bytes:
    for pattern, repl in GENERIC_RULES:
        def _sub(m):
            if WHITELIST_RE.search(m.group(0)):
                return m.group(0)
            findings.append(f"{file_path}: 模式 {repl.decode()}")
            return repl
        data = pattern.sub(_sub, data)
    return data


def scan_binary(path: Path, raw: bytes):
    """二进制文件只检不改：密钥嵌在 db/索引里无法安全改写，必须从包中排除

    注意：二进制扫描跳过通用 hex 规则。FTS5/SQLite 索引的内部结构会出现
    44-64 位连续 hex 字符的派生数据（已实测：源文本中不存在该串），
    保留该规则会让每个记忆索引库都报假警，进而让人习惯性忽略告警。
    真实泄露会同时命中 sk-/JWT/rt_/AYjC 这些带固定前缀的高置信度格式
    （原本包含真 Tushare token 的记忆库就同时含 sk- 密钥）。
    """
    for pattern, label in GENERIC_RULES:
        if label == b"REDACTED_HEX_TOKEN":
            continue
        for m in pattern.finditer(raw):
            if WHITELIST_RE.search(m.group(0)):
                continue
            binary_hits.append(f"{path}: 含 {label.decode()}（二进制，需从包中排除）")
            return  # 每个文件只报一次


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    root = Path(sys.argv[1]).resolve()
    check_only = "--check" in sys.argv
    if not root.is_dir():
        print(f"❌ 目录不存在: {root}")
        sys.exit(1)

    modified = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name == Path(__file__).name:
            continue

        try:
            raw = path.read_bytes()
        except OSError:
            continue

        # 二进制文件（按扩展名或含 NUL 字节）：只扇开扫描告警，不改写
        if path.suffix.lower() in BINARY_EXT or b"\x00" in raw[:8192]:
            scan_binary(path, raw)
            continue

        new = raw

        # cookies 目录整体清空
        if "cookies" in path.parts and path.suffix == ".json":
            if raw.strip() not in (b"{}", b""):
                findings.append(f"{path}: 登录态 cookie 文件")
                new = b"{}\n"
        elif path.suffix == ".json":
            try:
                obj = json.loads(raw)
                if scrub_json_obj(obj, path):
                    new = json.dumps(obj, indent=2, ensure_ascii=False).encode() + b"\n"
                new = scrub_text(new, path)
            except (json.JSONDecodeError, UnicodeDecodeError):
                new = scrub_text(raw, path)
        else:
            new = scrub_text(raw, path)

        if new != raw:
            modified += 1
            if not check_only:
                path.write_bytes(new)

    if check_only:
        if findings or binary_hits:
            print(f"❌ 检测到 {len(findings)} 处文本密钥 + {len(binary_hits)} 个含密钥的二进制文件:")
            for f in findings[:40]:
                print(f"   - {f}")
            for f in binary_hits[:20]:
                print(f"   ⚠️ {f}")
            sys.exit(1)
        print("✅ 未检测到疑似密钥（含二进制文件）")
    else:
        print(f"✅ 清洗完成: 处理 {modified} 个文件, 替换 {len(findings)} 处")
        for f in findings[:80]:
            print(f"   - {f}")
        if len(findings) > 80:
            print(f"   ... 及其他 {len(findings) - 80} 处")
        if binary_hits:
            print(f"⚠️  {len(binary_hits)} 个二进制文件含密钥，无法清洗，已列出——请删除或在打包时排除:")
            for f in binary_hits[:20]:
                print(f"   - {f}")


if __name__ == "__main__":
    main()
