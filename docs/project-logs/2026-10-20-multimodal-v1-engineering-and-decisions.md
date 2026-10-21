# Corvus Multimodal v1 — Engineering & Decision Log

工程窗口：2026-10-18 至 2026-10-20（America/Los_Angeles）。综合核对与本地文档收尾：2026-10-21。

本文面向未参与开发的工程师及 Claude 技术审查。它解释已交付路径、设计取舍、真实故障、证据边界与剩余风险，不是重新部署说明，也不是宣告系统 SEALED。本文编写期间未修改功能代码、部署、运行推理或推送 Git。

## 1. 阅读方式与交付结论

本文采用四种证据标记：

- **[代码/记录事实]**：可由指定提交、源码、已有工程报告或受保护部署检查结果核对。
- **[用户验收]**：用户在 Mac 上报告的实际使用结果；不冒充代理完成的浏览器自动化。
- **[推断]**：与现有证据一致，但没有直接观测到全部因果链。
- **[UNKNOWN]**：现有记录不足，不以经验猜测补齐。

历史报告描述的是当时状态。它们可能写着“Mac pending”、旧的 6 MiB 限制或旧镜像；本文将后续修复与用户验收单独追加，不反向改写历史失败为成功。代码提交、部署成功、HTTP 成功、语义质量通过、用户验收和重启验收分别成立，不能互相替代。

| 能力 | 本轮结束状态 | 不能据此声称 |
| --- | --- | --- |
| STT | 私有 no-convert Whisper、原生听写、浏览器 WAV 转换已部署；重启丢失挂载已修复；用户确认 Mac 使用正常 | 所有浏览器/语言均通过；宿主内存隐私已解决；再次重启已实测 |
| TTS | 已有 Kokoro CPU 服务通过原生 Read Aloud 接入；用户确认 Mac 可用 | 实时双向通话、所有声音/语言质量已验证 |
| Vision | 单原图存储、原生图片 UI、即时内存预览、错误轮次后可继续发送；推理副本缩放已部署 | 所有 OCR、尺寸、硬件或 60 秒内必达保证 |
| Vision Resize | **Vision Resize — MAC ACCEPTANCE PASS**：原始杯子照片与 FocusFox 截图用户实测通过 | 全部 Vision 场景 SEALED |
| Web Search | 已有 SearXNG、Web intent、证据获取与保守来源展示 MVP；代码/离线验收有记录 | 任意 URL 全文阅读、完整文章摘要产品已完成 |

### 1.1 最初的问题

Corvus 已有 A3 对话、附件、Vision、语音后端，却不能直接把这些能力当成 Open WebUI 的原生功能使用。v1 的目标是：在当前可工作的 Lab 中，复用原生 composer、麦克风、图片预览与朗读，把现有本地能力接起来，并保留证据、鉴权、手动发送与精确回滚。

产品交付不是一套新的音视频平台：用户说话后检查可编辑文字并手动 Send；用户选择一张图片并输入文字，发送后能看到图片、回答，重新打开聊天仍有缩略图；用户按需朗读文字。实时通话、历史图片自动重送、视觉检索、任意文档上传不属于本轮。

## 2. 实际架构、版本与隔离边界

### 2.1 服务与依赖

以下是现有部署核对记录及本地收尾核对的基线，不是要求未来照搬的通用端口方案。镜像 ID 是本机保留物的身份，不保证可从远端 registry 拉取。

| 组件 | 实际职责与边界 | 版本/本机入口 |
| --- | --- | --- |
| Open WebUI | 原生登录、composer、消息 UI、音频/图片适配路由；持久保存聊天与图片引用 | v0.6.5；`127.0.0.1:3003` |
| Corvus Pipe | 把 WebUI 当前消息映射到 Lab 会话及既有 Corvus 对话入口，校验已确认回复 | `deploy/open-webui/corvus_pipe.py` 及 `prepare_vision.py` 的既有扩展；Lab `/api/chat` |
| Corvus Lab API | 对话权威、附件处理、Vision 输入、Web/记忆集成 | systemd `corvus-lab-api.service`；`127.0.0.1:18096` |
| Production API | 独立 API 工作目录和规范数据 | `127.0.0.1:8096`；不得随 Lab 回滚 |
| Qwen / llama.cpp | **Lab 和 Production 共用**的推理服务 | `corvus-llama`；`127.0.0.1:8095`；模型别名 `corvus` |
| A3 Attachment Store | 规范原始附件、内容寻址 blob、完整性及消息来源关联 | `memory/attachments.py`；使用各 API 自己的数据根 |
| STT Bridge | 无规范写入的认证转录桥；复用 R1 transport | `127.0.0.1:18106` → 私有 Whisper `/inference` |
| 私有 dictation Whisper | 只接收严格 WAV，不走磁盘转换器 | 固定既有镜像及 `ggml-small.bin`；不发布主机端口 |
| Kokoro | CPU 文字转 WAV；与规范助手文字分离 | `corvus-kokoro`；`127.0.0.1:8105` |
| SearXNG | 搜索发现；不自行承担 Corvus 页面获取和证据授权 | `searxng-local` adapter；默认 `127.0.0.1:8110` |
| Hindsight / Corvus Memory | 现有文本记忆、规范 Evidence 与派生路径 | 本轮不重构；图片轮次保持既有排除规则 |
| FoxGate / Lab nginx | HTTPS 远程入口、独立网关认证、反向代理 | `https://lab-corvus.foxluma.com` → Lab WebUI |

Open WebUI 源码 pin：`07d8460126a686de9a99e2662d06106e22c3f6b6`，不是当前上游 HEAD。原归档 SHA256 为 `e15a53351b91fdc0d8e4499d03f210b684fa198cd58d6557cc5aabffaae5f836`，lockfile SHA256 为 `d140bb9648ff22a039826c710fc5bfa4e5e36b8660ea6e97c9253025cbb1ead9`。正常编译使用既有 Node 22/Svelte/Vite 流程；Node 镜像 pin 和逐文件 source pin 见 `deploy/open-webui/multimodal-v1/source-lock.json`。

本地收尾时保留的运行镜像：

| 服务 | 镜像 ID |
| --- | --- |
| Lab WebUI（聊天错误恢复修复后） | `sha256:2427456fa33f5eccf8a854f9ad37f3af05f0cc443ae6348468f136a25a0745dc` |
| STT Bridge | `sha256:5d3cd6aff2db1a9712ce98669942d093858640298e9c04903f3cee3b510dc6b2` |
| 私有 Whisper | `sha256:caf0cd77c922e9c53f10a9bc17c2f74cc2295d12e7b0f96b630fb3b3c55a0026` |
| Kokoro 日志保护派生镜像 | `sha256:94d19bad32ccb34df77cccc2f5c9bc4ebd1a225878be2522d27b16edc5ae3c44` |
| llama.cpp | `sha256:c50a38601c8bbb6dcb2fdbe60ee336faea7c7c7e11a1d5a6396993783617d911` |

### 2.2 数据流

