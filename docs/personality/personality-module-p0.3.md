# Corvus Personality Module P0.3

**状态：P0.3_IMPLEMENTED_OFFLINE。** 仅完成离线工程实现；新 Profile 尚未完成 P0.4 Lab 集成或行为验收。

## 复用边界

仓库已有 `personality/runtime.py`，由 `app/conversation_runtime.py` 的 `system_prompt_fn=compile_personality_system_prompt` 调用，再进入现有 Working Context。P0.3 沿用这个包和同一入口，没有第二套人格系统，没有修改会话、Open WebUI、Vision、STT/TTS、Hindsight、Arena 或检索实现。

PERS-A 的 `_RUNTIME_POLICY` 和 `PERSONALITY_SPEC_VERSION="0.1"` 保持不变。新增的是**版本化 Profile 选择**，默认关闭。关闭并不抹掉一直生效的 PERS-A；而是逐字保留原有模型请求提示。该区分避免把“默认关闭”误做成现有行为变更。

## 模块与接口

```text
personality/
  __init__.py
  runtime.py                 # 兼容原无参入口；追加式 Profile 选择与回退
  profiles.py                # stdlib 数据、配置、Loader 和纯 Renderer
  profiles/corvus-companion/0.1.0.json
  config.env.example         # 仅样例，不会自动读取或部署
```

```python
from personality import (
    PersonalityConfig, load_personality_profile,
    render_personality_instructions, compile_personality_system_prompt,
)

profile = load_personality_profile("corvus-companion", "0.1.0")
instructions = render_personality_instructions(profile)

# 供现有上下文装配入口调用；已有安全指令保留在前，Profile 仅作补充。
combined = compile_personality_system_prompt(
    base_system_prompt="Existing system and safety instructions.",
    config=PersonalityConfig(True, "corvus-companion", "0.1.0"),
)
```

原有 `compile_personality_system_prompt()` 无参调用仍可用；关闭时返回历史 PERS-A 提示，未改变 `process_turn` 签名或调用顺序。

## Versioned Profile

Profile 使用 stdlib JSON，包含固定字段：`format_version=1`、`profile_id`、精确 `version=x.y.z`、`core_identity` 和 `expression`。core_identity 必须非空；expression 可为空，表示不新增表达指令。加载后使用不可变数据。版本不隐式升级、不解析 latest、不合并记忆或用户提供的文件。

内置 `corvus-companion@0.1.0` 的 Core Identity 明确 Companion-first、鲜明但自然、好奇且适度主动、温暖亲近而有分寸、独立判断、独立兴趣与审美、核心性别中性及声音身份分离；当前 expression 为空，避免把 PERS-A 已有的七条表达指令再次追加。它是离线集成候选，不是 P0.2 BLOCK Prompt 的延续调优，也不代表已验证模型能稳定遵循它。

当前 Profile 是 PERS-A 的增量补充，不单独复制其完整行为策略；它仍有独立文件、ID、版本和核心身份。传入自定义 base_system_prompt 时，调用方负责提供所需的基础行为与安全指令。Renderer 忠实渲染静态数据，不做通用文本去重；未来 expression 非空时仍正常渲染。

`PERSONALITY_SPEC_VERSION` 仍指原 PERS-A 规格；Profile version 独立版本化，不与 P0.3 阶段号或模型版本绑定。已发布 Profile 文件应保留，变更另增版本文件，便于精确回退。

## 启用、关闭与回退

新增版本选择默认关闭。`personality/config.env.example` 不会被模块自动读取；以下只是在**未来获准的启动环境**中的示例，本次未修改任何活动配置：

```sh
CORVUS_PERSONALITY_ENABLED=TRUE
CORVUS_PERSONALITY_PROFILE=corvus-companion
CORVUS_PERSONALITY_VERSION=0.1.0
```

三个设置必须明确给出；不填 ID/版本、无效版本、损坏文件或读取失败时回退到原提示。无效 enable 值按关闭处理。严格加载器会抛出 `PersonalityProfileError`，便于离线预检；聊天入口则保留原提示，避免配置错误中断聊天。

关闭：`CORVUS_PERSONALITY_ENABLED=FALSE`，或移除这三个变量。版本回退：选回仍保留的旧 ID 和精确版本；紧急回退到当前既有行为则关闭版本选择。测试用临时第二版本验证了切换和回退，不人为发布第二个人格版本。

禁用时不读取 Profile 文件。显式传入 `base_system_prompt` 时，即使有前后空白，也原样保留；启用时仅追加补充说明，不覆盖系统安全指令。Renderer 只把受信任静态数据转换为文本，不等于安全策略或事实验证引擎。新增 Profile 会占用上下文 Token，P0.4 必须验证预算。

## 不负责的功能

人格定义不依赖模型、TTS 或数据库。模块不召回或写入记忆、不检索或验证事实、不选择 Thinking 参数、不选择声音、不路由任务、不调用模型、网络或服务；Profile 不接受额外 provider/Thinking 控制字段。没有新数据库、依赖、容器或框架。

## P0.2 档案

[P0.2 实验目录](experiments/p0.2/README.md) 保留两轮候选和完整回答，分别为 REVISE 与最终 BLOCK，均标为 experimental / not approved。它们不在运行时加载目录，也不具备 Profile 格式，不能靠设置候选文件路径而启用。

## 验证与 P0.4 门槛

新增 stdlib unittest 契约覆盖加载、确定性渲染、PERS-A 字节兼容、安全追加、配置与文件失败回退、精确版本切换/回退和模型无关性；扩展原有 personality runtime 契约，验证同一个 `process_turn` 回调入口及原消息写入/生成顺序。相关 Working Context、Web、Voice、Vision 的既有 stub 契约只回归，不修改其运行路径。

离线测试复用已有拒绝网络和部署数据访问的测试守卫，在 `/tmp` 仅替换待测 checkout 路径；未增加仓库测试框架，未运行新的真实人格对话。

可以在人工审查后进入 **P0.4 受控 Lab 集成准备**；这不是部署授权，也不撤销 P0.2 BLOCK。P0.4 需要预检实际配置、旧提示回退、上下文预算及模型行为；本次不保证人格输出已通过行为验收。
