#!/usr/bin/env python3
"""
xyvaClaw 深度脱敏脚本
从 Desktop/openclaw 生成纯净分发版 config-base
比原 sanitize-config.py 更彻底：移除所有个人数据、ID、会话、记忆
"""
import json
import sys
import re
import os
import shutil
from pathlib import Path

# ---- 脱敏规则 ----

SENSITIVE_KEY_PATTERNS = {
    'apiKey': '__API_KEY__',
    'appSecret': '__APP_SECRET__',
    'token': '__TOKEN__',
    'appId': '__APP_ID__',
}

SENSITIVE_VALUE_PATTERNS = [
    (r'sk-[a-zA-Z0-9_-]{20,}', '__API_KEY__'),
    (r'cli_[a-zA-Z0-9]{16,}', '__APP_ID__'),
    (r'AYjC[a-zA-Z0-9]{28,}', '__APP_SECRET__'),
    (r'ou_[a-zA-Z0-9]{32,}', '__OPEN_ID__'),
    (r'oc_[a-zA-Z0-9]{32,}', '__GROUP_ID__'),
    (r'[a-f0-9]{40,}', '__TOKEN__'),
]

# 需要完全移除的顶层字段
REMOVE_TOPLEVEL = ['wizard', 'auth']

# 需要清空的 channels 子字段
CHANNEL_CLEAR_FIELDS = ['allowFrom', 'groupAllowFrom', 'docEditorOpenIds']


def sanitize_value(key, value):
    if not isinstance(value, str) or not value:
        return value
    for sensitive_key, placeholder in SENSITIVE_KEY_PATTERNS.items():
        if key.lower() == sensitive_key.lower() and value != placeholder:
            return placeholder
    for pattern, placeholder in SENSITIVE_VALUE_PATTERNS:
        if re.fullmatch(pattern, value):
            return placeholder
    return value


def sanitize_obj(obj, parent_key=''):
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if isinstance(v, str):
                result[k] = sanitize_value(k, v)
            else:
                result[k] = sanitize_obj(v, k)
        return result
    elif isinstance(obj, list):
        return [sanitize_obj(item, parent_key) for item in obj]
    return obj


def sanitize_paths(obj, home_dir):
    if isinstance(obj, str):
        return obj.replace(home_dir, '~')
    elif isinstance(obj, dict):
        return {k: sanitize_paths(v, home_dir) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_paths(item, home_dir) for item in obj]
    return obj


def clean_config(data):
    """深度清理 openclaw.json"""
    # 移除个人化顶层字段
    for key in REMOVE_TOPLEVEL:
        data.pop(key, None)

    # 清理 meta
    if 'meta' in data:
        data['meta'] = {
            'brand': 'xyvaClaw',
            'version': '1.0.0',
            'basedOn': data['meta'].get('lastTouchedVersion', 'unknown'),
        }

    # 脱敏所有敏感值
    data = sanitize_obj(data)

    # 清理 channels 中的个人 ID 列表
    if 'channels' in data:
        for ch_name, ch_conf in data['channels'].items():
            if isinstance(ch_conf, dict):
                for field in CHANNEL_CLEAR_FIELDS:
                    if field in ch_conf:
                        ch_conf[field] = []
                # appId 和 appSecret 用占位符
                if 'appId' in ch_conf:
                    ch_conf['appId'] = '__APP_ID__'

    # 清理 gateway token
    if 'gateway' in data and 'auth' in data['gateway']:
        data['gateway']['auth']['token'] = '__AUTO_GENERATE__'

    # 清理 plugins summaryModel（保留结构，值用占位符）
    # 实际这个值是 model ref 不是 secret，保留即可

    return data