```text
Mac → HTTPS / FoxGate 认证 → Open WebUI 原生认证
  ├─ 文字/图片消息 → Corvus Pipe → Lab API → 共用 Qwen → 规范助手消息 → WebUI
  │                         └─ 现有文本记忆/Web 证据路径（按轮次条件运行）
  ├─ 原生听写 → 浏览器内存 PCM WAV → 原生认证 STT route
  │           → 认证私有 Bridge → 独立 no-convert Whisper → 可编辑 composer
  ├─ 原生朗读 → 认证 speech route → 固定本地 Kokoro → 临时 WAV → 浏览器
  └─ 图片发送 → 认证同源 adapter → A3 原图 store
               → WebUI 保存授权引用 → 同源鉴权显示
               → 当前轮次推理时才构造内存图片副本 → Qwen
```

Lab API 的实际工作目录为 `/home/ethan/srv/apps/corvus-lab`，数据根为 `/home/ethan/srv/data/corvus/lab`。Production 数据根为 `/home/ethan/srv/data/corvus/private`；Demo 也有独立生命周期。已保存的 Lab systemd unit 使用自己的虚拟环境、只读源码与受限可写数据目录，并限制访问 private/demo。WebUI 数据卷是 `corvus-lab-open-webui-data`，不能以旧备份覆盖当前聊天来回滚代码。

**隔离的实质限制：**API、数据和 WebUI 分离不等于推理资源隔离。两个 API 都指向 `http://127.0.0.1:8095`。重启 Qwen、改变其 GPU 分配或占用唯一模型槽，会影响 Production；Lab 实验不能以“仅改 Lab”为由操作共用模型。

### 2.3 可恢复性与版本保存

功能源码位于多个保留分支，并非全部已合并 main。2026-10-21 本地收尾把累计原生前端源码、已有 Lab systemd 配置及 Kokoro 运行定义的缺口保存为本地提交；完整清单见 `docs/deployment-logs/2026-10-21-multimodal-v1-local-commit-closure.md`。

- `0abe328ef10beb270a5a2ce119648994722831c1`：累计原生前端 patch、源码 pin 和原流程复用说明。
- `03102dc7cc1e8f9c5caf1a52bde225eedd4795f0`：已有 Lab unit/drop-ins、已安装 Pillow 的依赖声明。
- `0406e2d509981b40c06ecf28cb2ca32482775a67`：独立 TTS 分支上的实际 Kokoro Compose 保存。
- `59d7ddff59f31c60c0b2bd24597085582c3b96ac`：本地提交收尾清单。

持久凭据、用户所有权记录、私密 resolved Compose、原始附件、数据库、备份、模型、依赖缓存和镜像不进入 Git。源码可保存不等于裸机灾难恢复已演练。旧 `/tmp` worktree 中未提交的 O_TMPFILE 草稿在收尾时未找回，不能宣称所有历史实验草稿都可恢复；保留 Git refs 未被清理。

## 3. STT：复用既有传输，直到真实浏览器可用

### 3.1 为什么复用 Whisper 与 A3 transport

A3 已有 `app/transcription.py`、附件转录与 TRANSCRIPT 来源关系。R1 的工作是把“HTTP 转录”和“保存派生附件”分开，而不是再造 STT backend：`transcribe_audio_bytes()` 接收音频字节/元数据，通过原有 multipart 协议、语言与 prompt 行为调用 Whisper 并返回文字；`transcribe_attachment()` 继续复用 transport 并保存 A3 TRANSCRIPT provenance。

R1 `688a8bbd94a96239daa50c9277521ea22c706196` 的纯 transport 不创建附件、SQLite 消息或记忆。R2 `3affe0f0899d2158a66b4259cb7295ef0a4b0810` 在不同容器之间增加窄认证 Bridge；WebUI 不重复实现 Whisper multipart，也不假装能直接 import 另一个容器中的 Python。

R3 `0489bd7409f5e6a95a41acf42027fca651a1e658` 保留原生录音、取消与 composer；R4 `83ca1d38836a45088fa6574ed177b1064a0cd87d` 使用浏览器 `decodeAudioData()`、`OfflineAudioContext` 和内存 PCM16 WAV 编码。服务端仍只接受 canonical 16 kHz、mono、PCM16、有限 RIFF 长度的 WAV；它才是权威格式门禁。

### 3.2 隐私边界导致架构选择变化

[代码/记录事实] 旧共享 Whisper 的 `--convert` 会使用 ffmpeg 磁盘转换路径；失败或进程死亡可留下命名音频文件。普通 finally 清理不能覆盖 SIGKILL；tmpfs 也不能自动等同不可换出或即时回收。

早期 noswap local-driver tmpfs 探针通过，证明本机支持相应挂载配置，但它只解决限定存储/换出问题，不能保证失败文件立即消失。O_TMPFILE 草稿需要源码/构建介入，未成为本轮部署。直接给共享 A3 Whisper 去掉 `--convert` 又会破坏其既有压缩音频兼容。

最终 R6 `c0b818fa2c72a4eeb6f8691f5e25f06eea8b87e1` 选择复用既有 image/model，增加一个独立的 **no-convert dictation Whisper**。A3 原服务不变；浏览器先规范化 WAV。R7 `4be6907622e9f0634e5b1c327ae5054cca9200ef` 负责打包，初始 live gate 关闭，后续受控授权才接线开启。

代价是独立模型常驻 RAM/CPU，而不是零成本复用。实际限制为 Whisper 8 CPU、1088 MiB、memory-plus-swap 等于 memory，Bridge 1 CPU、256 MiB；Bridge 单请求准入。私有 Whisper 无主机端口，仅内部网络可达；固定 Bridge 入口为 loopback 18106，无旧 A3 fallback、自动重试或请求自选 upstream。根文件系统/模型/secret 挂载受限，内容日志禁用。

### 3.3 凭据权限与激活故障

首次受控激活 `6dfc5225574fc28073917546f3f07d4b364cb958` 返回 503 并回滚。根因不是 Whisper：WebUI UID 0 但 capabilities 全丢弃，不能读取 UID 10001 所有、0400 的共享 secret 文件。“root 总能读”在该配置中是错误假设。

修复 `6a2a5eb1bab2c4c107dc34b60e2919071795bec1` 复用原独立高熵 credential，分发两个消费者专用只读文件：WebUI UID/GID 0/0、Bridge 10001/10001，均 0400，目录 0700。保留 WebUI-only UID-0 owner-check 修复及其源码 pin；没有加 DAC_OVERRIDE、放宽权限、复用 JWT key 或轮换 secret。

Retry 3 中还出现一次验收脚本误用 `/api/config` 身份传递的故障：该 pinned endpoint 读取原生 token cookie，checker 使用 Bearer 后误以为返回配置缺字段。它触发过保守回滚；修正 checker 后复用相同候选恢复。此事属于验收工具预期错误，不是产品鉴权失效。

### 3.4 HTTP 200、关键词与真正的语音质量

Retry 2/3 的混合语言输出曾 HTTP 200、非空，却不匹配固定关键词。原脚本把这当系统异常会误触发回滚。识别可能产生等价表达、翻译或遗漏；关键词只能覆盖有限形式，既不能证明全部语义正确，也不能单凭不匹配证明系统故障。

