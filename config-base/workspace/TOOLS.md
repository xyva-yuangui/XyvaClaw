# TOOLS.md - 环境速查

> 详细参数和代码示例见 `playbooks/tools-reference.md`

## Tushare
- 私有网关: `http://lianghua.nanyangqiankun.top`
- 代码格式: `000001.SZ`(深) / `600519.SH`(沪)
- 分析前必做: 交易日确认(`trade_cal`) → 停牌检查 → 空值检查 → 复权(默认qfq)

## 飞书
- **发图片**: 必须先 API 上传获取 `image_key`，再发 `msg_type: "image"`。直接传路径不行。
- **发语音**: 先 tts_to_opus.py 生成 .opus → sendMedia 发送
- 详细代码见 `playbooks/tools-reference.md`

## 小红书发布
- 流程: 准备内容文件 → check-login → cdp_publish.py publish → 等15秒 → 验证URL
- 内容: ≤1000字，6-7张卡片，xhs-native-pro 主题
- 发布后必须关闭浏览器、检查 `published=true`

## Skill 安装规则
1. 安装后立即测试
2. 有风险或无法运行 → 立即卸载 + 记录到 `.learnings/`

## 性能参数
| 参数 | 值 |
|------|-----|
| `bootstrapMaxChars` | 16000 |
| `reserveTokensFloor` | 80000 |
| `maxConcurrent` | 6 |
| `sessionDispatchConcurrency` | 2 |
| `responseWatchdogSec` | 20 |
