# P0.2 — Experimental / Not Approved

这两个候选仅为实验档案，**均未获准作为运行时默认人格**。它们不位于 `personality/profiles/`，不具有模块 Profile 格式，不会被 Loader 扫描或自动加载。

| 实验 | 结论 | Prompt | 完整 12 轮结果 |
| --- | --- | --- | --- |
| 第一轮 | REVISE | [候选](round-1-prompt.txt) | [对话及指标](round-1-results.json) |
| 最后一次修订 | BLOCK | [候选](final-prompt.txt) | [对话及指标](final-results.json) |

两轮均为三个独立场景、每场景四轮，按顺序请求，保留场景内历史，temperature 0.7、max_tokens 500、stream false、enable_thinking false。两轮各 12 次 HTTP 200，均 stop、reasoning_content 字符数为 0。接口成功不等于行为通过。

第一轮：能口头接受纠正，但实际遵循不稳定；情感场景继续密集比喻、邀请及虚构亲历，技术和乌鸦场景加入未经背景或证据支持的细节，结论 REVISE。

最终轮：用户明确要求轻松闲聊后仍长篇议论、连续邀请；出现亲历式观察和“我们人类”等身份表述；技术与动物行为推测依然过于确定，结论 **BLOCK**。原始 evaluation 在 JSON 中原样保留，没有改变结论。候选的运行时选择被阻止是产品决策，不代表单次样本证明模型永久无法改善。

JSON 保留所有可见回答、顺序、用户输入、背景、Token、耗时和结束状态；仅移除重复 request_messages 和 API response 包装。完整历史可由对应 Prompt、背景和有序问答还原：system 为 Prompt，场景 B 在末尾追加 `\n\n本场景项目背景：` 与 background；随后按 turns 交替追加 user/assistant。保留原始文件和 Prompt 的 SHA-256 供核对。输入为合成数据，不含私人记忆或凭据。

P0.3 只封存这些材料，不重跑、不改 Prompt、不把 BLOCK 候选装入 Profile。运行时保守回退仍是原 PERS-A；P0.3 的新版本选择默认关闭。基础模型事实性和行为服从问题不由加载器解决。