`dc46ab579be3b91b6b11cba730e5da98644bc4c8` 将验收区分为 `SYSTEM_FAILURE`、`QUALITY_REVIEW_REQUIRED`、`QUALITY_FAIL`、`ACCEPTED`。认证、协议、隐私、资源等硬门禁仍保持关闭/回滚行为，质量未确认不会伪装成通过。

已有在线 Retry 3 报告的真实结果：

| 项目 | 当时观测 |
| --- | --- |
| 中文公开合成 WAV | 200，非空，既有 phrase check ACCEPTED；4.342 s |
| 英文公开合成 WAV | 200，非空，既有 phrase check ACCEPTED；4.141 s |
| 混合语言 | 200，4.411 s，检测到预期若干概念；**QUALITY_REVIEW_REQUIRED** |
| 无认证 native / Bridge | 403 / 401；错误 Bridge credential 为 401 |
| 无效/不支持音频、过大、超过 120 s | 分别 400/400、413、400 |
| provider 不可达 / deadline | 脱敏 502；deadline 约 25.057 s |
| 客户端取消 | 忙碌准入曾返回 503，约 4.975 s 内恢复到可验证输入状态 |

这些故障/取消是当时授权的真实在线检查，不是把 mocks 称为在线证据。取消 caller 不等于 Whisper worker 同步终止；准入须等实际工作结束。记录的 engine memory peak 约 894.598 MiB、Bridge 56.066 MiB 是合成样本观测，非所有负载保证。

### 3.5 Mac 真正录音暴露的两类前端故障

早期请求 filename=`recording.wav`、Content-Type=`audio/wav`，实际却含 WebM/Opus markers，后端返回 400 `Invalid or unsupported PCM WAV audio.`。这是严格校验正确拒绝，不能通过改 MIME、放宽 WAV 校验或接旧 converter 修复。排查必须确认实际 native microphone `onstop` 上传路径，而非只验证独立 converter 函数。

之后用户 hard reload 与无痕仍失败，旧 JS 已返回 404，当前新版 bundle 中的 converter 也确实在运行。这排除了“只需清缓存”作为该次失败的充分解释。Chrome 给出的具体异常落在 WebM EBML 检查：unknown-sized `Cluster`（`0x1F43B675`）被只允许 unknown-sized Segment 的规则拒绝。

`953d7c853a876d296bf776ce63637d0ad708111d` 对现有 `deploy/lab/stt/normalize.ts` 做有界处理，保留编码大小、时长、嵌套及后端 WAV 校验；不是增加转换器。公开合成音频与实际解析路径验证后受控部署。浏览器解码可能在时长检查前分配内存，取消也不是同步取消 WebAudio；这些限制没有被“支持 Chrome”消除。

### 3.6 Linux 重启后的持久化修复

[代码/记录事实] 一次真实 Linux reboot 删除 `/tmp/corvus-stt-credential-material-...`，导致 WebUI secret bind source 缺失、exit 127、3003 不通，外部 502。Bridge 停止；此前私有 Whisper 已恢复。这不是重建镜像能解决的问题。

`3b93d3ae0b60fad4c96bb9afae8243a84ee81d4d` 与 verifier 修正 `75e3cf9b2042891709fdc1fde18a1158a0767d67` 把原 credential、WebUI protocol override 及 admission 材料放到受保护的 `/etc/corvus-lab/stt`。消费者 ownership/read-only 挂载保持不变；不轮换原 secret，不恢复旧数据库。

三个 STT 相关容器使用既有 Docker 管理及 `unless-stopped`，没有第二套竞争 supervisor。重新创建仅限 WebUI/Bridge，原 image、数据卷、Pipe/Arena/TTS 与其他服务保留。恢复后网页与 health 200，一次认证公开 STT 200、5.123 s，`private, no-store`；原生未认证仍 403。

**[用户验收]** 后续用户确认 Mac STT、TTS 与网页访问正常。**[范围限制]** 修复验证了持久来源、当前行为及 restart metadata，没有再执行一次 Linux reboot；`unless-stopped` 也不保证依赖 readiness 或修复历史 exit 139。手动停止的容器不会因此自动恢复。严禁后来使用带旧 `/tmp` mounts 的 Vision/STT 包覆盖今天的配置。

## 4. TTS：保留规范文字，语音作为展示派生物

A3 已有 `app/tts.py` 与 `GET /api/tts/{assistant_message_id}`：仅从规范 assistant 文字生成 WAV，TTS 失败不撤销助手消息。WebUI v1 复用现有 Kokoro-FastAPI-zh CPU 服务和原生 Read Aloud，而不是移植 A3 UI 或另造语音服务。

### 4.1 实际接口与运行依赖

`deploy/lab/tts/kokoro.py` 通过原生认证 `/api/v1/audio/speech` 调用固定 `http://127.0.0.1:8105/v1/audio/speech`。配置为 model `kokoro`、voice `af_mica`、`lang_code=z`、speed 0.95、WAV、`stream=false`、不生成 download link。接收文字 JSON，返回音频；没有音频识别输入，也不写 canonical chat。

边界为请求 24 KiB、文字 1–4000 字符、读取 body 5 s、连接 3 s、合成 60 s、返回音频 8 MiB。输出检查 24 kHz PCM16 mono/stereo。现有 Kokoro/PyAV 曾在非 streaming 响应仍发出 `0xffffffff` RIFF/data 长度；adapter 只在完整有界接收后修正该已知 sentinel 并验证 finite WAV，不是通用音频 converter。

容器复用 `hexgrad/Kokoro-82M-v1.1-zh` 的既有运行环境与 voice 文件，voice 目录只读挂载，loopback 暴露、`unless-stopped`。准确运行 Compose 在独立 TTS 分支 `0406e2d` 的 `deploy/kokoro/privacy/compose.runtime.yml`；日志保护实现为 `7c0b5d0bbbfe993d4cd4910f1e9c1306de9e3b51`。原上游 CPU image 以 digest pin，而非浮动 latest。

### 4.2 隐私与验收边界

早期工作发现服务日志可能包含输入或音频相关内容，先完成日志隔离/保护再接通。native helper 固定目标、无 redirect/proxy/retry、脱敏错误、`private, no-store`，不保存朗读文本/音频。仅 Docker log none 不足以证明所有进程输出安全，也不解决宿主 swap/dump；保护源码、实际 fd 和 runtime settings 才是当时核对对象。

`3793b13d1f6855d5df7a3b139d47036b1879e4e0` 接通 WebUI；TTS-2.3 的一次公开合成验证为真实认证路径 200/有限 WAV。最初 checker 预期无认证 401，但 v0.6.5 实际为 403，且在合成前停止；修正预期不等于改鉴权。旧报告当时 Mac/iPhone pending，后续 **[用户验收]** Mac 朗读可用。

固定中文配置不等于所有英文/混合语音、voice 或浏览器均做过质量验收。iPhone Safari 未由 Mac 结果覆盖。v1 先交付可工作的听写与朗读，避免把 turn-taking、回声/打断、连续 streaming、实时播放、取消与长期权限同时带进交付范围；实时双向语音不是本轮已实现能力。

