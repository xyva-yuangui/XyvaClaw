# openclaw-cognitive-kit

给 [OpenClaw](https://github.com/openclaw/openclaw) 加一层**认知预处理**：在每轮对话构建 prompt 之前，先用规则引擎识别意图、检索长期记忆、预选技能，把结论注入当轮上下文。

核心是一条已经打通的链路：

```
用户消息
   ↓
before_prompt_build 钩子（extensions/v15-cognitive-hook）
   ↓
cognitive-core --analyze     ← 只跑规则/记忆/技能，不调用 LLM
   ↓
prependContext 注入当轮 prompt
   ↓
Gateway 用自己的模型生成回复
```

注入耗时实测 **70–180ms**，且全链路 fail-open——超时、脚本缺失、输出非法都直接返回空对象，绝不阻塞对话。

---

## 这个仓库包含什么

| 模块 | 说明 |
|---|---|
| **V15 认知引擎** | 17 个 Python 模块：规则引擎（101 条通用意图规则）、记忆织网、模型路由、技能锻造、感知总线、守护循环等 |
| **认知钩子插件** | `extensions/v15-cognitive-hook`，TypeScript，通过 `api.on("before_prompt_build")` 接入 |
| **安装与脱敏工具链** | 一键安装、配置脱敏/还原、密钥全仓扫描（含二进制） |
| **cron 完整性巡检** | 校验定时任务引用的脚本是否存在、超时是否够用、占位符是否已填 |
| **16 个通用技能** | 文档处理、数据可视化、浏览器自动化、代码执行、地图、天气、翻译等 |
| **实例互联技能** | `claw-link`，让多个 OpenClaw 实例之间收发消息、共享媒体与帖子 |
| **A股数据服务** | 多源路由（akshare / baostock / tushare）与缓存框架 |

## 不包含什么（重要）

**业务域规则集与业务参数不在开源范围。**

具体来说，以下内容属于作者在长期使用中积累的私有资产，**不随本仓库发布**：

- **三个业务域的规则** —— 规则引擎的完整框架、优先级策略、`custom-rules.json`
  外部加载机制和 101 条通用意图规则都完整开源；但小红书、量化、内容写作
  这三个业务域的 12 条规则不包含在内
- **量化投研资产** —— 多智能体投研 prompt 矩阵、因子权重、策略参数、回测配置
- **内容运营资产** —— 各平台的话术模板、选题库、发布策略
- **演进知识库** —— 从 v5 到 v15 的架构决策记录与踩坑笔记
- **个人记忆与轨迹** —— 记忆库、推理链、学习记录、定时任务运行日志
- **实际的定时任务配置** —— 本仓库只给 3 个开箱可用的基础任务作为示例

这不是刻意阉割。引擎、框架、工具链是完整可用的；上面这些是**用出来的东西**，
而不是代码。你按自己的场景积累，会得到属于你的那一套。

想加自己的规则不需要改代码，写到 `workspace/state/custom-rules.json` 即可，
引擎会自动合并（见 `rule-engine-v15.py` 里的 `CUSTOM_RULES_FILE`）。

## 快速开始

```bash
cp .env.template .env      # 填入 DEEPSEEK_API_KEY
bash openclaw-install.sh   # 安装到 ~/.openclaw
```

安装器会把配置里的占位符替换成你的 key，未填的自动跳过；网关 token 留空则生成随机值。

启用认知注入（**默认关闭**，建议先自己评估值不值）：

```bash
# 1. 先确认分析入口可用
python3 ~/.openclaw/workspace/scripts/v15/cognitive-core-v15.py --analyze "测试"

# 2. 把 openclaw.json 里 plugins.entries.v15-cognitive-hook.enabled 改为 true

# 3. 重启 gateway，日志出现 [v15-hook] registered 即成功
```

想让记忆检索也生效，需要本地向量服务：

```bash
ollama pull bge-m3
```

不想装本地模型就把 `agents.defaults.memorySearch.enabled` 改为 `false`——规则和技能预选照样工作。

## 已知限制

诚实说明，避免误解：

- **规则命中不等于免掉 LLM 调用。** 规则引擎做的是意图识别、技能预选和风险提示，不含直答模板。所有消息仍然走模型生成。宣传"拦截率"是误导。
- **集群相关能力需要第二台机器。** 本地闪电分类、本地 embedding、集群保活在单机下会跳过（脚本会明确输出"跳过"而不是写入噪声）。
- **`code-runner` 等部分技能要求较新的 Python。** 建议 3.11+。
- **认知注入的价值取决于你的规则质量。** 空规则集下注入内容为空，不占上下文预算，也不产生收益。

## 许可

**AGPL-3.0-or-later**（见 [LICENSE](LICENSE)）。

选它的原因：允许任何人自由使用、修改、自建，但如果你把它改造后作为**网络服务**提供给别人，你也需要把修改后的源码开放出来。

第三方内容归属见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。其中 `workspace/SOUL.md` 来自 OpenClaw 上游（MIT, Copyright © 2025 Peter Steinberger）——MIT 与 AGPL 兼容，但其版权与许可声明必须保留，请不要删除该文件。

### 关于贡献

目前**暂不接受 Pull Request**。

原因需要讲清楚：作者是本仓库唯一版权人，因此保留了将自己的代码另行授权的权利（例如将来推出商业版本）。一旦合并了没有签署贡献者许可协议（CLA）的外部代码，这个权利就永久丧失了。

欢迎提 Issue 反馈问题和需求。如果贡献流程建立起来（届时会引入 CLA 或 DCO），会在这里更新说明。

---

<sub>本仓库由作者的一个打包器从个人实例自动生成（打包器本身不随包发布）。它采用白名单制，并内置密钥扫描、个人标识残留自查、第三方技能检测和工具链漂移检测——任一项不通过即拒绝出包。</sub>
