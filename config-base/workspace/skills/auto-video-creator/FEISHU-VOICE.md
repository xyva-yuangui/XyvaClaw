# 飞书语音消息发送指南

## 流程
1. 用 `tts_to_opus.py` 生成 .opus 文件
2. 通过 OpenClaw 的 `sendMedia` 发送 .opus 文件到飞书

## 生成语音
```bash
python3 ~/.openclaw/workspace/skills/auto-video-creator/scripts/tts_to_opus.py \
  --text "你好，这是一段语音消息" \
  --voice zh-CN-YunxiNeural \
  --output ~/.openclaw/workspace/output/audio/voice.opus
```

## 发送语音到飞书
生成的 .opus 文件可以直接作为媒体发送：
- 飞书扩展的 `sendMediaFeishu` 自动识别 .opus → `file_type: "opus"` + `msg_type: "media"`
- 在飞书中显示为可播放的语音消息

## 可用语音
| 语音 | 语言 | 风格 |
|------|------|------|
| zh-CN-YunxiNeural | 中文男 | 阳光青年 |
| zh-CN-XiaoxiaoNeural | 中文女 | 温柔知性 |
| zh-CN-YunyangNeural | 中文男 | 新闻播报 |
| zh-CN-XiaoyiNeural | 中文女 | 活泼可爱 |

## 注意
- opus 文件需要输出到 `~/.openclaw/workspace/output/audio/`（不使用 /tmp/）
- 飞书要求 opus 格式，脚本自动处理 MP3→Opus 转换
- 最大文件 30MB