## 5. Vision：保留原始证据，只改变推理输入

### 5.1 A3 既有能力与 Single-Store 决策

2026-09-08 的 A3 已支持 raw attachment upload、内容寻址 blob、附件元数据、message attachment provenance 和当前轮次 `image_url`。`app/vision_input.py` 与 `app/conversation_runtime.py` 原有流程为：提交规范用户文字 → 关联附件 → 构造原有文本 Working Context → 当前模型输入追加图片 → Qwen → 提交助手文字 → 派生同步。

因此本轮没有新 storage engine、Vision model 或上传 UI。`96c868d`、`b5a48be`、`da3d9c38f36be4921843f217d0b8cdbe520a4039` 的工作是把这套能力接到 native WebUI，并把用户、chat、message 与附件引用的权威关系补齐。

**Single-Store 指一个原图规范字节来源，不是所有数据只存在一个文件。**原始 PNG/JPEG 由 A3 store 保存；WebUI File/chat 仅有引用及必要元数据。受保护备份属于另行管理的恢复副本；浏览器上传 buffer、模型输入 Base64 与内存缩放副本是临时数据，不能持久化成第二份应用原图。

### 5.2 上传、发送、显示与授权的完整边界

1. 用户通过 native `+` 选择一张 PNG/JPEG，预览、编辑文字或移除；原图在浏览器内存中。当前路径绕过 pre-store `compressImage`，不先改变证据。
2. Send 要求非空文字、一个兼容图片、原始大小不超过 **20 MiB**；image + Arena 在写入前拒绝。未完成请求不并发派发。
3. 经 `deploy/open-webui/vision.py` 的认证同源 `POST /api/v1/files/corvus-image/{chat_id}/{message_id}`，服务端核对原生 user、owned chat、user message 与 operation。客户端 UUID/attachment ID 不是授权凭据。
4. adapter 调固定 Lab API `/api/attachments`，复用 A3 存储与既有 SQLite operation 事务。原始 bytes、格式、大小/完整性约束保留，不给请求方选择 upstream。
5. WebUI File 的 `path=None`、`data={}`；chat 保存 `{type: image, corvus_ref, url}` 形式的引用，而不是 data URL/原始 bytes。保存入口也拒绝 raw/Base64/不支持的 image serialization。
6. native Pipe 扩展从已授权绑定解析**当前 turn** attachment，再调用既有 A3 Vision；历史图片只显示，不重复送推理。image turn 沿用 API 的 Hindsight exclusion，不自动把图片内容写入 Hindsight。
7. `GET /api/v1/files/{id}/content` 每次核对 user、chat、message、引用 membership 与 operation state，经固定内部 API 读取原图，`private, no-store`。不把旧 A3 未认证 content endpoint 直接公开给浏览器。
8. 重新打开聊天时使用同样的引用和授权显示路径。unsupported import/share/clone/reference 转移失败关闭，不能凭知道 chat UUID 或附件 ID 跨用户访问。

操作状态 `PENDING/READY/CLAIMED/UNCERTAIN/COMMITTED/REVOKED` 与 SQLite 事务用于上传丢响应、dispatch claim 和不确定提交；这些不是“网络失败就自动再发一次”的队列。无法确认 canonical commit 时保留不确定状态，阻止重复派发。删除先撤销访问；uncertain、orphan 或仍被引用的 blob 保守保留，未建立安全 reconcile 前不自动物理清理。**逻辑撤销不等于物理擦除**，备份也有自己的保留周期。

### 5.3 容量与网关

早期 adapter 为 6 MiB，A3 Vision reader 为 16 MiB，网关全局 10 MiB；这些历史值并不等于今天的有效限制。`7dc2478420194429249e53bac0520e9a15d58e8c` 仅把 Lab site 上限改为 32 MiB，并在 Lab 使用 Nginx 原生 request streaming，避开 16 MiB tmpfs 的请求缓冲约束；其他站点仍维持原限制。

实际 Lab 网关源码位于 Corvus 的 `deploy/lab/foxgate/nginx/`，不能拿缺少 Lab 路由的旧 FoxGate GitHub 配置覆盖运行环境。`4f138cf28916b4d1a82f6abcefe84838d888a265` 协调现有前端、adapter 和 A3 reader 为原始 **20 MiB**，不增加 compressor。32 MiB transport ceiling 给协议开销留余量，不等于允许 32 MiB 图片。

当时公开合成 PNG exact 20 MiB 接受、+1 byte 413，单次 canonical Vision dispatch 200/3.750 s，有基本图形/颜色 grounding。它证明 encoded-byte 边界，不证明所有手机 codec、分辨率或大图解码内存都安全。WebUI 仅引用、reload 显示、无额外持久 upload cache 有当时检查；跨用户实际第二浏览器登录未做，离线/绑定函数拒绝证据不能冒充完整跨用户浏览器验收。

### 5.4 UI 故障的因果链与最小修复

| 提交 | 已确认故障与修复 | 没有顺手改变的边界 |
| --- | --- | --- |
| `4845db585b3cf4ad50929d9ec721d7da808a5d17` | 331 KiB JPEG upload 6 ms 即 canceled。Svelte 响应式块跟踪到提交期间变化的 controller，触发自己的 `abort()`；将取消收敛到 chat 切换 helper 与该次请求所属 controller 生命周期 | 不重做上传、权限、存储，不通过重复推理验证 |
| `4d5b5847cb35db03e63af305d473c4f69aea188c` | live message.files 先暴露正式 URL，授权引用尚未保存，图片 GET 过早失败；先暂存并保存绑定，再把正式 files 发布到当前 history | 不重新上传原图，不改变正式引用权威 |
| `e5afa6837299b96f30b0457b64f745a7c3cadf99` | 即使上述顺序正确，等网络成功才显示仍慢；点击 Send 后把已有 composer 预览放在 per-chat 内存状态，原生消息 Image 使用它，正式 URL load 成功再切换 | 原图上传/绑定/保存顺序不变；不写 chat、draft、localStorage |
| `a7558fdc39acbe29ca5813182b155b0b65766798` | 上轮 `done=true`、error 非空、content 为空时，Chat.svelte 后续发送守卫仍拒绝新消息；移除已结束错误轮次的重复拒绝，保留前面的未完成请求保护 | 不动 taskIds、AbortController、MODEL_TIMEOUT，不重试旧轮次，不覆盖 composer |

上述提交分别保留于 `fix/vision-upload-abort-lifecycle`、`fix/vision-reference-display-order`、`fix/vision-immediate-memory-preview`、`fix/chat-after-completed-error` 分支；后续分支 HEAD 可能包含部署记录，不应把 HEAD 与首次功能提交混淆。

主要维护入口为 `deploy/open-webui/prepare_vision.py`，预览状态/helper 位于 `deploy/open-webui/vision.ts`，现有测试为 `tests/test_webui_vision_frontend.mjs`。生成目标仍是 native Chat/UserMessage/Image 等组件，没有第二套 composer。

