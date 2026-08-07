# v15-cognitive-hook

把 V15 认知预分析接到**每轮消息**上——这是 V15 从"CLI 工具链"变成"真实消息管道"的唯一接线点。

## 原理

```
用户消息 → Gateway → before_prompt_build 钩子 ─┐
                                              ├→ cognitive-core-v15.py --analyze
                                              │    · L0 规则引擎（113 条）
                                              │    · 记忆检索（top 3）
                                              │    · 技能预选
                                              ↓
                          prependContext 注入当轮 prompt
                                              ↓
                        Gateway 自己的模型生成回复
```

**关键设计：`--analyze` 不调用任何 LLM。** 生成仍由 Gateway 完成，避免双重 LLM 调用和成本翻倍。

## 注入内容示例

| 用户消息 | 注入的 prependContext |
|---|---|
| 把这个发到小红书 | `意图=xhs_publish 动作=execute 规则=xhs_02 建议技能=xhs-studio,xhs-publisher 风险=medium` + `已匹配技能: xhs-studio` |
| 先做个表格然后发到飞书 | `意图=excel_operation 建议技能=document-suite,excel-xlsx` + `复合意图=是（需拆解为多步执行）` |
| 帮我写个 python 脚本 | `意图=code_task 动作=execute 规则=code_03 风险=low` |

规则未命中且无记忆命中时**注入为空**，不占用任何上下文预算。

## 启用

1. 先确认分析入口可用：
   ```bash
   python3 ~/.openclaw/workspace/scripts/v15/cognitive-core-v15.py --analyze "把这个发到小红书"
   ```
   应输出含 `"ok": true` 和非空 `context` 的 JSON。
2. 在 `~/.openclaw/openclaw.json` 把 `plugins.entries.v15-cognitive-hook.enabled` 改为 `true`
3. 重启 gateway，日志里应出现 `[v15-hook] registered (timeout=1200ms, ...)`

想让记忆检索也生效，需先建索引（否则只有规则和技能部分）：
```bash
python3 -c "import importlib.util,sys; s=importlib.util.spec_from_file_location('mf','$HOME/.openclaw/workspace/scripts/v15/memory-fabric-v15.py'); m=importlib.util.module_from_spec(s); sys.modules['mf']=m; s.loader.exec_module(m); print(m.MemoryFabric().build_index())"
```

## 两个容易踩坑的机制（已核对 OpenClaw 2026.3.13 源码）

**1. 必须用 `api.on`，不能用 `api.registerHook`**

OpenClaw 有两套互不相干的钩子系统：
```js
on:           (hookName, handler, opts) => registerTypedHook(...)  // Plugin Hooks，返回值被采纳
registerHook: (events, handler, opts)   => registerHook(...)       // Internal Hooks，无返回值
```
用 `registerHook` 注册也不报错、也会被调用，但 `prependContext` 会被**完全忽略**——插件看上去装上了却毫无效果。本插件因此只用 `api.on`，且它不存在时直接不注册（不做降级，避免假阳性）。

**2. `hooks.allowPromptInjection` 不能为 false**

`registerTypedHook` 会检查：
```js
if (policy?.allowPromptInjection === false && isPromptInjectionHookName(hookName)) → 拒绝注册
```
严格 `=== false` 才拦，未配置即通过。但 `openclaw.json` 里已显式写了 `hooks.allowPromptInjection: true`，就是防止将来被误关。

另：`register()` 必须是**同步函数**——加载器不 await，异步会导致首个 await 之后的所有注册丢失。

## 配置项

| 字段 | 默认 | 说明 |
|---|---|---|
| `enabled` | `false` | 总开关 |
| `timeoutMs` | `1200` | 硬超时（实测分析耗时 96-180ms） |
| `pythonBin` | `python3` | 解释器 |
| `scriptPath` | `~/.openclaw/workspace/scripts/v15/cognitive-core-v15.py` | 分析脚本 |
| `minChars` | `2` | 短于此长度不分析 |
| `maxContextChars` | `1200` | 单轮注入上限 |
| `maxConsecutiveFailures` | `5` | 连续失败后自动熄火 |

## 安全边界（已实测）

| 场景 | 行为 |
|---|---|
| 分析超时 | kill 子进程 → 返回 `{}`，对话不受影响 |
| 脚本/解释器缺失 | 注册前检查 + 运行时降级 → 返回 `{}` |
| 输出非法 JSON | 解析失败 → 返回 `{}` |
| 连续失败 5 次 | 自动熄火，重启 gateway 恢复 |
| 心跳消息 | 跳过分析，零开销 |

**一律开放失败（fail-open）**：任何异常都只是"没有注入"，绝不阻塞或中断对话。

## 代价

每轮增加一次 Python 冷启动，实测 **96-180ms**。如果你觉得不值，把 `enabled` 改回 `false` 即可，无任何残留影响。

## 已知限制

- 113 条规则**没有直答模板**，所以 L0 命中不等于免 LLM 调用；本插件的价值是"路由更准/技能预选/风险提示"，不是省钱
- 依赖 `cognitive-core-v15.py` 的 `--analyze`；该脚本另需 `pyyaml`（见 `workspace/requirements.txt`）
