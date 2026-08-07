---
name: code-runner
description: Execute Python code, Shell commands, and pytest tests in a sandboxed environment. Returns structured results with stdout, stderr, exit_code, and timing. Use when writing/testing/debugging code, running scripts, or validating code snippets. Supports --lang python/shell/test, --timeout, --workdir.
version: 1.0.0
category: coding
---

# Code Runner

沙盒执行 Python / Shell 代码，返回结构化结果（stdout / stderr / exit_code / 耗时）。

## 安装依赖

```bash
pip install pytest  # 可选，用于测试模式
```

## 用法

### Python 代码执行
```bash
python3 ~/.openclaw/workspace/skills/code-runner/scripts/run_code.py \
  --lang python --code "print(sum(range(10)))"
```

### Shell 命令执行
```bash
python3 ~/.openclaw/workspace/skills/code-runner/scripts/run_code.py \
  --lang shell --code "ls -la && df -h"
```

### 执行文件
```bash
python3 ~/.openclaw/workspace/skills/code-runner/scripts/run_code.py \
  --lang python --file /path/to/script.py --timeout 60
```

### 测试模式（pytest）
```bash
python3 ~/.openclaw/workspace/skills/code-runner/scripts/run_code.py \
  --lang test --code "
def test_add():
    assert 1 + 1 == 2
def test_fail():
    assert 1 + 1 == 3
"
```

### JSON 输出（适合管道）
```bash
python3 run_code.py --lang python --code "import sys; print(sys.version)" --json
```

## 参数

| 参数 | 说明 | 默认 |
|---|---|---|
| `--lang` | python / shell / test | python |
| `--code` | 内联代码字符串 | - |
| `--file` | 代码文件路径 | - |
| `--timeout` | 超时秒数 | 30 |
| `--workdir` | 工作目录 | ~/  |
| `--env` | 环境变量 JSON | - |
| `--save` | 保存结果到文件 | - |
| `--json` | JSON 格式输出 | - |

## 返回结构

```json
{
  "lang": "python",
  "exit_code": 0,
  "stdout": "输出内容",
  "stderr": "",
  "success": true,
  "elapsed_ms": 125,
  "timestamp": "2026-03-31T10:00:00"
}
```

## 注意事项

- Shell 命令使用 `/bin/zsh` 执行
- 代码在独立进程中运行，不影响 OpenClaw 主进程
- stdout 最大输出 10000 字符，超出自动截断
- 测试模式需要安装 `pytest`
