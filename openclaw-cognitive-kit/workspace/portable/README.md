# OpenClaw 一键安装包

> 将你的 AI 助手复制到任何电脑

## 快速开始

### 打包（在源电脑上）
```bash
bash ~/.openclaw/workspace/portable/openclaw-pack.sh
```
输出：`~/Desktop/openclaw-portable-YYYYMMDD_HHMMSS.tar.gz`

### 安装（在目标电脑上）
```bash
# 1. 解压
tar -xzf openclaw-portable-*.tar.gz
cd openclaw-portable-*

# 2. 填写密钥
cp .env.template .env
nano .env  # 填写 BAILIAN_API_KEY 和 FEISHU_APP_SECRET

# 3. 安装
# Mac:
bash openclaw-install.sh

# Linux (Ubuntu/Debian):
bash openclaw-install-linux.sh
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `openclaw-pack.sh` | 打包脚本（在源电脑运行） |
| `openclaw-install.sh` | Mac 安装脚本 |
| `openclaw-install-linux.sh` | Linux 安装脚本 |
| `sanitize-config.py` | 配置脱敏（打包时自动调用） |
| `restore-config.py` | 配置恢复（安装时自动调用） |
| `.env.template` | 密钥模板 |

## 打包内容

✅ 包含：
- `openclaw.json`（脱敏版，密钥替换为占位符）
- `workspace/`（AGENTS.md, TOOLS.md, skills 等）
- `agents/`（多角色配置）
- `cron/`（定时任务）
- 多角色 workspace（workspace-quant-analyst 等）

❌ 不包含（每台机器独立）：
- `node_modules/`（安装时自动下载）
- `cache/`（运行时自动生成）
- `sessions/`（会话历史）
- `logs/`（日志）
- `browser/`（Chrome 扩展）
- `*.sqlite`（语义索引，启动时自动构建）

## 密钥清单

| 密钥 | 必填 | 来源 |
|------|------|------|
| BAILIAN_API_KEY | ✅ | 阿里云百炼平台 |
| FEISHU_APP_SECRET | ✅ | 飞书开放平台 |
| XHS_COOKIE | ❌ | 浏览器抓取（会过期） |
| TUSHARE_TOKEN | ❌ | Tushare 官网 |
| GATEWAY_TOKEN | 自动 | 安装时自动生成 |

## Mac → Linux 注意

- `screencapture` → 需安装 `scrot` 或 `gnome-screenshot`
- `ffmpeg` 路径自动适配
- `LaunchAgent` → `systemd` 自动切换
- 飞书 webhook 地址需要更新为新服务器 IP

## 常见问题

**Q: 打包后多大？**
A: 约 50-80MB（不含 cache 和 node_modules）

**Q: 多台电脑能用同一个飞书应用吗？**
A: 可以，但同时只能有一个 gateway 连接飞书。多台电脑需要多个飞书应用。

**Q: 密钥安全吗？**
A: 打包时自动脱敏，密钥不会出现在压缩包中。安装时从 .env 读取。
