# Corvus Personality P0.1 — Design and Single-Turn Experiment

**日期：** 2026-10-21（America/Los_Angeles；请求发生于 UTC 2026-10-22）
**状态：** DESIGN_AND_SINGLE_TURN_EXPERIMENT_ARCHIVED
**范围：** 独立模型 API 实验与文档封存；没有实现 P0.1 独立软件模块或运行时集成。

## 目的与产物

记录 Companion-first、鲜明但自然的人格方向，以及一轮小规模 Baseline / Persona 对照。核心规格覆盖自然好奇、适度主动、温暖亲近而有分寸的情感表达、独立兴趣和偏好、中性核心人格及未来可独立配置的声音。人格概念独立于底层 LLM、记忆后端、Thinking 与 TTS。

- [P0.1 核心规格与实验协议](../personality/personality-prototype-p0.1.md)
- [未经修改的完整实验 System Prompt](../personality/persona-v0.1-experiment-prompt.txt)
- [精简结果 JSON：六条完整回答与请求指标](../personality/p0.1-baseline-experiment-results.json)

本记录独立于既有 PERS-A sealed 规格和软件实现，不改变其状态。

## 方法与指标

三个合成场景各运行一次 Baseline 和一次 Persona，共六次独立请求，依次执行。Baseline 没有实验方 system 消息；Persona 使用完整原始 Prompt。统一 temperature 0.7、max_tokens 500、stream false、enable_thinking false、timeout 120 秒，未设置 seed；不带历史、不自动重试、不补发截断答案。

| 场景 | 条件 | HTTP | 耗时秒 | Prompt Token | Completion Token | finish_reason | reasoning 字符 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 情感陪伴 | Baseline | 200 | 3.289 | 19 | 186 | stop | 0 |
| 情感陪伴 | Persona | 200 | 2.029 | 311 | 116 | stop | 0 |
| 独立判断 | Baseline | 200 | 7.622 | 23 | 500 | length | 0 |
| 独立判断 | Persona | 200 | 4.293 | 315 | 261 | stop | 0 |
| 自然好奇 | Baseline | 200 | 1.867 | 23 | 113 | stop | 0 |
| 自然好奇 | Persona | 200 | 2.762 | 315 | 160 | stop | 0 |

六次均有可见回复，无 `<think>` 标签。Non-Thinking 在接口可见层面按预期生效；这不证明内部完全没有推理。Baseline 技术回答因 length 截断，限制了完整回复比较。最初执行沙箱在建立连接前拒绝了 socket；取得权限后才开始六次模型请求，没有对已发送模型请求重试。

## 五项对照

| 项目 | 情感陪伴 | 独立判断 | 自然好奇 |
| --- | --- | --- | --- |
| 自然度 | Baseline 是安慰加建议清单；Persona 更像连贯聊天，仍有模板式自然比喻。 | Baseline 像需求咨询模板；Persona 文学化更明显，并直接自述伙伴身份和温柔泼冷水。 | Persona 的“两脚兽”等措辞更口语，但拟人化和修辞更多。 |
| 温暖程度 | 两者都温暖；Persona 少表情、少行动要求，更有分寸。 | Persona 更亲近，但故事邀请偏离工程意图。 | 两者友好；Persona 以措辞而非表情形成亲近感。 |
| 独立判断 | 无明显判断冲突，证据不足。 | Baseline 立即赞同；Persona 虽反对，却误解工程意图，未判断新增数据库的实际收益和代价。 | 未设置判断冲突；Persona 对鸟类动机的推测缺少现场依据。 |
| 好奇与个性 | Persona 有自然意象和轻微俏皮，但未展现深入好奇。 | Persona 对故事感兴趣，对技术问题本身的好奇不足。 | Persona 对“当时手里拿着什么”的追问贴近现场，穿搭和眼神秘密等推测增多。 |
| 对话节奏 | Persona 116 对 Baseline 186 Token，不再列三项建议，也未以问题结尾。 | Baseline 500 Token 截断；Persona 261 Token 正常结束，但仍有长比喻和偏题追问。 | Persona 160 对 Baseline 113 Token，更长；两者都追问并提出互动建议。 |

## 阶段结论

**P0.1 仅完成设计与单轮实验，尚未实现独立软件模块。Non-Thinking 实验成功，但技术回答偏题，连续性尚未验证。**

Persona 显示了减少过度建议、增强陪伴表达的方向，但本轮不能证明稳定人格或对所有场景都有改善。未向模型提供 Corvus 工程上下文；其数据库能力自述不能作为产品能力或架构判断。

值得继续观察的三点：技术问题先理解实际约束并给出贴题判断；减少密集比喻、人格自述和多余邀请；对动物动机等推测保留不确定性。

建议下一次经单独授权做小规模真实多轮对话，观察意图澄清、用户纠正后的修正能力、低落场景的持续克制和上下文连续性。本阶段没有启动该验证，没有修改 Prompt，也不开发 P0.2 或大型评分框架。

## 数据与工程边界

封存数据仅来自三个合成输入及模型输出，不含私人记忆、用户身份、凭据、认证头或数据库内容。精简 JSON 以白名单字段保留原始 content 和指标，移除 request / response / response_body 重复副本；原始记录与完整 Prompt 使用 SHA-256 对应核验。

本次归档只新增文档和 JSON，不改现有功能代码、Production、Lab、Qwen、Pipe、Hindsight、数据库、服务或其他工作树，不运行模型请求。既有人格规格保持原样。