即时预览的正式 URL 接管等图片 load，保留 stale-result 检查，避免闪烁和旧 load 事件覆盖新状态。保存失败显示明确失败，用户只能显式恢复到空 composer，不覆盖正在编辑的新草稿；不自动重传/重新推理。该恢复能力是页面内存级，刷新/退出后不能承诺恢复临时原图。

用户确认“前轮失败后不能继续发”的阻塞已修复；“Corvus did not return a confirmed reply”仍可出现。**UI 恢复与模型回复成功是两件事**：允许下一条独立消息不代表补发上一条、不代表超时解决。

### 5.5 编译材料丢失与正常源码构建恢复

早期 20 MiB 等小修复因重启丢失 `/tmp` 依赖，曾使用严格 pin 的增量 JS packaging；其部署记录明确写明不是完整 Svelte 编译。后来即时预览需要可靠组件编译，不能不断依赖 minified string patch。

恢复时使用同一 Open WebUI archive、lockfile、既有 branding/Arena patches、Node 22 与已锁依赖，将材料保留到 `/home/ethan/srv/build/corvus-webui-v065`。执行正常 Svelte/Vite 构建，不新造 packager。累计源码现在由 `deploy/open-webui/multimodal-v1/frontend.patch` 与 source-lock 保存：7 个 native 文件 + 3 个已有 helper；在已校验 117 个基线文件的 branding/Arena source 上重放，10 个结果 hash 全部匹配。

`f243fe16cc73e1d863ea66ab76ec02d661d215a4` 保存即时预览部署记录，后续 a755 修复也经正常构建部署。新 WebUI 必须继承当前 STT/TTS/认证/backend adapter，不从旧镜像重做覆盖。构建通过是静态/打包证据，不能替代真实浏览器验收。

## 6. Vision「未确认回复」与模型时间调查

### 6.1 先区分 transport、业务提交和 UI

`Corvus did not return a confirmed reply` 是 Pipe 的保护性报错，不是唯一业务错误码。session mapping、overall/model status、persistence 状态或非空 reply 条件不满足都可能产生它。后端 `/api/chat` 可以 HTTP 200 包含失败业务状态；WebUI `completed` HTTP 200 也只证明生命周期 endpoint 成功，不能证明助手回复已提交。

已调查轮次存在规范用户消息/附件，但没有已确认的助手消息，WebUI 为 `done=true, content=''` 加 error，operation 为 uncertain。这与单纯“前端漏显示已保存回答”不同。先前某轮直接确认过 `MODEL_TIMEOUT`，但不能把它套到所有后续失败。

**2026-10-20 20:07 PDT 左右轮次：**已有技术时间记录约为 20:07:23.610 模型 task 开始、20:08:23.177 API 返回 HTTP 200、20:08:23.527 模型收到取消、20:09:10.357 释放。约 60 秒的形态与 timeout 相符；**该轮原始业务响应未留存，精确业务错误码仍 UNKNOWN**。记录时间相关性不能替代实际错误字段。本文不保留图片或聊天正文，也没有为补证重新请求。

### 6.2 场景观察不能直接归因语义复杂度

**[用户验收/故障观察]** 狐狸图片成功、复杂动物群像也成功；高分辨率深绿色杯子照片超时，FocusFox 及其他文字截图也超时。因此“文字多才失败”“语义复杂才失败”都不能解释全部样本。它们也不是控制了尺寸、编码、上下文和运行负载的 benchmark。

### 6.3 直接 llama.cpp 单次实验

用户授权使用同一失败原图，附件 ID `c15b7fe66d385c88ae990e2f804494c2`，**4,026,809 bytes**。此 ID 仅用于对应技术调查，不构成访问权限。原图在内存中核对，正文/Base64 未进入日志或本文。

实验绕过 WebUI、Pipe、Corvus API、历史上下文、RAG 和 Hindsight，直接 POST `127.0.0.1:8095/v1/chat/completions`，model `corvus`，仅问「请描述这张图片里有什么。」；没有额外 system prompt。请求前槽空闲；使用现有生成参数，非 streaming，60 秒客户端上限，仅一次、不重试，不写 Corvus 聊天/记忆。

结果：**DIRECT_QWEN_FAILED**，约 **60.038 s** `CLIENT_TIMEOUT`，未取得 HTTP 响应头/有效回答；不是已收到某个 HTTP 错误码。

已有 llama.cpp 技术日志时间线：

| PDT 时间 | 可确认事件 |
| --- | --- |
| 20:42:37.560 | slot 接到该请求 |
| 20:42:37.756 | processing 记录开始；未观察到显著排队 |
| 20:43:37.566 | 约 60 s 后客户端取消 |
| 20:44:24.001 | task 释放，processing 到释放约 106 s |

取消到释放约 46 s，不能把客户端 timeout 当底层立即停止。日志中的 prompt token 计数不证明已生成首 token。没有可靠的视觉编码、prompt evaluation 和首 token 分阶段耗时；也没有由该次记录确认的 OOM/资源异常。

**结论范围：**上层 Corvus 组件不是“这张图直连超时”的必要条件；不能据此判定 Qwen 有缺陷，不能确定 106 s 都用于视觉编码，不能证明 CPU 是全部根因。具体阶段瓶颈仍 **UNKNOWN**。本次综合日志没有新增推理。

## 7. CPU/GPU 配置核对与未完成对照

### 7.1 实际模型配置

[代码/记录事实] llama.cpp **build 10630**，commit `d222767c7a6516559a3f49e7721b6c6b1acc87b4`，CUDA12 server image。模型与 projector 为：

- `/models/Qwen_Qwen3.5-9B-Q5_K_M.gguf`：Qwen3.5-9B，Q5_K_M，7,111,487,520 bytes。
- `/models/mmproj-Qwen_Qwen3.5-9B-bf16.gguf`：BF16 projector（含 F32 tensors），921,704,896 bytes；视觉初始化可用。
- GPU：RTX 2080 Ti，11,264 MiB。已有快照约使用 8,013 MiB、空闲 2,805 MiB；这不是视觉 peak 或安全 reserve 保证。

原启动关键参数：

```text
-m /models/Qwen_Qwen3.5-9B-Q5_K_M.gguf
--mmproj /models/mmproj-Qwen_Qwen3.5-9B-bf16.gguf
--no-mmproj-offload --alias corvus --host 0.0.0.0 --port 8080
-c 8192 -ngl 99 -t 8 -b 512 -ub 512 --parallel 1 --no-cache-prompt
```

**`--no-mmproj-offload` 明确强制视觉编码使用 CPU。**`-ngl 99` 是主模型 offload 请求值，不能自动写成实测 GPU 层数。Flash Attention 没有显式参数，默认 auto；当前有效 kernel 的逐层选择 UNKNOWN。现有启动记录未见相应 unsupported-operator/fallback 警告，强制 CPU 不能说成已证实 FA 异常 fallback。

### 7.2 上游问题对照的边界

既有官方 Issue 对照记录：

