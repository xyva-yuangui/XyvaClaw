# [分享创造] xyvaClaw — 会自我进化的 AI 助手，38+ 技能，一键部署

> 适用平台：V2EX（发到「分享创造」节点）
> 注意：V2EX 用户偏好简洁、技术性强的内容，不要太营销感

---

**标题**: xyvaClaw — 会自我进化的 AI 助手，38+ 技能，一键部署，开源

**正文**:

做了个开源项目，基于 OpenClaw 运行时深度增强的 AI 助手平台，分享给大家。

## 解决什么问题

用 OpenClaw 搭 AI 助手的痛点：
- 配置要手写 JSON，门槛高
- 单模型，API 挂了就废了
- 上下文一长就丢信息
- 技能一个个装，费时间

## xyvaClaw 做了什么

- **一键安装**: `git clone + bash` 搞定，有图形化配置向导
- **五级容灾**: DeepSeek → Qwen → Kimi → Reasoner → Qwen Max，自动切换
- **无损上下文**: 对话再长不丢信息
- **38 个技能预装**: 浏览器自动化、文档生成、量化选股、视频制作、飞书全 API
- **自我进化**: 错误学习 + 效果追踪 + 自我反思，越用越聪明
- **四层记忆**: 会话 → 日记忆 → 长期 → 知识图谱

## 技术栈

- 运行时: OpenClaw (Node.js)
- 飞书集成: 112 个 TypeScript 源文件
- 无损引擎: 自研 lossless-claw
- 模型: DeepSeek V3.2 + 百炼（Qwen/Kimi/GLM/MiniMax）

## 快速体验

```bash
git clone https://github.com/xyva-yuangui/XyvaClaw.git && cd XyvaClaw && bash xyvaclaw-setup.sh
```

需要一个 API Key: [DeepSeek](https://platform.deepseek.com/api_keys)（注册送免费额度）

GitHub: https://github.com/xyva-yuangui/XyvaClaw
官网: https://www.xyvaclaw.com

MIT 协议，求个 Star ⭐

有问题欢迎讨论。
