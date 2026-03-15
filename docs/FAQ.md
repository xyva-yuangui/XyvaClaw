# 常见问题 (FAQ)

---

## 安装相关

### Q: 支持哪些操作系统？
- **macOS** 12+ (Monterey 及以上)
- **Linux** Ubuntu 22.04+, Debian 12+, CentOS 8+, Fedora 38+
- Windows 暂不支持（可通过 WSL2 使用 Linux 安装脚本）

### Q: 需要哪些前置依赖？
- Node.js 22+
- Python 3.10+
- ffmpeg（视频/音频处理）
- Homebrew（macOS，用于自动安装依赖）

安装脚本会自动检测并提示安装缺失的依赖。

### Q: 安装包多大？
- 项目源码约 15-20MB
- 安装后（含 node_modules）约 100-150MB
- 首次启动会下载 embedding 模型约 70MB

### Q: 安装需要 sudo 权限吗？
- macOS: 安装 `xyvaclaw` wrapper 到 `/usr/local/bin` 时需要 sudo
- Linux: 安装系统依赖和 systemd 服务时需要 sudo
- 核心配置部署到 `~/.xyvaclaw` 不需要 sudo

### Q: 可以指定安装目录吗？
可以。通过环境变量 `XYVACLAW_HOME` 指定：
```bash
export XYVACLAW_HOME=/path/to/your/dir
bash xyvaclaw-setup.sh
```

---

## 配置相关

### Q: 至少需要哪些 API Key？
至少需要 **一个** AI 模型 Provider：
- DeepSeek API Key（推荐，性价比高）
- 或 百炼 API Key（支持更多模型）
- 或 任何 OpenAI 兼容的 Provider

飞书等通道 Key 是选填的。

### Q: 可以同时用多个模型吗？
可以。配置多个 Provider 后，系统会自动 fallback。例如 DeepSeek 为主模型，百炼为备用。

### Q: 配置文件在哪里？
- 主配置: `~/.xyvaclaw/openclaw.json`
- 环境变量: `~/.xyvaclaw/.env`
- 飞书密钥: `~/.xyvaclaw/secrets/feishu.env`

### Q: 如何修改配置？
直接编辑 `~/.xyvaclaw/openclaw.json`，然后重启 gateway：
```bash
xyvaclaw gateway restart
```

### Q: 配置向导可以重新运行吗？
可以。进入项目目录，重新启动向导：
```bash
cd xyvaclaw/setup-wizard
XYVACLAW_HOME=~/.xyvaclaw node server/index.js
```
然后浏览器打开 http://localhost:19090

---

## 运行相关

### Q: 首次启动为什么慢？
首次启动会下载本地 embedding 模型（约 70MB），用于语义搜索和记忆检索。下载完成后秒启。

### Q: 如何后台运行？
- **macOS**: 安装时选择开机自启，会创建 LaunchAgent
- **Linux**: 安装时选择 systemd 服务
- **手动**: `nohup xyvaclaw gateway &`

### Q: 如何查看日志？
```bash
# 主日志
tail -f ~/.xyvaclaw/logs/gateway.log

# 错误日志
tail -f ~/.xyvaclaw/logs/gateway.err.log

# 健康检查
bash ~/.xyvaclaw/scripts/health-check.sh
```

### Q: Gateway 占用多少资源？
- 内存: 约 100-200MB（空闲时）
- CPU: 空闲时接近 0，处理请求时短暂升高
- 磁盘: 日志每天约 1-5MB，可用 log-rotate 清理

### Q: 端口被占用怎么办？
编辑 `~/.xyvaclaw/openclaw.json`，修改 `gateway.port`：
```json
"gateway": {
  "port": 18790
}
```

---

## 技能相关

### Q: 安装后有多少技能可用？
38 个技能，分为核心（默认启用 6 个）和可选技能。

### Q: 如何启用/禁用技能？
技能基于 workspace 中的 SKILL.md 文件自动识别。删除或重命名技能目录即可禁用。

### Q: 量化选股需要什么配置？
需要 Tushare Token。在 `.env` 中配置 `TUSHARE_TOKEN`。

### Q: 小红书功能需要什么？
需要小红书 Cookie（会过期，需定期更新）。

---

## 更新相关

### Q: 如何更新 xyvaClaw？
```bash
# 更新 OpenClaw 运行时
npm update -g openclaw

# 更新 xyvaClaw 配置（如果是 git clone 的）
cd xyvaclaw
git pull
```

### Q: 更新后配置会丢失吗？
不会。配置存储在 `~/.xyvaclaw/` 中，与安装包分离。

### Q: 需要重新打包配置基线吗？
大版本更新后建议重新运行 sanitize 脚本，确保配置模板兼容新版本：
```bash
python3 installer/sanitize-for-distribution.py ~/.xyvaclaw config-base
```

---

## 安全相关

### Q: API Key 安全吗？
完全安全。所有密钥仅存储在本地 `~/.xyvaclaw/` 目录中，不会上传到任何服务器。

### Q: 配置向导的数据发到哪了？
配置向导是纯本地的 Web 服务（localhost:19090），数据直接写入本地文件，不经过任何外部服务器。

### Q: 如何备份配置？
```bash
# 简单备份
cp -r ~/.xyvaclaw ~/.xyvaclaw.backup

# 或使用 tar
tar -czf xyvaclaw-backup.tar.gz -C ~ .xyvaclaw
```

---

## 网络问题（中国大陆用户）

### Q: GitHub 下载/clone 很慢？
推荐以下方式：
- 直接 [下载 ZIP 压缩包](https://github.com/xyva-yuangui/XyvaClaw/archive/refs/heads/main.zip)
- 使用 GitHub 镜像：`git clone https://ghproxy.com/https://github.com/xyva-yuangui/XyvaClaw.git`
- 使用代理工具加速

### Q: npm install 很慢？
切换到国内镜像：
```bash
npm config set registry https://registry.npmmirror.com
```

### Q: Homebrew 安装很慢？（macOS）
使用国内一键安装脚本：
```bash
/bin/zsh -c "$(curl -fsSL https://gitee.com/cunkai/HomebrewCN/raw/master/Homebrew.sh)"
```

### Q: pip install 很慢？
切换到国内镜像：
```bash
pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

---

## 故障排除

### Q: gateway 无法启动？
```bash
# 检查 OpenClaw 是否安装
openclaw --version

# 检查 OPENCLAW_HOME
echo $OPENCLAW_HOME  # 应该是 ~/.xyvaclaw

# 检查配置文件
cat ~/.xyvaclaw/openclaw.json | python3 -m json.tool

# 检查端口占用
lsof -i :18789
```

### Q: 飞书消息收不到？
1. 确认 gateway 正在运行: `xyvaclaw gateway status`
2. 确认飞书 webhook 地址正确
3. 检查错误日志: `tail ~/.xyvaclaw/logs/gateway.err.log`
4. 确认应用已发布且有权限

### Q: 模型调用报错？
- 检查 API Key 是否正确
- 检查余额是否充足
- 查看 `logs/gateway.err.log` 中的具体错误信息
- 尝试在配置向导中验证 Key
