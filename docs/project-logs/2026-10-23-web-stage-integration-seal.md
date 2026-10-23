# Web 阶段集成与封版（W1 / W1.1 / Plan C / W2 + Personality P0.1–P0.4）

- 日期：2026-10-23
- 集成分支：`integration/web-stage-seal`
- 工作目录：`/home/ethan/srv/apps/corvus-web-seal`
- 状态：仅在本地提交。没有 push，没有合并到 `main` 或 `lab/ow2e-console`，没有部署，也没有重启任何服务。

## 1. 结论

这个分支**可以作为 Voice 开发的起点**。它的运行时代码与当前在 Lab 中运行的代码逐字节一致（`memory/`、`personality/`、网关配置；`app/` 只有第 4 节所列的 STT 差异），并且包含所有已验收的 Web 成果和 Personality P0.1–P0.4。

`main` 上 Production 一侧的前台登记移植**没有并入**（理由见第 3 节）。

## 2. 提交链

| 提交 | 内容 | 来源 |
|---|---|---|
| `4f8013a` | `lab/ow2e-console` 的 HEAD | 已有 |
| `3d2718b` | 集成基线：multimodal closure（Vision / STT / chat 修复）+ STT 开机恢复 + Kokoro 运行配置 + 网关 body32 | 已有 |
| `6b3e430` | W1：联网证据作答 | 已有，Lab 已验收 |
| `35dd9c9` | W1.1：动态日期、auto 联网判断、简洁回答、Arena 公平性 | 已有，Lab 已验收 |
| `b796650` | Plan C：与 Provider 无关的来源边界、E2 加固 | 已有，Lab 已验收 |
| `cc95d3d` | W2：计时、检索可靠性、相关性门槛、多来源、表格修复 | 已有，Lab 验收（附约束） |
| `2c26ca5` | Personality P0.1 文档（`cherry-pick -x 14b6cf8`） | 来自 `main` |
| `236b79b` | Personality P0.2/P0.3：版本化人格档案（`cherry-pick -x 8b863ec`） | 来自 `main` |
| `dcc2e8a` | 冲突整合：P0.3 合约与 W1.1 日期行 | 本次 |
| `b99a5d5` | Personality P0.4：只存在于 Lab 中的产物（逐字节复制） | 运行中的 Lab |
| 本文档 | 集成报告 | 本次 |

## 3. 集成策略与取舍

- **以 Web 线（`cc95d3d`）为基础**：它已经包含了 Lab 线的全部成果，以及 W1 到 W2 的所有已验收提交。
- **Personality 的取法**：从 `main` 用 `cherry-pick -x` 取两个提交，保留原作者和原提交号的追溯。没有整体合并 `main`。
- **P0.4**：0.1.1 档案、`config.env.example`、Lab 集成测试和两份验收记录，只存在于运行中 Lab 的未提交改动里。它们**按字节原样提交**，每个文件都与 W2 部署前快照中的哈希核对过。P0.4 自己的记录写着 “COMMIT BLOCKED by uncommitted prerequisite changes”，这里说的前置条件就是当时还没提交的 Web 改动，本分支已经包含它们。
- **一处冲突的整合**：`tests/test_personality_runtime.py`。
  - Lab 的 P0.4 版本**删掉了** P0.3 的“版本化人格启用 / 停用 / 回退”合约，原因是 W1.1 追加的日期行破坏了它的完全相等断言。
  - 本分支**保留了这个合约**，只把完全相等改为“人格提示在前且原样不变，后面跟日期行”。
  - Lab 改过的 `test_memory_arena.py` 只是 W1.1 已有断言的子集，所以采用 W1.1 的版本（断言更强）。