def build_config_base(source_dir, output_dir):
    """从源目录构建纯净 config-base"""
    source = Path(source_dir)
    output = Path(output_dir)

    print(f"[1/8] 处理 openclaw.json...")
    config_path = source / 'openclaw.json'
    if config_path.exists():
        data = json.loads(config_path.read_text())
        home_dir = str(Path.home())
        data = clean_config(data)
        data = sanitize_paths(data, home_dir)
        out_path = output / 'openclaw.json.template'
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
        print(f"   -> {out_path}")

    print(f"[2/8] 复制 config/...")
    src_config = source / 'config'
    dst_config = output / 'config'
    if src_config.exists():
        dst_config.mkdir(parents=True, exist_ok=True)
        for f in src_config.glob('*.json'):
            shutil.copy2(f, dst_config / f.name)
            print(f"   -> {f.name}")

    print(f"[3/8] 复制 agents/ (去除 sessions, 脱敏 JSON)...")
    src_agents = source / 'agents'
    dst_agents = output / 'agents'
    if src_agents.exists():
        for agent_dir in src_agents.iterdir():
            if agent_dir.is_dir():
                agent_conf = agent_dir / 'agent'
                if agent_conf.exists():
                    dst_agent = dst_agents / agent_dir.name / 'agent'
                    dst_agent.mkdir(parents=True, exist_ok=True)
                    for f in agent_conf.glob('*.json'):
                        # Sanitize agent JSON files too
                        try:
                            agent_data = json.loads(f.read_text())
                            agent_data = sanitize_obj(agent_data)
                            (dst_agent / f.name).write_text(
                                json.dumps(agent_data, indent=2, ensure_ascii=False) + '\n'
                            )
                        except (json.JSONDecodeError, UnicodeDecodeError):
                            shutil.copy2(f, dst_agent / f.name)
                        print(f"   -> agents/{agent_dir.name}/agent/{f.name}")

    print(f"[4/8] 复制 extensions/...")
    src_ext = source / 'extensions'
    dst_ext = output / 'extensions'
    if src_ext.exists():
        for ext_dir in src_ext.iterdir():
            if ext_dir.is_dir() and ext_dir.name != '.openclaw-install-backups':
                dst_ext_dir = dst_ext / ext_dir.name
                # rsync-like copy excluding node_modules
                shutil.copytree(
                    ext_dir, dst_ext_dir,
                    ignore=shutil.ignore_patterns(
                        'node_modules', '*.broken.*', '.DS_Store'
                    ),
                    dirs_exist_ok=True
                )
                print(f"   -> extensions/{ext_dir.name}/")

    print(f"[5/8] 复制 workspace 核心文件...")
    src_ws = source / 'workspace'
    dst_ws = output / 'workspace'
    dst_ws.mkdir(parents=True, exist_ok=True)

    # 保留的核心 MD 文件（模板化）
    keep_md = ['BOOT.md', 'HEARTBEAT.md', 'TOOLS.md', 'WORKFLOW_AUTO.md', 'README.md']
    for md in keep_md:
        src_f = src_ws / md
        if src_f.exists():
            shutil.copy2(src_f, dst_ws / md)
            print(f"   -> workspace/{md}")

    # .gitignore
    gi = src_ws / '.gitignore'
    if gi.exists():
        shutil.copy2(gi, dst_ws / '.gitignore')

    print(f"[6/8] 复制 skills/...")
    src_skills = src_ws / 'skills'
    dst_skills = dst_ws / 'skills'
    if src_skills.exists():
        SKIP_SKILLS = {'_archived', '_incomplete', 'output'}
        for skill_dir in sorted(src_skills.iterdir()):
            if skill_dir.is_dir() and skill_dir.name not in SKIP_SKILLS:
                dst_skill = dst_skills / skill_dir.name
                shutil.copytree(
                    skill_dir, dst_skill,
                    ignore=shutil.ignore_patterns(
                        'node_modules', '__pycache__', '.venv',
                        '*.pyc', '.DS_Store', 'output', '.cache',
                        'runtime', 'sessions', 'TEST-RESULTS-*',
                    ),
                    dirs_exist_ok=True
                )
                print(f"   -> skills/{skill_dir.name}/")

    print(f"[7/8] 复制运维脚本...")
    src_scripts = source / 'scripts'
    dst_scripts = output / 'scripts'
    if src_scripts.exists():
        dst_scripts.mkdir(parents=True, exist_ok=True)
        for f in src_scripts.glob('*.sh'):
            shutil.copy2(f, dst_scripts / f.name)
            print(f"   -> scripts/{f.name}")

    print(f"[8/8] 复制 completions/...")
    src_comp = source / 'completions'
    dst_comp = output / 'completions'
    if src_comp.exists():
        dst_comp.mkdir(parents=True, exist_ok=True)
        for f in src_comp.iterdir():
            if f.is_file():
                shutil.copy2(f, dst_comp / f.name)
                print(f"   -> completions/{f.name}")

    # [9/8] Post-process: replace hardcoded home paths in all text files
    print(f"[9/8] 替换硬编码路径...")
    home_dir = str(Path.home())
    username = Path.home().name
    TEXT_EXTS = {'.py', '.sh', '.md', '.mjs', '.json', '.ts', '.yaml', '.yml', '.txt'}
    replaced_count = 0
    for fpath in output.rglob('*'):
        if fpath.is_file() and fpath.suffix in TEXT_EXTS:
            try:
                content = fpath.read_text(errors='replace')
                original = content
                # Replace specific paths first, then generic
                content = content.replace(f'{home_dir}/.openclaw', '~/.xyvaclaw')
                content = content.replace(f'{home_dir}/.config/clawdbot', '~/.config/clawdbot')
                content = content.replace(home_dir, '~')
                if content != original:
                    fpath.write_text(content)
                    replaced_count += 1
            except Exception:
                pass
    print(f"   -> {replaced_count} 个文件中的路径已替换")

    print("\n=============================")
    print("Done! config-base is ready.")

    # 统计
    total_files = sum(1 for _ in output.rglob('*') if _.is_file())
    total_size = sum(f.stat().st_size for f in output.rglob('*') if f.is_file())
    print(f"Total files: {total_files}")
    print(f"Total size: {total_size / 1024 / 1024:.1f} MB")


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 sanitize-for-distribution.py <source_dir> <output_dir>")
        print("  source_dir: path to Desktop/openclaw (or ~/.openclaw)")
        print("  output_dir: path to xyvaclaw/config-base")
        sys.exit(1)

    source_dir = sys.argv[1]
    output_dir = sys.argv[2]

    if not Path(source_dir).exists():
        print(f"Error: source not found: {source_dir}")
        sys.exit(1)

    build_config_base(source_dir, output_dir)


if __name__ == '__main__':
    main()
