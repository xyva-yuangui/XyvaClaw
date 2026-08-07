#!/usr/bin/env python3
"""
OpenClaw 配置恢复脚本
从脱敏的 openclaw.json + .env 恢复完整配置

用法:
    python3 restore-config.py <sanitized.json> [.env文件路径] [--package <打包目录>]

    --package: 同时恢复打包目录内 agents/*/agent/*.json 和
               workspace/config/tushare.json 中的占位符（就地写回）
"""
import json
import os
import sys
import secrets
from pathlib import Path

# 占位符 → .env 变量名
PLACEHOLDER_ENV_MAP = {
    'YOUR_API_KEY': 'BAILIAN_API_KEY',  # 兼容旧版占位符
    'YOUR_BAILIAN_API_KEY': 'BAILIAN_API_KEY',
    'YOUR_DEEPSEEK_API_KEY': 'DEEPSEEK_API_KEY',
    'YOUR_WANXIANG_API_KEY': 'WANXIANG_API_KEY',
    'YOUR_OPENAI_API_KEY': 'OPENAI_API_KEY',
    'YOUR_MINIMAX_API_KEY': 'MINIMAX_API_KEY',
    'YOUR_KIMI_API_KEY': 'KIMI_API_KEY',
    'YOUR_QWEN_PORTAL_KEY': 'QWEN_PORTAL_KEY',
    'YOUR_AMAP_API_KEY': 'AMAP_API_KEY',
    'YOUR_FEISHU_APP_SECRET': 'FEISHU_APP_SECRET',
    'YOUR_FEISHU_APP_ID': 'FEISHU_APP_ID',
    'YOUR_FEISHU_OPEN_ID': 'FEISHU_OPEN_ID',
    'YOUR_FEISHU_CHAT_ID': 'FEISHU_CHAT_ID',
    'YOUR_TUSHARE_TOKEN': 'TUSHARE_TOKEN',
}

# OAuth 类占位符无法从 .env 恢复，需在目标机重新登录
OAUTH_PLACEHOLDERS = ('REDACTED_OAUTH_ACCESS', 'REDACTED_OAUTH_REFRESH', 'REDACTED_JWT')

missing_env = set()
oauth_hits = set()


def load_env(env_path: str) -> dict:
    """加载 .env 文件（未修改的模板占位值视为未填写）"""
    env = {}
    path = Path(env_path)
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            key, _, value = line.partition('=')
            value = value.strip().strip('"').strip("'")
            # 过滤模板占位值，避免用户未编辑 .env 时将占位符当真密钥写入
            if value and ('your-' in value.lower() or value.lower().endswith('-here')):
                continue
            env[key.strip()] = value
    return env


