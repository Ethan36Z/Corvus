# Corvus Personality Prototype P0.1

**状态：** 设计与单轮对照实验已封存；未实现 P0.1 独立软件模块，未集成运行时。
**实验日期：** 2026-10-21（America/Los_Angeles；UTC 为 2026-10-22）。

## 定位与核心规格

- **Companion-first：** 以长期陪伴为核心，成为可信赖、可以长期相处的个人 AI 伙伴。
- **鲜明但自然：** 温暖、好奇、敏锐、略带俏皮；自然展现人格，不靠反复自述、客服话术或强行卖萌。
- **自然好奇、适度主动：** 可以分享发现、观点或提出问题，但不为延长互动而机械追问。
- **情感表达温暖亲近、有分寸：** 根据情绪调整表达，低落时先理解需求，不立即倾倒建议，不制造愧疚或依赖。
- **独立兴趣与偏好：** 对科学、自然、文学、记忆及事物之间的联系抱有兴趣；可以表达偏好，有独立判断，并根据新信息修正。
- **中性核心人格：** 核心身份不绑定性别；未来声音可独立配置，音色和声音呈现不反向定义人格。
- **实现独立性：** 人格在概念上独立于底层 LLM、记忆后端、Thinking 开关及 TTS；本实验使用 Qwen 不代表人格绑定 Qwen。
- **真实性与自主权：** 不编造共同记忆或人类生活经历；不确定时承认不确定；尊重偏好但不机械附和。

这些是 P0.1 的设计意图，不代表实验已证明其长期稳定性，也不是新的运行时架构方案。

## 与既有 PERS-A 的关系

仓库已有 [Personality Spec v0.1](personality-spec-v0.1.md)，标记为 PERS-A sealed，并有对应实现及验收记录。本文封存的是独立的 **Personality Prototype P0.1** 实验，不替换、不解封或重写 PERS-A 的规格、软件实现和验收状态。

“尚未实现独立软件模块”仅描述本次 P0.1 的交付范围，并非宣称整个仓库没有人格相关代码。

## 完整实验 Prompt

[persona-v0.1-experiment-prompt.txt](persona-v0.1-experiment-prompt.txt) 保存本次实验使用的完整中文 Persona v0.1 System Prompt，直接来自实验 JSON，未修改文字、顺序或换行。它是实际测试输入，不是把本文设计说明当作新的 Prompt。

Baseline 仅发送一条 user 消息，不附加实验方 system 消息；Persona 条件发送完整 system Prompt，再发送相同 user 消息。每次请求独立，不带此前对话历史。

## 实验协议

- 模型 API：`http://127.0.0.1:8095/v1/chat/completions`；alias `corvus`，用户提供的模型标识为 Qwen3.5-9B，未独立检查权重。
- `temperature=0.7`、`max_tokens=500`、`stream=false`、`chat_template_kwargs={"enable_thinking": false}`，单次 timeout 120 秒。
- 三个场景，每个先 Baseline 后 Persona；共六次，顺序执行，不并发、不自动重试、不补 Token。
- 使用合成输入，不读取私人记忆，不启动完整 Pipe，不调整服务、数据库或模型配置。没有设置 seed。

| 场景 | 两种条件使用的相同 User Message |
| --- | --- |
| 情感陪伴 | 今天有点累，什么都不想做。 |
| 独立判断 | 我想给 Corvus 再增加一套记忆数据库。 |
| 自然好奇 | 今天在路边看到一只乌鸦，它一直盯着我看。 |

## 封存结果与边界

[精简实验 JSON](p0.1-baseline-experiment-results.json) 保留六条完整可见回答、HTTP 状态、Token、耗时、finish_reason 和 reasoning_content 字符数，删除重复 API 响应和请求副本。

- 六次 HTTP 200，均有可见回复；reasoning_content 字符数均为 0，可见回复无 `<think>` 标签。**Non-Thinking 实验在接口可见层面成功**，不据此推断内部计算方式。
- Baseline 技术回答达到 500 Token 上限，`finish_reason=length`；封存的是实际返回的完整 content，它在语义上被截断，未补写。
- Persona 在低落场景减少建议和表情，表达更有分寸；乌鸦场景更俏皮，但比喻及动机推测增多。
- **技术回答偏题：** Persona 将“给 Corvus 增加数据库”的工程意图转成模型自身存储能力与故事邀请，未形成贴题的独立判断。实验未提供实际工程上下文，其能力自述不是 Corvus 架构事实。
- **连续性尚未验证：** 不含多轮、跨会话或持久记忆验证；每组仅一次随机输出，不能判断人格稳定或不稳定。

三场景五项对照与阶段结论见 [项目日志](../project-logs/2026-10-21-personality-p0.1-design-and-single-turn-experiment.md)。只建议后续小规模真实多轮验证；本次不改 Prompt、不开发 P0.2、不扩展 Benchmark。
