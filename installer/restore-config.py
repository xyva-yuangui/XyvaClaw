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
        data['channels']['feishu'] = data.get('channels', {}).get('feishu', {})
        data['channels']['feishu']['enabled'] = True
        data['channels']['feishu']['appId'] = feishu_id
        data['channels']['feishu']['appSecret'] = {
            'source': 'env',
            'id': 'FEISHU_APP_SECRET',
        }
        data['channels']['feishu'].setdefault('domain', 'feishu')
        data['channels']['feishu'].setdefault('groupPolicy', 'allowlist')
        data['channels']['feishu'].setdefault('dmPolicy', 'allowlist')
        data['channels']['feishu'].setdefault('topicSessionMode', 'disabled')
        data['channels']['feishu'].setdefault('responseWatchdogSec', 15)
        data['channels']['feishu'].setdefault('sessionDispatchConcurrency', 5)
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

    # Update meta
    if 'meta' in data:
        data['meta']['brand'] = 'xyvaClaw'

    return data


def apply_wizard(data, wizard):
    """Apply wizard UI config to data"""
    if not wizard:
        return data

    # Assistant name (stored separately, not in openclaw.json)
    # Model providers from wizard
    if 'providers' in wizard:
        if 'models' not in data:
            data['models'] = {'mode': 'merge', 'providers': {}}
        for prov in wizard['providers']:
            name = prov.get('name', '')
            if name and prov.get('apiKey'):
                data['models']['providers'][name] = {
                    'baseUrl': prov['baseUrl'],
                    'apiKey': prov['apiKey'],
                    'api': prov.get('api', 'openai-completions'),
                    'models': prov.get('models', []),
                }

    # Channels from wizard
    if 'channels' in wizard:
        if 'channels' not in data:
            data['channels'] = {}
        for ch in wizard['channels']:
            ch_name = ch.get('type', '')
            if ch_name:
                data['channels'][ch_name] = ch.get('config', {})

    # Skills selection (used by installer, not stored in openclaw.json)

    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 restore-config.py <template.json> [.env] [wizard.json]")
        sys.exit(1)

    template_path = Path(sys.argv[1])
    env_path = sys.argv[2] if len(sys.argv) > 2 else '.env'
    wizard_path = sys.argv[3] if len(sys.argv) > 3 else ''

    if not template_path.exists():
        print(f"Error: template not found: {template_path}")
        sys.exit(1)

    data = json.loads(template_path.read_text())
    env = load_env(env_path)
    wizard = load_wizard_config(wizard_path) if wizard_path else {}

    data = apply_env(data, env)
    data = apply_wizard(data, wizard)

    output = Path('openclaw.json')
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
