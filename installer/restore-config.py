#!/usr/bin/env python3
"""
xyvaClaw 配置恢复脚本
从模板 + 用户 .env / wizard JSON 生成完整 openclaw.json
"""
import json
import os
import sys
import secrets
from pathlib import Path


def load_env(env_path):
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
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def load_wizard_config(wizard_path):
    path = Path(wizard_path)
    if path.exists():
        return json.loads(path.read_text())
    return {}


def restore_paths(obj, home_dir):
    if isinstance(obj, str):
        if obj.startswith('~/') or obj == '~':
            return obj.replace('~', home_dir, 1)
        return obj
    elif isinstance(obj, dict):
        return {k: restore_paths(v, home_dir) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [restore_paths(item, home_dir) for item in obj]
    return obj


def apply_env(data, env):
    """Apply environment variables to config template"""
    home_dir = str(Path.home())

    # DeepSeek
    deepseek_key = env.get('DEEPSEEK_API_KEY', '')
    if deepseek_key and 'models' in data and 'providers' in data['models']:
        providers = data['models']['providers']
        if 'deepseek' in providers:
            providers['deepseek']['apiKey'] = deepseek_key
        else:
            providers['deepseek'] = {
                'baseUrl': 'https://api.deepseek.com/v1',
                'apiKey': deepseek_key,
                'api': 'openai-completions',
                'models': [
                    {
                        'id': 'deepseek-chat',
                        'name': 'DeepSeek V3.2',
                        'reasoning': False,
                        'input': ['text'],
                        'contextWindow': 128000,
                        'maxTokens': 65536,
                    },
                    {
                        'id': 'deepseek-reasoner',
                        'name': 'DeepSeek Reasoner',
                        'reasoning': True,
                        'input': ['text'],
                        'contextWindow': 128000,
                        'maxTokens': 65536,
                    },
                ],
            }

    # Bailian
    bailian_key = env.get('BAILIAN_API_KEY', '')
    if bailian_key and 'models' in data and 'providers' in data['models']:
        providers = data['models']['providers']
        if 'bailian' in providers:
            providers['bailian']['apiKey'] = bailian_key

    # Custom providers from .env
    custom_count = int(env.get('CUSTOM_PROVIDER_COUNT', '0') or '0')
    if custom_count > 0:
        if 'models' not in data:
            data['models'] = {'mode': 'merge', 'providers': {}}
        for i in range(custom_count):
            cp_name = env.get(f'CUSTOM_PROVIDER_{i}_NAME', '')
            cp_url = env.get(f'CUSTOM_PROVIDER_{i}_URL', '')
            cp_key = env.get(f'CUSTOM_PROVIDER_{i}_KEY', '')
            cp_models_str = env.get(f'CUSTOM_PROVIDER_{i}_MODELS', '')
            if cp_name and cp_key:
                models = []
                if cp_models_str:
                    for mid in cp_models_str.split(','):
                        mid = mid.strip()
                        if mid:
                            models.append({
                                'id': mid,
                                'name': mid,
                                'reasoning': False,
                                'input': ['text'],
                                'contextWindow': 128000,
                                'maxTokens': 4096,
                            })
                data['models']['providers'][cp_name] = {
                    'baseUrl': cp_url,
                    'apiKey': cp_key,
                    'api': 'openai-completions',
                    'models': models,
                }

    # Remove providers with no key
    if 'models' in data and 'providers' in data['models']:
        to_remove = []
        for name, prov in data['models']['providers'].items():
            key = prov.get('apiKey', '')
            if not key or key.startswith('__'):
                to_remove.append(name)
        for name in to_remove:
            del data['models']['providers'][name]

    # Fix primary/fallback model if provider was removed
    available_models = []
    if 'models' in data and 'providers' in data['models']:
        for pname, prov in data['models']['providers'].items():
            for m in prov.get('models', []):
                available_models.append(f"{pname}/{m['id']}")

    if available_models and 'agents' in data and 'defaults' in data['agents']:
        defaults = data['agents']['defaults']
        if 'model' in defaults:
            primary = defaults['model'].get('primary', '')
            if primary not in available_models:
                defaults['model']['primary'] = available_models[0]
            fallbacks = defaults['model'].get('fallbacks', [])
            defaults['model']['fallbacks'] = [f for f in fallbacks if f in available_models]

    # Feishu channel
    feishu_id = env.get('FEISHU_APP_ID', '')
    feishu_secret = env.get('FEISHU_APP_SECRET', '')
    if feishu_id and feishu_secret:
        if 'channels' not in data:
            data['channels'] = {}
        feishu_conf = data.get('channels', {}).get('feishu', {})
        feishu_conf['enabled'] = True
        feishu_conf.setdefault('domain', 'feishu')
        feishu_conf.setdefault('connectionMode', 'websocket')
        feishu_conf.setdefault('dmPolicy', 'pairing')
        feishu_conf.setdefault('groupPolicy', 'allowlist')
        feishu_conf.setdefault('requireMention', True)
        # Use accounts format (official recommended)
        if 'accounts' not in feishu_conf:
            feishu_conf['accounts'] = {}
        feishu_conf['accounts'].setdefault('main', {})
        feishu_conf['accounts']['main']['appId'] = feishu_id
        feishu_conf['accounts']['main']['appSecret'] = feishu_secret
        # Remove legacy top-level credentials if present
        feishu_conf.pop('appId', None)
        feishu_conf.pop('appSecret', None)
        data['channels']['feishu'] = feishu_conf
    else:
        # No feishu credentials, disable channel
        if 'channels' in data and 'feishu' in data['channels']:
            data['channels']['feishu']['enabled'] = False

    # Gateway
    gw_port = env.get('GATEWAY_PORT', '18789')
    gw_token = env.get('GATEWAY_TOKEN', '') or secrets.token_hex(24)
    if 'gateway' in data:
        data['gateway']['port'] = int(gw_port)
        data['gateway']['auth']['token'] = gw_token

    # Restore paths
    data = restore_paths(data, home_dir)

    # Fix meta: OpenClaw 2026.3.x only accepts lastTouchedVersion/lastTouchedAt
    import datetime
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    data['meta'] = {
        'lastTouchedVersion': '2026.3.13',
        'lastTouchedAt': now_utc,
    }

    # Ensure wizard section exists (required for gateway to not show 'Missing config')
    if 'wizard' not in data:
        data['wizard'] = {
            'lastRunAt': now_utc,
            'lastRunVersion': '2026.3.13',
            'lastRunCommand': 'setup',
            'lastRunMode': 'local',
        }

    # Preserve plugins from template, dynamically toggle feishu based on config
    if 'plugins' not in data:
        data['plugins'] = {'allow': [], 'slots': {}, 'entries': {}}
    # Ensure lossless-claw is always enabled
    allow_list = data.get('plugins', {}).get('allow', [])
    if 'lossless-claw' not in allow_list:
        data.setdefault('plugins', {}).setdefault('allow', []).append('lossless-claw')
    # Toggle feishu_local based on whether feishu channel is configured
    feishu_enabled = data.get('channels', {}).get('feishu', {}).get('enabled', False)
    if feishu_enabled:
        if 'feishu_local' not in allow_list:
            allow_list.append('feishu_local')
        data['plugins'].setdefault('entries', {})['feishu_local'] = {'enabled': True}
    data['plugins']['allow'] = allow_list

    return data


def apply_wizard(data, wizard):
    """Apply wizard UI config to data"""
    if not wizard:
        return data

    # Assistant name (stored separately, not in openclaw.json)
    # Model providers from wizard
    # wizard['providers'] is a dict: {deepseek: {enabled, apiKey, ...}, bailian: {...}, custom: [...]}
    if 'providers' in wizard and isinstance(wizard['providers'], dict):
        if 'models' not in data:
            data['models'] = {'mode': 'merge', 'providers': {}}
        wp = wizard['providers']

        # Built-in providers (deepseek, bailian, etc.)
        BUILTIN_PROVIDER_META = {
            'deepseek': {
                'baseUrl': 'https://api.deepseek.com/v1',
                'api': 'openai-completions',
                'models': [
                    {'id': 'deepseek-chat', 'name': 'DeepSeek V3.2', 'reasoning': False,
                     'input': ['text'], 'contextWindow': 128000, 'maxTokens': 65536},
                    {'id': 'deepseek-reasoner', 'name': 'DeepSeek Reasoner', 'reasoning': True,
                     'input': ['text'], 'contextWindow': 128000, 'maxTokens': 65536},
                ],
            },
            'bailian': {
                'baseUrl': 'https://coding.dashscope.aliyuncs.com/v1',
                'api': 'openai-completions',
                'models': [
                    {'id': 'qwen3.5-plus', 'name': 'qwen3.5-plus', 'reasoning': False,
                     'input': ['text', 'image'], 'contextWindow': 1000000, 'maxTokens': 65536,
                     'compat': {'thinkingFormat': 'qwen'}},
                    {'id': 'qwen3-max-2026-01-23', 'name': 'qwen3-max-2026-01-23', 'reasoning': False,
                     'input': ['text'], 'contextWindow': 262144, 'maxTokens': 65536,
                     'compat': {'thinkingFormat': 'qwen'}},
                    {'id': 'qwen3-coder-next', 'name': 'qwen3-coder-next', 'reasoning': False,
                     'input': ['text'], 'contextWindow': 262144, 'maxTokens': 65536},
                    {'id': 'qwen3-coder-plus', 'name': 'qwen3-coder-plus', 'reasoning': False,
                     'input': ['text'], 'contextWindow': 1000000, 'maxTokens': 65536},
                    {'id': 'MiniMax-M2.5', 'name': 'MiniMax-M2.5', 'reasoning': False,
                     'input': ['text'], 'contextWindow': 196608, 'maxTokens': 32768},
                    {'id': 'glm-5', 'name': 'glm-5', 'reasoning': False,
                     'input': ['text'], 'contextWindow': 202752, 'maxTokens': 16384,
                     'compat': {'thinkingFormat': 'qwen'}},
                    {'id': 'glm-4.7', 'name': 'glm-4.7', 'reasoning': False,
                     'input': ['text'], 'contextWindow': 202752, 'maxTokens': 16384,
                     'compat': {'thinkingFormat': 'qwen'}},
                    {'id': 'kimi-k2.5', 'name': 'kimi-k2.5', 'reasoning': False,
                     'input': ['text', 'image'], 'contextWindow': 262144, 'maxTokens': 32768,
                     'compat': {'thinkingFormat': 'qwen'}},
                ],
            },
        }

        for name, meta in BUILTIN_PROVIDER_META.items():
            prov_conf = wp.get(name)
            if isinstance(prov_conf, dict) and prov_conf.get('enabled') and prov_conf.get('apiKey'):
                existing = data['models']['providers'].get(name, {})
                data['models']['providers'][name] = {
                    'baseUrl': existing.get('baseUrl', meta['baseUrl']),
                    'apiKey': prov_conf['apiKey'],
                    'api': existing.get('api', meta['api']),
                    'models': existing.get('models', meta['models']),
                }

        # Custom providers (list of {name, baseUrl, apiKey})
        for cp in wp.get('custom', []):
            if isinstance(cp, dict):
                name = cp.get('name', '')
                if name and cp.get('apiKey'):
                    data['models']['providers'][name] = {
                        'baseUrl': cp.get('baseUrl', ''),
                        'apiKey': cp['apiKey'],
                        'api': cp.get('api', 'openai-completions'),
                        'models': cp.get('models', []),
                    }

    # Channels from wizard
    # wizard['channels'] is a dict: {feishu: {enabled, appId, ...}, dingtalk: {...}, webchat: {...}}
    if 'channels' in wizard and isinstance(wizard['channels'], dict):
        if 'channels' not in data:
            data['channels'] = {}
        for ch_name, ch_conf in wizard['channels'].items():
            if isinstance(ch_conf, dict) and ch_conf.get('enabled'):
                existing = data['channels'].get(ch_name, {})
                existing.update(ch_conf)
                data['channels'][ch_name] = existing

    # Skills selection (used by installer, not stored in openclaw.json)

    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 restore-config.py <template.json> [.env] [wizard.json] [--output-dir <dir>]")
        sys.exit(1)

    # Parse --output-dir from argv
    output_dir = None
    args = list(sys.argv[1:])
    if '--output-dir' in args:
        idx = args.index('--output-dir')
        if idx + 1 < len(args):
            output_dir = args[idx + 1]
            args = args[:idx] + args[idx + 2:]

    template_path = Path(args[0])
    env_path = args[1] if len(args) > 1 else '.env'
    wizard_path = args[2] if len(args) > 2 else ''

    if not template_path.exists():
        # Fallback: try config-base/ relative to this script's repo location
        script_dir = Path(__file__).resolve().parent
        fallback = script_dir.parent / 'config-base' / 'openclaw.json.template'
        if fallback.exists():
            print(f"Template not found at {template_path}, using fallback: {fallback}")
            template_path = fallback
        else:
            print(f"Error: template not found: {template_path}")
            print(f"  (also checked fallback: {fallback})")
            sys.exit(1)

    data = json.loads(template_path.read_text())
    env = load_env(env_path)
    wizard = load_wizard_config(wizard_path) if wizard_path else {}

    data = apply_env(data, env)
    data = apply_wizard(data, wizard)

    # Output to .openclaw/ nested directory (OpenClaw 2026.3.x convention)
    if output_dir:
        out_base = Path(output_dir)
    else:
        out_base = Path('.openclaw')
    out_base.mkdir(parents=True, exist_ok=True)
    output = out_base / 'openclaw.json'
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    print(f"Config generated: {output}")

    # Check for missing keys
    content = output.read_text()
    missing = []
    if '__API_KEY__' in content:
        missing.append('API keys not configured')
    if '__APP_ID__' in content:
        missing.append('Feishu App ID not configured')
    if '__APP_SECRET__' in content:
        missing.append('Feishu App Secret not configured')
    if missing:
        for m in missing:
            print(f"  Warning: {m}")

    # Count configured providers
    providers = data.get('models', {}).get('providers', {})
    print(f"  Providers: {len(providers)} configured")
    for name in providers:
        models = providers[name].get('models', [])
        print(f"    - {name}: {len(models)} models")


if __name__ == '__main__':
    main()