def restore_paths(obj, home_dir: str):
    """将 ~ 路径替换为当前用户的 home 目录"""
    if isinstance(obj, str):
        if obj.startswith('~/') or obj == '~':
            return obj.replace('~', home_dir, 1)
        return obj
    elif isinstance(obj, dict):
        return {k: restore_paths(v, home_dir) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [restore_paths(item, home_dir) for item in obj]
    return obj


def _restore_str(value: str, env: dict, source: str) -> str:
    """单个字符串的占位符替换（dict 值和 list 元素共用）"""
    if value in PLACEHOLDER_ENV_MAP:
        env_key = PLACEHOLDER_ENV_MAP[value]
        if env.get(env_key):
            return env[env_key]
        missing_env.add(env_key)
        return value
    if value == 'YOUR_GATEWAY_TOKEN':
        return secrets.token_hex(24)
    if value in OAUTH_PLACEHOLDERS:
        oauth_hits.add(source or '(main config)')
    return value


def restore_secrets(obj, env: dict, source: str = ''):
    """从 .env 恢复敏感信息（递归处理 dict / list / 裸字符串）"""
    if isinstance(obj, dict):
        return {k: (_restore_str(v, env, source) if isinstance(v, str)
                    else restore_secrets(v, env, source))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [(_restore_str(i, env, source) if isinstance(i, str)
                 else restore_secrets(i, env, source))
                for i in obj]
    if isinstance(obj, str):
        return _restore_str(obj, env, source)
    return obj


def restore_package_files(package_dir: Path, env: dict, home_dir: str):
    """恢复打包目录内 agents 配置、tushare.json 和飞书身份占位符（就地写回）"""
    targets = list(package_dir.glob('agents/*/agent/auth-profiles.json'))
    targets += list(package_dir.glob('agents/*/agent/models.json'))
    tushare = package_dir / 'workspace' / 'config' / 'tushare.json'
    if tushare.exists():
        targets.append(tushare)

    for path in targets:
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            print(f"  ⚠️ 跳过（无法解析）: {path}")
            continue
        data = restore_paths(data, home_dir)
        data = restore_secrets(data, env, source=str(path.relative_to(package_dir)))
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
        print(f"  ✅ 已恢复: {path.relative_to(package_dir)}")

    restore_feishu_identities(package_dir, env)


# 含飞书身份占位符的功能文件（相对打包目录）
FEISHU_ID_FILES = [
    'cron/jobs.json',
    'cron/self-reflect.json',
    'cron/self-reflect-pm.json',
    'workspace/config/v12-cluster.json',
    'workspace/config/v15-cluster.json',
    'workspace/config/task-monitor-config.json',
    'workspace/config/feishu_channel.json',
    'workspace/skills/content-studio/config/default.json',
    'workspace/skills/seedance-video/config/default.json',
]


def restore_feishu_identities(package_dir: Path, env: dict):
    """把功能文件中的飞书身份占位符换成用户自己的 ID（纯文本替换）"""
    mapping = {
        'YOUR_FEISHU_APP_ID': env.get('FEISHU_APP_ID', ''),
        'YOUR_FEISHU_OPEN_ID': env.get('FEISHU_OPEN_ID', ''),
        'YOUR_FEISHU_CHAT_ID': env.get('FEISHU_CHAT_ID', ''),
    }
    unfilled = [k for k, v in mapping.items() if not v]
    done = 0
    present = set()          # 包内确实存在的占位符
    for rel in FEISHU_ID_FILES:
        path = package_dir / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text()
        except OSError:
            continue
        for ph in mapping:
            if ph in text:
                present.add(ph)
        new = text
        for ph, real in mapping.items():
            if real:
                new = new.replace(ph, real)
        if new != text:
            path.write_text(new)
            done += 1
    if done:
        print(f"  ✅ 已将飞书身份写入 {done} 个文件")
    # 只对包内真存在的占位符告警。社区版不含飞书集成，
    # 无条件告警会让用户以为少配了东西。
    missing = [u for u in unfilled if u in present]
    if missing:
        print(f"  ⚠️ 以下飞书配置未填，定时推送/权限白名单将不生效: {', '.join(PLACEHOLDER_ENV_MAP[u] for u in missing)}")
        print("     获取方式: 飞书开放平台看 appId；向机器人发 /whoami 或看日志取自己的 open_id；群聊里 @机器人取 chat_id")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    package_dir = None
    if '--package' in sys.argv:
        idx = sys.argv.index('--package')
        if idx + 1 < len(sys.argv):
            package_dir = Path(sys.argv[idx + 1])
            args = [a for a in args if a != sys.argv[idx + 1]]

    if not args:
        print(__doc__)
        sys.exit(1)

    input_path = Path(args[0])
    env_path = args[1] if len(args) > 1 else '.env'

    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        sys.exit(1)

    data = json.loads(input_path.read_text())
    home_dir = str(Path.home())
    env = load_env(env_path)

    # 恢复路径
    data = restore_paths(data, home_dir)

    # 恢复密钥
    data = restore_secrets(data, env)

    # 输出
    output_path = Path('openclaw.json')
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

    print(f"✅ 配置恢复完成: {output_path}")

    # 恢复打包目录内其他配置文件
    if package_dir and package_dir.is_dir():
        print(f"🔧 恢复打包目录配置: {package_dir}")
        restore_package_files(package_dir, env, home_dir)

    if missing_env:
        print(f"⚠️  以下密钥未填写（请在 .env 中配置）: {', '.join(sorted(missing_env))}")
    if oauth_hits:
        print("⚠️  以下文件包含 OAuth 凭证占位符，需在目标机重新登录:")
        for s in sorted(oauth_hits):
            print(f"   - {s}")
        print("   执行: openclaw models auth login --provider openai-codex / qwen-portal")

    # ── 配置合法性校验（防止非法字段导致 gateway 崩溃）──
    LEGAL_TOP_KEYS = {
        "meta", "wizard", "auth", "models", "agents", "messages",
        "commands", "session", "channels", "gateway", "plugins",
    }
    illegal = [k for k in data.keys() if k not in LEGAL_TOP_KEYS]
    if illegal:
        print(f"❌ 检测到非法顶层字段: {illegal}")
        print(f"   gateway 会拒绝启动！请删除这些字段后再使用。")
        print(f"   合法字段: {sorted(LEGAL_TOP_KEYS)}")
        sys.exit(1)
    else:
        print(f"✅ 配置字段验证通过（无非法顶层字段）")


if __name__ == '__main__':
    main()