- **没有并入 `main` 上 Production 一侧的前台登记移植**（`f240896`、`c315d0e`）。
  - 这两个提交里的 `foreground_registry.py`、`foreground_activity.py` 以及 4 个测试文件，**与 Lab 线的实现逐字节相同**。
  - 剩下的只是一个 Production 兼容性测试、Production 的 systemd 配置和两份文档，都属于 Production 线。
  - 把两条线真正合并成一条（处理 `conversation_runtime.py` 和 `playground_api.py` 中早已存在的分歧）需要单独决策，不在本次封版范围内。

## 4. 与运行中 Lab 的一致性（逐文件比对）

| 范围 | 结果 |
|---|---|
| `memory/` | 一致 |
| `personality/` | 一致（包含 P0.3 和 P0.4） |
| `deploy/lab/foxgate/` | 一致 |
| `app/` | 除 STT 外一致（含 W1、W1.1、Plan C、W2 和 Vision 单存储） |
| `app/` 中的 STT 差异 | 本分支含有已提交的 STT 重构 `688a8bb`：`transcription.py` 提取出 `transcribe_audio_bytes`，`transcribe_attachment` 接口保留；另有 `stt_bridge.py`、`stt_active.py`、`stt_protocol.py`。Lab API 目录里仍是旧的 `transcription.py`（STT bridge 运行在自己的容器中）。**这个重构已通过离线测试，但还没有在 Lab API 上运行过，Voice 阶段需要实际验证。** |
| `deploy/open-webui/` | 本分支多了已提交的 Vision 打包文件（不是运行时代码） |

## 5. 测试（在集成分支上运行）

| 套件 | 结果 |
|---|---|
| 回归 A（离线守卫，全部模块） | 54 通过 / 22 环境限制失败。新增的 `test_personality_profiles` 通过。`test_personality_lab_integration` 受 “Lab only” 路径门禁影响而失败，但在 Lab 路径沙箱中通过 |
| 扩展回归 B（Lab 路径沙箱，16 个模块） | **264 个用例全部通过**：Hindsight、Arena、retain、dense、reboot、Personality P0.3/P0.4、W2、Plan C |
| Vision 单存储（Open WebUI 镜像，`--network none`） | 20/20 |
| Kokoro 隐私（固定的派生镜像，`--network none`） | 19/19 |
| Pipe 哈希锁 | `corvus_pipe.py` 仍为 `68967bd…`，Vision Pipe 可以正常生成 |

## 6. W2 已知限制（随封版记录）

1. **“最新版本”类措辞不准确**：例如 “Node.js 最新 LTS” 回答成了 24.11.0，那是 24 进入 LTS 的版本，而不是最新的 LTS 补丁。关键词和锚点规则无法判断这类语义。
2. **证据较弱时语义准确性有限**：相关性门槛是启发式的，E2 只检查锚点，不验证语义。模型仍可能写出没有引用、来自自身知识的说法，或者措辞含糊（例如重新核实 3.14 时没有明确纠正之前的错误）。
3. **Hindsight 后台推理导致前台等待**：Hindsight 与前台共用一个 llama。实测 `model_wait_ms` 可达 5.8–16.7 秒，而实际计算只有 4–8 秒。这是 Voice / Streaming 阶段要解决的首要性能问题。
4. 非联网聊天的召回仍会带入旧的错误回答（M1，记忆质量问题）。
5. 搜索服务（DDGS）对部分措辞会返回空结果；大页面偶尔会触发抓取超时。两种情况都会如实降级。
6. 删除断言后，回答开头可能留下空行（仅外观问题）。

## 7. 对 Voice 阶段的提示

- **Kokoro 容器 `corvus-kokoro` 已经退出**（exit 137，在 W1 验收之前就已如此），所以 `/api/tts` 返回 503。需要先恢复它。
- 本分支的 STT 重构（`688a8bb`）尚未在 Lab API 上运行，第一次部署时应把语音 / STT 冒烟测试列为必做项。
- 生成上限是 `MAX_GENERATION_TOKENS = 512`，加上与 Hindsight 共用 llama，这两点都会直接影响通话体验。
- 部署本分支前，仍需完整快照 Lab，并核对第 4 节中的 STT 差异。
