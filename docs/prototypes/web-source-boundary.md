# Web 来源边界（方案 C）— 最小规格

- 基线：`feature/w1.1-date-intent` @ `35dd9c9`（已在 Lab 验收）
- 分支 / worktree：`feature/web-source-boundary` @ `/home/ethan/srv/apps/corvus-web-source-boundary`
- 范围：只改 Context Assembly 和 Web 呈现层。不改 Hindsight、Retain Ledger、数据库 Schema、Personality、Pipe。不删除、不改写任何记忆或证据。

## 1. 问题

W1.1 Lab 验收中的 O1：一个联网轮次的跨会话 RAG 召回带入了旧的助手回答（message 139，其中写着 "Python 3.14 尚未发布"）。模型几乎原样复述，并把内容标成 `[web_1]`，但本轮证据只有 244 个字符，并不支持这些内容。

Hindsight 也已经把助手的幻觉归纳成了 `world` 类型的事实，并且丢失了原始角色（例如 "Python 3.14 官方尚未发布…"、"Node.js 22 includes V8 13.5"）。

研究依据：hallucination snowballing（Zhang et al., ICML 2024）——为了与先前的输出保持一致，模型会继续给出它本可以识别为错误的陈述。

## 2. 原则

1. **来源身份 ≠ 事实可信度。** `user_said` 可以作为用户背景和个性化信息，但不能证明外部世界的事实。`assistant_said`、`derived`、来源不明的记忆，**都不是联网事实的证据**。
2. **策略不依赖具体 Provider。** 由 Corvus 自己判定 origin，不信任 Provider 自称的角色。来源不明一律视为 `derived`（默认拒绝）。
3. **E2 只是低成本的防护**，不是语义验证器（见第 5 节）。

## 3. Origin 判定（Corvus 侧，与 Provider 无关）

| 条件 | origin |
|---|---|
| `id` 是规范 SQLite 整数 ID，且 `role == "user"` | `user_said` |
| `id` 是规范 SQLite 整数 ID，且 `role == "assistant"` | `assistant_said` |
| 其他任何情况（`role` 为 `derived`、缺失、未知，或 `id` 不是规范 ID，例如 `hindsight:…`） | `derived` |

### Provider 最小契约

送入上下文组装的每一项至少要有 `content`（文本）。

- 只有能对应到 Corvus 规范消息的条目，才可以带规范整数 `id` 和该消息的真实 `role`。
- 归纳、摘要、事实抽取得到的条目，必须使用非整数的命名空间 ID（如 `hindsight:<id>`）。它们的 `role` 应为 `derived`，缺省也视为 `derived`。

违反契约时结果是**安全的**：条目被当作 `derived`，在联网轮次中被排除。

## 4. 上下文策略

| 轮次 | 历史召回允许的 origin | 召回块的标题 | 同会话近期消息 |
|---|---|---|---|
| 非联网（含 Vision、语音、Arena） | 全部，**行为与现在完全相同** | 不变 | 不变 |
| 联网（本轮有 Web 证据） | 只允许 `user_said` | 改为“用户自己说过的背景，仅作个人语境，不是外部事实证据” | 保留（续问和“重新核实”需要用到），但由提示词和 E2 约束 |

实现方式：`build_working_context(..., web_grounded=False)`。只有本轮存在 Web 证据时，`conversation_runtime` 才传 `True`。召回会按允许的 origin 继续向后扫描，尽量补满条数，不额外调用检索。

## 5. E2：支撑检查（确定性，不增加模型调用）

- 逐句检查联网回答，跳过围栏代码块。
- 从每句中提取**强锚点**：带小数点的版本号；≥32 的整数（年份、较大的数值）；含数字的标识符（`F1`、`wasm32`、`2to3`、`11GB`）；点分标识符（`node.js`、`sys.remote_exec`）；`__dunder__` 名称。1–31 的纯整数通常是月、日或小计数，跨语言写法不一致，因此不作为锚点。
- 每句的比对语料：
  - 有 `[web_n]` 的句子 → 被引用的那几段摘录；
  - 没有引用的句子 → 本轮全部证据；
  - 两种情况都加上用户自己的文本（当前消息、召回到的 `user_said` 条目、同会话的用户消息）。
- 发布状态否定类断言（`尚未发布`、`未发布`、`还没发布`、`not yet released`、`unreleased`…）：只要证据里没有类似的否定表述，就判为不支撑（这是 O1 中出现的高风险时效断言）。
- 不通过的句子：去掉其中的 `[web_n]`，在句末加 `（未经来源核实）` / `(not verified by sources)`。**不删除内容**，只取消“有证据支撑”的展示方式。
- 诊断字段：`web_claims_unverified`（数量）。

**能力边界（必须明示）：**

- 锚点能在证据中找到，**不代表**陈述正确。例如 "从 64KiB 降到 16KiB" 和证据 "从 16KiB 提升到 64KiB" 用的是同样的锚点，E2 **检测不出来**。
- 没有锚点的纯描述句，E2 也无法检查。
- 主要防线是第 4 节的来源边界，E2 只是兜底。

## 6. 提示词

在 `WEB_EVIDENCE_SYSTEM_INSTRUCTION` 末尾加一句：较早的助手回答和召回的记忆不是证据；除非本轮的网页证据支持，否则不要复述它们的事实性内容。

## 7. 验收（离线；基于真实数据的 fixture）

1. **O1 重放**：RAG 返回 user 138 和 assistant 139（真实文本）→ 联网轮次只保留 138；非联网轮次两条都在。
2. **模拟 Hindsight**：用真实的 `world` 事实 "Python 3.14 官方尚未发布…"，role 为 `derived` 或缺失 → 联网轮次排除，非联网轮次保留。
3. **E2 处理真实回答**：O1 的回答加上它的 244 字符证据 → 未经核实的句子被标注，F1 的引用被去掉；A1、A2、M1，以及 message 139 配上它自己原本的证据 → 0 标注。
4. **混合问答**：用户说过的 "RTX 2080 Ti 11GB" 进入用户背景；回答中引用的 2080 Ti、11GB 不被误标。
5. **同会话重新核实**：证据显示 3.14 已发布，但回答复述 "Python 3.14 尚未发布 [web_1]" → 标注，并去掉引用。
6. **引用编号真实但内容不支持**："Node.js 22 内置 V8 13.5 [web_1]"，证据里没有 13.5 → 标注。
7. **锚点相同但语义矛盾**（记录为已知限制）：断言 E2 **不**标注它。
8. 非联网聊天的上下文参数与现在完全一致。回归 A、B 全部通过；W1、W1.1、Arena、Vision 的契约不变。

Lab 验收需单独授权：在旧的错误记忆仍在库中的情况下重放 O1，并测试混合问答和同会话重新核实。
