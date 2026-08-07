#!/usr/bin/env python3
"""
OpenClaw 配置脱敏脚本
将 openclaw.json 中的敏感信息替换为占位符
"""
import json
import sys
import re
from pathlib import Path

SENSITIVE_KEYS = {
    'apiKey': 'YOUR_API_KEY',
    'appSecret': 'YOUR_FEISHU_APP_SECRET',
    'token': 'YOUR_GATEWAY_TOKEN',
}

# provider 上下文 → 语义化占位符（restore-config.py 按此从 .env 分别回填）
PROVIDER_PLACEHOLDERS = {
    'bailian': 'YOUR_BAILIAN_API_KEY',
    'deepseek': 'YOUR_DEEPSEEK_API_KEY',
    'wanxiang': 'YOUR_WANXIANG_API_KEY',
    'openai-codex': 'YOUR_OPENAI_API_KEY',
    'openai': 'YOUR_OPENAI_API_KEY',
    'minimax-cn': 'YOUR_MINIMAX_API_KEY',
    'kimi-coding': 'YOUR_KIMI_API_KEY',
    'qwen-portal': 'YOUR_QWEN_PORTAL_KEY',
    'amap': 'YOUR_AMAP_API_KEY',
}

# 本地回环/内网端点无需真密钥
LOCAL_PROVIDERS = {'omlx-mini2', 'ollama', 'local-mlx'}

SENSITIVE_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', 'YOUR_API_KEY'),
    (r'AYjC[a-zA-Z0-9]{28,}', 'YOUR_FEISHU_APP_SECRET'),
]

# 飞书身份 ID：不是密钥但必须因人而异。不替换会导致新用户的定时消息/主动推送
# 发到原主人的群和账号里，同时其自己的飞书应用无法通过白名单验证
IDENTITY_PATTERNS = [
    (r'cli_[a-f0-9]{16}', 'YOUR_FEISHU_APP_ID'),
    (r'ou_[a-f0-9]{32}', 'YOUR_FEISHU_OPEN_ID'),
    (r'oc_[a-f0-9]{32}', 'YOUR_FEISHU_CHAT_ID'),
]

ENV_VARS_TO_SANITIZE = [
    'XHS_COOKIE',
    'TUSHARE_TOKEN',
]


def sanitize_value(key: str, value, provider_hint: str = ''):
    """检查 key 是否需要脱敏，按 provider 上下文给语义化占位符"""
    if isinstance(value, str):
        for sensitive_key, placeholder in SENSITIVE_KEYS.items():
            if key.lower() == sensitive_key.lower() and value and value != placeholder:
                if sensitive_key == 'apiKey':
                    if provider_hint in LOCAL_PROVIDERS:
                        return 'local'
                    return PROVIDER_PLACEHOLDERS.get(provider_hint, placeholder)
                return placeholder
        for pattern, placeholder in SENSITIVE_PATTERNS:
            if re.match(pattern, value):
                return placeholder
    return value


def sanitize_obj(obj, parent_key=''):
    """递归脱敏 JSON 对象，父级 key（provider 名）作为占位符语义提示"""
    if isinstance(obj, dict):
        result = {}
        provider_hint = parent_key if (parent_key in PROVIDER_PLACEHOLDERS or parent_key in LOCAL_PROVIDERS) else ''
        hint = str(obj.get('provider', '')) or provider_hint
        for k, v in obj.items():
            result[k] = sanitize_value(k, v, hint) if isinstance(v, str) else sanitize_obj(v, k)
        return result
    elif isinstance(obj, list):
        return [sanitize_obj(item, parent_key) for item in obj]
    return obj


def sanitize_paths(obj, home_dir: str):
    """将绝对路径替换为 ~ 相对路径"""
    if isinstance(obj, str):
        return obj.replace(home_dir, '~')
    elif isinstance(obj, dict):
        return {k: sanitize_paths(v, home_dir) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_paths(item, home_dir) for item in obj]
    return obj


def sanitize_identities(obj):
    """将飞书 appId / open_id / chat_id 替换为占位符（逐字符串正则）"""
    if isinstance(obj, str):
        out = obj
        for pattern, placeholder in IDENTITY_PATTERNS:
            out = re.sub(pattern, placeholder, out)
        return out
    elif isinstance(obj, dict):
        return {k: sanitize_identities(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_identities(item) for item in obj]
    return obj


def main():
    if len(sys.argv) < 3:
        print("用法: python3 sanitize-config.py <input.json> <output.json>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        sys.exit(1)

    data = json.loads(input_path.read_text())
    home_dir = str(Path.home())

    # 脱敏敏感信息
    data = sanitize_obj(data)

    # 飞书身份 ID → 占位符
    data = sanitize_identities(data)

    # 替换绝对路径
    data = sanitize_paths(data, home_dir)

    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

    print(f"✅ 脱敏完成: {output_path}")
    print(f"   已替换: apiKey, appSecret, token")
    print(f"   已替换: 飞书 appId / open_id / chat_id → 占位符")
    print(f"   已替换: 绝对路径 → ~")


if __name__ == '__main__':
    main()