- [llama.cpp #21272](https://github.com/ggml-org/llama.cpp/issues/21272) 的 FA/视觉 fallback 关联 [修复 #21271](https://github.com/ggml-org/llama.cpp/pull/21271)。修复 commit `86221cf6dace86f47d896a38e0de652db4aa81a8` 已在当前 build 的祖先中；不能仅靠 issue 标题把现有强制 CPU 归因到该旧 bug。
- [#22582](https://github.com/ggml-org/llama.cpp/issues/22582) 有 Qwen3.5-9B 图像编码约 82 s 的报告，但其根因解释未获维护者认可。相似耗时不是已确认同一根因。
- [#23422](https://github.com/ggml-org/llama.cpp/issues/23422) 描述 11GB 环境视觉显存分配问题；本机当前 CPU mmproj 及该次无对应分配错误的记录，不足以判定命中同一问题。

这里引用已完成的上游核对，不代表在本文编写日重新确认全部 issue 状态，也不构成升级建议。

### 7.3 GPU 对照为什么没有图片结果

最初因共享 Production 与未知视觉 buffer 显存需求而停止。后来用户明确授权 15 分钟维护窗口，保留原容器、image、参数、Compose 和恢复步骤，才进行临时候选启动。不能在 `-ngl 99` 下直接去掉 CPU flag 并假设 2.8GB 足够。

现有候选使用当前版本 native fit/自动 GPU layer 安排及 reserve 方案，保持 model/mmproj 不变；这意味着若请求执行，主模型 GPU layers 可能成为额外变量。候选健康，但**没有获得可核验的 CUDA 视觉后端确认**，因而 gate 停止，**实际图片 POST 数为 0**。

结果必须写 **GPU_VISION_BLOCKED**，不是 GPU Vision 推理失败，更不是性能对照无改善。现有记录：维护约 68.61 s，原 CPU Vision 完整配置与 `-ngl 99` 恢复，原容器保留，Production/Lab health 与 model 连接正常，其他服务身份未变；候选已清理。恢复后显存快照约 7,987 MiB 使用、2,832 MiB 空闲。没有永久参数变更或额外图片健康推理。

## 8. 有效线索、替代方案与最小推理缩放

### 8.1 用户提供的同画面对照

**[用户验收]** 原杯子照片 1536×2048 超时；同一画面由外部确定性工具缩为 768×1024 后成功。该对照比“狐狸/文字是否复杂”的猜测更有用：支持尺寸或视觉处理量影响请求完成时间。

但它不能证明精确 1024px 阈值是模型极限，也不能分离像素数量、重新编码、当时负载等全部因素，更不能单独证明 CPU 是全部根因。因此采用保守输入策略，不宣称完成性能根因研究。

### 8.2 方案取舍

| 方案 | 已确认能力 | 本轮不选/选择原因 |
| --- | --- | --- |
| llama.cpp `--image-max-tokens` | 当前版本源码存在该参数 | 对当前模型及性能效果未验证；改共用模型配置增加 Production 风险 |
| Open WebUI `compressImage` | 既有浏览器函数可保持比例缩放，小图可不变 | 当前 Single-Store 先保存原图；只在保存后对推理缩放需增加临时副本跨 frontend/Pipe/API 传递及绑定，不能简单打开设置 |
| Pillow | 实际 Python 环境已有成熟 Pillow **12.3.0** | 在附件读取之后、Base64 之前集中处理，不换协议/模型、不增加持久存储、不改共享模型 |

最终不是“前端不能处理图片”，而是根据**原图保存位置与推理输入构造位置**选择最低耦合处。复用成熟工具不等于必须选择最靠近 UI 的工具。

### 8.3 最终实现 `98ae271`

提交 **`98ae27167b0c1e34e2b616351f77757b61c0da08`**，branch `fix/vision-inference-resize`，只改：

- `app/vision_input.py`
- `tests/test_vision_input_adapter.py`

`build_vision_messages()` 先通过原有 `load_vision_attachment()` 检查附件 PRESENT、MIME、签名、20 MiB、原始完整性，再在 Base64 前调用 `_inference_image_bytes()`：

1. 用已安装 Pillow 打开限定 PNG/JPEG；原始宽、高都不超过 1024 时，直接返回**原始字节**，不重新编码。
2. 大图执行 `ImageOps.exif_transpose()`，再用 LANCZOS `thumbnail((1024,1024))` 等比缩小；只编码到 `BytesIO`，保持原 PNG/JPEG 格式与 MIME。
3. 缩放副本仅存在当前推理内存；canonical attachment 元数据、blob、消息关联不改。Base64 是模型请求的派生输入，不保存到 chat/附件库。
4. Pillow decompression-bomb warning 转错误，处理失败返回脱敏明确 `VisionInputError`，不退回原始大图、不自动重试。

**小图分支细节：**为保留字节，小图不重新编码/归一化 EXIF；显式 EXIF transpose 发生在缩放分支。不能把该实现描述为“所有小 JPEG 的方向已独立验证”。大图方向有合成测试；小图对下游 EXIF 行为仍需留意。

20 MiB 上传限制及原有 60 s 模型等待上限保持不变。Pillow 不是新的上传系统，亦没有修改 WebUI、Pipe、STT/TTS、Qwen 参数或数据库。

### 8.4 现有离线测试及结论边界

已有 Vision input adapter 与 conversation runtime 回归记录为 PASS，使用合成图片与临时隔离存储：

| 检查 | 已有结果 |
| --- | --- |
| 小 PNG 1024×512、小 JPEG 640×480 | 模型输入与原始 bytes 相等 |
| PNG 1536×2048 | 输出 768×1024，保持比例 |
| 带 EXIF 旋转 JPEG 2048×1536 | 输出方向与 768×1024 尺寸正确，测试色块方位吻合 |
| 宽图 4096×512 | 输出 1024×128 |
| PNG alpha、PNG/JPEG format/MIME | 保持相应格式/通道语义 |
| 原始 blob、附件元数据、SQLite row count | 没有因派生输入改变/新增 |
| 非法/损坏图处理 | 明确脱敏失败，无派生文件或重试 |
| 既有文本顺序、Vision 失败来源保留 | 回归通过 |

本地收尾另外复核过既有 Vision adapter/runtime、attachment operation 两项、Web MVP/Pipe 42 项及源码重放。这些是各自范围的记录，不是本文新跑的完整验收，也不是所有单元测试全部通过的笼统承诺。

### 8.5 部署事实与真实 Mac 验收

Lab 的实际虚拟环境已有 Pillow **12.3.0**，无临时安装。首次非交互 sudo 不满足权限时未强行部署，源码恢复原状且服务保持健康；随后使用最小本地 operator handoff，受控更新/重启仅 Lab API。已有受保护 operator 结果记录：commit 98ae271、health **HTTP 200**、model/recovery OK、自动 inference requests **0**；运行源码匹配修复。

Production 未修改；WebUI、Pipe、共享 Qwen、Hindsight、STT/TTS、FoxGate 不因该修复改变。保留原 Lab API 源码、unit/drop-ins 和 scoped rollback，不能回滚数据库来回滚 Python 文件。

**[用户验收，本文补充到旧部署记录之后]** 用户在 Mac 直接使用原始高分辨率杯子照片成功识别；FocusFox 文字截图也成功识别。因此记录：

**Vision Resize — MAC ACCEPTANCE PASS**

此结果覆盖这两项真实验收，不覆盖全部 OCR、所有图片方向/尺寸、不同浏览器与硬件，也不保证模型每次 60 s 内完成。部署过程中没有自动重跑历史失败图；用户主动验收与代理自动 retry 必须区分。

## 9. Web Search：已有搜索与正文获取基础，不夸大产品完成度

### 9.1 现有链路

主要源码为 `app/web_intent_gate.py`、`app/searxng_provider.py`、`app/web_search.py`、`app/web_fetch.py`、`app/web_acceptance.py`、`app/web_mvp.py` 和 `app/conversation_runtime.py`。`50a63850f83506724aaff4c2af4f50811d00d646` 为 W2.1 MVP 集成；`01dd02e`/`9b374cf` 为更早 prototype，不表示另起新搜索系统。

Pipe 配置 `web_mode=off/on/auto`。auto 先用现有 deterministic signals，含明确不搜索/记忆问题优先；模糊情况才调用既有模型做 WEB/NO_WEB 分类，错误 fail closed。on 是明确启用，off 不做搜索。它不是让模型随意选网络目标。

SearXNG 本地 provider 只做 discovery；后续由现有公开 URL 校验、SSRF/目标与响应约束、页面抓取/提取和 evidence collector 处理。W2 的 candidate fetch bound 为 3，不无限爬站。搜索 snippet 不能冒充已抓取正文，未经校验的 URL 不成为可信来源。

### 9.2 什么会送给 Qwen，什么不会

Lab 已有 `CORVUS_WEB_MVP_ENABLED=TRUE` drop-in。`prepare_web_mvp()` 只在显式 evidence requirements、来源和覆盖等条件满足时产生 `GROUNDED_ANSWER`，将已选择证据通过原有上下文打包交给 Qwen；引用映射来自已验证页面，不采信模型凭空生成的链接。

当前已安装 Pipe 没有从普通自然语言自动推导结构化 `web_requirements`，也不允许客户端伪造可信 `SourceFacts`。因此普通 WebUI 路径通常走保守 `SOURCES_WITH_LIMITATIONS` 或 `SEARCH_FAILED`：展示已抓取/提取来源及限制，**该确定性回复不调用事实回答模型、不做个人 recall**，标记 evidence insufficient/model NOT_CALLED，而非假装做了完整摘要。失败 provider 与真实 no-results 分开，部分 usable results 可保留。

既有运行时只有确认的 assistant canonical commit 才进入后续相应 provenance/派生同步；Pipe 仅对明确结果类型、匹配 session、有效 assistant ID 和正常 persistence 接受该 fallback。HTTP 200 不是允许无证据回答的开关。

### 9.3 验收与未完成部分

已有 Stage A3.4、W2/W2.1 工程记录，以及离线 mocks 的 intent/provider/来源/业务状态/Pipe 测试；本地收尾 Web MVP/Pipe 42 项 PASS。未从这些记录获得“任意真实网页/任意问题的 Mac 全文总结已通过”的证据，本文不追加此验收声明。

需要精确区分两件事：仓库**已有受限页面 fetch/extraction 基础**，不能说只有 snippets；但独立面向用户的任意 URL Fetch / Article Extraction、全文覆盖验证、付费/登录/JS 页面、日期版本可信提取与通用正文摘要产品仍未完成或未验证。后续应独立评估，不能靠改一个“联网”开关宣称交付。

## 10. Architecture & Product Decisions

### REUSE BEFORE BUILD

A3 的 transcription、Vision、attachment、Kokoro 和 SearXNG 已存在。v1 的新增部分是必要 adapter、授权绑定和原生 UI 接线；不移植旧 React、造第二个 STT engine 或 image store。Pillow 选择同样基于已安装成熟库与最近的可信边界，而非写一个 resize 算法。

### TEST TO SHIP, NOT SHIP TO TEST

固定关键词脚本曾把成功但未确认语义的 STT 当系统故障；反过来 HTTP 200 也掩盖业务未确认。测试须对应用户结果与安全门禁：格式/auth/privacy 硬失败要停，混合语义需 review，不为了报告绿灯反复触发推理。Mac microphone 和真实图片暴露了合成样本没覆盖的问题，不能用再造框架替代用户体验。

### RESUME BEFORE RESTART

多次 usage/SSH 中断、reboot 与 `/tmp` 丢失说明需要先核对已有 artifact、image、checkpoint 和实际容器，而非重复 build/backup/deploy。只补未完成步骤；持久化材料与精确 source pin 比聊天中“上次成功”更可靠。

### STORE ORIGINAL EVIDENCE

图片是长期原始证据，不能为赶上 60 s 把规范附件偷偷替换为压缩图。Single-Store 使原图、来源和重新打开显示保持一致；WebUI 的引用不能成为另一个字节副本或绕过用户 ownership 的捷径。

### INFERENCE DERIVATIVES ARE DISPOSABLE

1024px 副本、模型 data URL、TTS 音频是可丢弃派生物；把它们放在现有边界内存中，可避免持久化版本同步、删除与跨服务授权协议。它不等于内存 erasure 已证明；swap/dump 仍有风险。

### NO AUTOMATIC RETRY OF UNCERTAIN TURNS

超时不代表服务端未提交；客户端取消后模型仍可能工作，operation uncertain 也不能安全当作未执行。保存失败可显式恢复草稿，后续独立消息可发送，但旧请求不自动重试/重新生成，以免重复 canonical dispatch 与推理。

### PRESERVE A WORKING PRODUCTION

Lab 与 Production 共用模型，必须把“API 代码隔离”与“资源影响隔离”分开。每次 WebUI/adapter 修复限于已授权服务，先保留 image/config/data recovery，再 scoped recreation；不通过项目级 down、旧数据库恢复或顺便升级模型解决局部 bug。

### FREEZE THE GOAL, NOT THE IMPLEMENTATION

目标一直是可用的原生听写、朗读和图片问答。实现从共享 converter 的隐私修补转向私有 no-convert；从预想前端 compressImage 接线转向已有 server-side Pillow。变化基于失败证据与交付边界，不是扩大架构。有效解法允许替换，已确认的用户目标和安全约束保持不变。

## 11. 已知限制、风险与不要重复的工作

### 11.1 尚未关闭的技术问题

- 1024px 是保守初始策略，不是精确模型极限；小字可能丢失，不能承诺完整 OCR。
- 20 MiB 是编码字节限制，不是 decoded pixels/RAM 的严格上界。Pillow bomb guard 有帮助，不等于所有恶意图片资源问题已解决。
- CPU 视觉编码由 flag 确认；具体 60/106 s 的阶段耗时 UNKNOWN。GPU 对照未完成，没有 GPU 性能结论。
- 共享单槽模型会受其他调用影响；不保证所有请求 60 s 内返回。本文不改 timeout，也不自动重试。
- 小 JPEG 保留原字节也保留其 EXIF，resize 分支的方向测试不覆盖所有原图显示/模型方向行为。
- 删除即时逻辑撤销，uncertain/orphan 原图与备份可继续保留；物理 reconcile/retention 需要保守且可证明引用安全的后续操作。
- 浏览器音频 decode 可在 duration validation 前分配；页面关闭会丢失内存图片恢复草稿；worker cancellation 并非同步底层终止。
- 主机/客户端 swap、core/crash dumps、hibernation、浏览器 buffer 生命周期仍是 residual risks；本轮没有全面解决宿主安全。
- legacy A3 Whisper `--convert` retention 未因 dictation 私有实例而修好；历史 exit 139 也没有被 restart policy 证明根治。
- iPhone Safari、所有声线/语言、完整 URL 正文产品、实时双向语音均未由本轮 Mac 验收覆盖。

### 11.2 后续工程师应避免

不要重新做 R1–R7 审计或复刻 A3 能力；先看当前 source pins 和已有 tests。不要从旧 WebUI 镜像覆盖累计 STT/TTS/Arena/branding。不要部署 `/tmp` credential packet 或 GitHub 上不含 Lab 路由的旧 nginx。不要把 suffix asset 存在当成实际客户端加载正确，也不要把清缓存当作每次录音失败的解释。

不要再次上传历史私图、触发推理来填日志空白；使用已授权技术元数据。不要将 `done=true` 理解为回复已提交，也不要为了允许新消息清掉旧错误或用户 composer。不要把当前成功样本当成扩容/并发指标。

### 11.3 Git 与运行状态不能合并成一个标签

本地实现分支多、部分旧 worktree 目录已丢失，但 refs 存在。当前 Lab 的四个部署镜像文件在 active checkout 仍是 dirty，字节已保存在相应其他提交；本地收尾没有为了 clean 而 reset 或替换 active worktree。main 未改。

**本地 commit ≠ GitHub push ≠ 运行时部署 ≠ 用户验收 ≠ 重启验收 ≠ SEALED。**已有脱敏 experiment reports 在 `reports/web-validation` 发布；本轮综合日志只本地提交。凭据/数据/本机 image cache 仍需独立保护。`MAC ACCEPTANCE PASS` 不能自动升级为 `SEALED`。

## 12. 证据索引与审查重放入口

### 12.1 本仓库已有源码与工程记录

相对路径按本地对应 feature ref 阅读；不是宣称当前 main 包含全部 feature。

| 主题 | 文件/既有入口 |
| --- | --- |
| A3 Vision 原设计 | `docs/project-logs/2026-09-08-a3-vision-v1-backend.md`、`2026-09-08-a3-vision-v1-web-interaction.md` |
| 附件基础 | `docs/project-logs/2026-09-08-a3-attachment-upload-api.md`、`app/attachment_upload.py`、`memory/attachments.py` |
| A3 语音来源关系 | `docs/project-logs/2026-09-14-a3-voice-v1-backend.md`、`2026-09-15-a3-3d-push-to-talk-voice-ui.md` |
| A3 TTS | `docs/project-logs/2026-09-15-a3-3c-tts-backend.md`、`app/tts.py` |
| STT route/bridge | `app/transcription.py`、`app/stt_protocol.py`、`app/stt_bridge.py`、`app/stt_active.py`、`deploy/lab/stt/activation/` |
| STT 浏览器/持久化 | `deploy/lab/stt/normalize.ts`、`dictation.ts`；`75e3cf9` 的 `deploy/lab/stt/boot/` |
| Vision 接线/UI | `deploy/open-webui/vision.py`、`vision.ts`、`prepare_vision.py`、`app/playground_api.py` |
| 推理缩放与回归 | `app/vision_input.py`、`tests/test_vision_input_adapter.py`、`tests/test_vision_conversation_runtime.py` |
| 前端回归 | `tests/test_webui_vision_frontend.mjs`；累计 source-lock、frontend.patch、README |
| 旧 A3 不回退 | `tests/test_transcription_adapter.py`、`tests/test_voice_conversation_runtime.py`、`tests/test_voice_api_contract.py` |
| Web | `docs/prototypes/w2-1-web-mvp.md`、`docs/phase-reports/stage-a3-4-web-v1.md`、`tests/run_web_acceptance_offline.py` |
| 运行定义保存 | `deploy/systemd/corvus-lab-api.service` 及 drop-ins；TTS 独立 ref `0406e2d` 的 runtime Compose |
| 本地收尾 | `docs/deployment-logs/2026-10-21-multimodal-v1-local-commit-closure.md` |

### 12.2 已发布报告（位于 reports/web-validation）

以下链接指向 reporting 分支，避免把仅存在该分支的报告误当 main 文件。它们是各阶段证据；最终状态以本日志明确追加的后续用户验收为准。

- [STT-1 原始集成及 converter blocker](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-stt1-whisper-offline-integration.md)
- [STT-1a noswap probe](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-stt1a-noswap-storage-probe.md)、[volatile storage 限制](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-stt1a2-volatile-storage.md)
- [STT R1 复用](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-stt-r1-legacy-reuse.md)、[R6 私有实例](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-stt-r6-private-whisper.md)、[R7 packaging](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-stt-r7-lab-preflight.md)
- [Credential repair](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-stt-credential-repair.md)、[Retry 2](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-stt-lab-activation-retry-2.md)、[Retry 3](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-stt-lab-activation-retry-3.md)
- [STT reboot restoration](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-20-stt-reboot-persistence-restored.md)
- [TTS 2.2 logging/runtime](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-tts2-2-kokoro-activation.md)、[TTS 2.3 native route](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-tts2-3-webui-activation.md)
- [Vision single-store decision](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-vision-single-store-decision.md)、[offline implementation](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-19-vision-single-store-offline.md)、[Lab activation](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-20-vision-single-store-lab-activation.md)
- [Vision 20 MiB deployment](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/multimodal/2026-10-20-vision-image20-lab-deployment.md)
- [Web W2.1 MVP](https://github.com/Ethan36Z/Corvus/blob/reports/web-validation/docs/experiment-reports/web/2026-10-18-w2-1-web-mvp-integration.md)

直接模型/CPU-GPU/resize 的部分技术检查结果保存于受保护本地 checkpoint 或当时调查记录，本文仅引用安全状态、时间与 commit，不附其私密配置、原始日志或聊天。部分阶段缺少可重放完整 trace，已在相关段落标 UNKNOWN；不要把本文当成原始逐 token 性能记录。

## 13. 交给 Claude 的技术审查问题

审查目标是**降低复杂度、提高可靠性，而不是重新设计整个系统**。请区分已确认问题、可能风险和证据不足，不要求重新执行私人图片推理来回答。

1. 当前多模态架构是否重复实现了已有成熟组件的能力？
2. Single-Store 与临时推理副本是否存在不必要的复杂性？
3. 1024px 推理尺寸策略是否存在明显的边界问题？
4. STT、TTS 和 Vision 有没有可以复用的现成机制？
5. 当前哪些部分过度设计，哪些部分反而缺少生产级保护？
6. 哪些后续改进具有最高用户价值，而不是最高技术复杂度？
7. 在 11GB VRAM 的限制下，是否有更简单可靠的多模态运行方案？

请优先给出可保留现有产品、规范原图、认证、手动发送、数据与 Production 的最小建议，并明确哪些判断需要额外证据。不要把本次 v1 的用户验收改写成未执行的全面生产认证。
