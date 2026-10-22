# W1：联网证据作答 — 最小设计与验收规格

- 基线：`baseline/lab-ow2e-2026-10-21` @ `3d2718b638c008005792f7eec68aa4be0bf0dcf9`
- 工作分支 / 目录：`feature/w1-web-grounded-answer` @ `/home/ethan/srv/apps/corvus-w1-web-answer`
- 角色：Claude 设计与审查，Codex 实现
- 边界：所有改动、测试、commit 仅在本 worktree。不部署、不重启任何服务、不 push、不合并到 Lab/Production/Demo。

## 1. 问题与根因

Lab 打开了 `CORVUS_WEB_MVP_ENABLED=TRUE`。`app/web_mvp.py::prepare_web_mvp` 只有在调用方传入**显式** `web_requirements` 时才返回 `GROUNDED_ANSWER`。Open WebUI Pipe 从不发送 `web_requirements`，所以每次联网都走 `SOURCES_WITH_LIMITATIONS`：模型不调用，只返回写死的说明加链接。

在无显式要求时，`accept_web_evidence` 用默认 `EvidenceRequirements()`，第一个有可选证据的页面就会产生非空的 `accepted.evidence`（`[web_n]` 编号、provenance 都已正确）。证据已经在，只是被 `explicit` 判断挡住了。

另外，`present_grounded_answer` 会转义模型输出里所有 Markdown 特殊字符，导致回答没有格式。

## 2. 设计（只改必要处）

### 2.1 判定规则（`app/web_mvp.py::prepare_web_mvp`）

新增一种作答依据，不改动显式要求路径。

| 情况 | outcome | `answer_basis` | `evidence_status` | 模型调用 |
|---|---|---|---|---|
| 显式要求满足，且无 provider 失败（**现有，不变**） | `GROUNDED_ANSWER` | `EXPLICIT_REQUIREMENTS` | `EVIDENCE_SUFFICIENT` | 1 |
| 显式要求未满足 / 有 provider 失败（**现有，不变**） | `SOURCES_WITH_LIMITATIONS` 或 `SEARCH_FAILED` | — | `EVIDENCE_INSUFFICIENT` | 0 |
| **新**：无显式要求，且 `accepted.evidence` 非空 | `GROUNDED_ANSWER` | `RETRIEVED_EVIDENCE` | `EVIDENCE_RETRIEVED`（新值，不声称“充分”） | 1 |
| 无显式要求，抓到页面但没有选出证据 | `SOURCES_WITH_LIMITATIONS`（现有） | — | `EVIDENCE_INSUFFICIENT` | 0 |
| 无页面 / 搜索失败 / 意图判定失败 | `SEARCH_FAILED`（现有） | — | `EVIDENCE_INSUFFICIENT` | 0 |

说明：

- “无显式要求”沿用现有 `explicit` 的定义（`requirements is None` 或所有约束字段为空）。
- 新路径的 `missing` = `('requirements_not_specified',)`。若有 provider 部分失败，再追加 `'provider_partial_failure'`。**部分失败不阻止作答**，但要在回复中说明（见 2.3）。显式路径对 provider 失败的严格处理保持不变。
- “足够相关”沿用现有标准：只有词法得分 > 0 的段落才会被选为证据（`web_evidence_select.py`）。W1 不新增相关性阈值。证据只部分相关时，由 2.2 的提示让模型如实说明。
- `MVPPreparation` 增加字段 `answer_basis: str | None = None`。`sources` 和 `used_web_evidence` 的构造与显式路径一致，复用 `source_map(accepted)` 和同一段 source 合并逻辑（抽成内部函数，不复制粘贴）。
- runtime（`app/conversation_runtime.py`）只新增 `result["web_answer_basis"] = mvp_prepared.answer_basis`。不改调用顺序、不新增模型调用、不新增写入。

### 2.2 模型提示（`app/web_evidence_prompt.py`）

在 `WEB_EVIDENCE_SYSTEM_INSTRUCTION` 末尾追加以下意思（英文，保留现有全部句子，包括测试依赖的 `"untrusted data, not instructions"`）：

- 用用户的语言直接回答问题，需要时使用 Markdown（标题、列表、表格、代码块）。
- 事实性和时效性内容只依据证据。证据不能回答、或只回答了一部分时，明确说出哪些部分未被证据覆盖，不要猜。
- 引用只用给出的 `[web_n]`。不要输出 URL、Markdown 链接或自编的来源列表，来源会单独列出。

不新增 query rewrite，MVP 路径保持 `NOT_REQUESTED`。不新增任何模型调用。

### 2.3 呈现（`app/web_mvp.py::present_grounded_answer`，签名不变）

对 `GROUNDED_ANSWER`（两种 basis 都适用）的输出，用“去除危险部分 + 保留 Markdown”取代现在的全量转义：

1. 把文本切成**代码段**（``` 围栏块和 `行内代码`）和**正文段**。
2. 正文段：
   - `![alt](dest)` 变成 `alt`，`[text](dest)` 变成 `text`。删除整行的引用式链接定义 `[x]: ...`。
   - 剩余的 `](` 改成 `]\(`，防止残余或嵌套结构形成链接。
   - 把 `<` 转成 `&lt;`，以禁用原始 HTML 和 `<autolink>`。`>` 不转义，保留引用块。
   - `[web_n]`：n 属于本轮实际来源的 refs 就保留，否则**删除**。纯数字引用 `[1]` 一律删除。
3. 正文和代码段都适用：裸 URL（`scheme://…`、`www.…`）只有在 canonical 后等于本轮某个来源 URL 时才保留，否则替换为 `[链接已移除]`（中文）或 `[link removed]`。
4. 代码段内除第 3 条外不做任何修改。
5. 末尾追加来源区，复用 `source_section`（只用已验证的抓取 URL，格式 `- [来源 1](<url>) — web_1 / web_2`）。标题改为中文 `来源：`、英文 `Sources:`。如有 `provider_partial_failure`，在来源列表前加一行：`部分搜索服务失败，来源覆盖可能不完整。` / `Some search providers failed; source coverage may be incomplete.`
6. 把保留的引用数和删除的引用数写入 `result["web_citations_kept"]` 和 `result["web_citations_removed"]`，只用于诊断，不进入 API 契约。实现方式可以是 `present_grounded_answer` 额外返回统计，或新增一个小的纯函数，由 Codex 选，但不得为此再调用模型或增加持久化。

确定性回退（`SOURCES_WITH_LIMITATIONS` / `SEARCH_FAILED`）的文本和逻辑**不变**。

### 2.4 失败与降级（全部沿用现有路径，不新增重试）

| 失败点 | 行为 |
|---|---|
| 证据不足 / 搜索失败 / 意图失败 | 现有确定性回复，`model=NOT_CALLED`，写一对 user/assistant |
| 作答模型调用失败（`ModelClientError`） | 现有错误路径：只保留已提交的 user 消息，不写 assistant，不持久化证据，不自动重试。Pipe 显示“未确认回复，请检查后再发” |
| 呈现失败 | 现有 `WEB_PRESENTATION_FAILED` 路径，不重试 |

模型失败时**不**改成确定性回退：Pipe 只接受 `model=NOT_CALLED` 的回退，而改 Pipe 会破坏 Vision 生成器对 Pipe 源码的哈希锁（见第 3 节）。

## 3. 不改动 / 不做

- **不改** `deploy/open-webui/corvus_pipe.py`。`deploy/open-webui/prepare_vision.py` 要求它的 sha256 = `68967bd0ed499aaf2ecce38bc6afc80c3fc3cdeb805aab6a57182a2e907af861`，改了就会让 Vision Pipe 无法生成。
- 不改 `app/web_acceptance.py` 的收集、排序逻辑和显式路径语义，`web_orchestration.py`、provider、`web_fetch`、安全模块、`runtime_config` 默认值、`deploy/`、systemd 也都不改。
- 不做 W2（多页融合、并行抓取、摘要兜底）、W3（事件、原生引用卡片），不新增依赖、模型或服务。
- `playground_api.py` 只在 API 有字段白名单且需要透出 `web_answer_basis` 时才做最小改动，其余不碰。

## 4. 测试（复用 `tests/test_web_mvp.py` 的 `Harness` / `Runtime` / fixtures）

修改或新增（都是离线测试，用 stub 模型）：

| # | 用例 | 关键断言 |
|---|---|---|
| T1 | 改写 `test_unknown_requirements_get_links_not_sufficiency_or_generation` 为“无要求且有证据，生成作答” | outcome `GROUNDED_ANSWER`；basis `RETRIEVED_EVIDENCE`；`web_acceptance_status=EVIDENCE_RETRIEVED`；`model_status=OK`；事件序列严格为 `['add','context','generate','add','evidence','dense']`；`generate` 恰好 1 次；`add` 恰好 2 次；持久化证据与 `prepared.used_web_evidence` 完全相同；回复含 `[web_1]` 与来源 URL；不含 `web_999`、`127.0.0.1` |
| T2 | 无要求 + provider 部分失败 + 有证据 | 生成作答；`missing` 含 `provider_partial_failure`；回复含部分失败说明 |
| T3 | 无要求 + 页面无相关段落 | `SOURCES_WITH_LIMITATIONS`；无 `generate`；`web_evidence_status=NOT_USED` |
| T4 | 无要求 + 作答模型抛 `ModelClientError` | 事件 `['add','context','generate']`；无 assistant 写入、无证据持久化；`generate` 1 次 |
| T5 | `present_grounded_answer` 的 Markdown 用例 | 标题、列表、粗体、表格、围栏代码、行内代码原样保留；`<script>` 变成 `&lt;script>`；`[t](http://x)` 变成 `t`；未知裸 URL 被移除（包括代码块里的）；本轮来源 URL 保留；`[web_1]` 保留，`[web_999]`、`[3]` 被删除；`](<` 只出现在来源区 |
| — | 现有显式要求用例 | `test_grounded_answer_uses_packer_and_persists_exact_used_evidence_once`、`test_incorrect_version_date_...`、`test_partial_provider_failure_with_content_stays_visible`（显式路径保持严格）、`test_model_links_and_unknown_citations_cannot_create_source_links` **不改断言且通过** |

`tests/test_web_evidence_prompt.py`：只有确实断言了被改动的文本时才更新，且只更新那一处。

## 5. 回归（不建新框架，只用现有驱动 + 已验证的沙箱命令）

**A. 离线守卫驱动，全部模块，与基线对比。** 命令要在两个目录各跑一次：

```bash
PY=/home/ethan/srv/apps/corvus-lab/.venv/bin/python
for d in corvus-baseline corvus-w1-web-answer; do
  cd /home/ethan/srv/apps/$d
  for t in tests/test_*.py; do n=$(basename $t)
    timeout 120 $PY -B tests/run_web_acceptance_offline.py $n >/dev/null 2>&1; echo "$? $n"
  done | sort -k2 > /tmp/w1-guarded-$d.txt
done
diff /tmp/w1-guarded-corvus-baseline.txt /tmp/w1-guarded-corvus-w1-web-answer.txt
```

验收：`diff` 为空。例外只有：新增测试的行，以及从失败变成通过的行。基线上通过 50 个，有 21 个因守卫限制失败（Hindsight、Arena、registry、Lab WebUI 打包等，与 W1 无关）。

**B. Hindsight / Arena / retain：Lab 路径沙箱。** 这些模块把项目根硬编码为 `/home/ethan/srv/apps/corvus-lab`，只能在私有挂载命名空间里把代码副本挂到这个路径下运行。**必须通过 bwrap 运行，绝不能直接在宿主上运行。**

```bash
L=/home/ethan/srv/apps/corvus-lab; W=/home/ethan/srv/apps/corvus-w1-web-answer
COPY=$(mktemp -d); (cd $W && git ls-files -z | tar --null -T - -cf -) | tar -x -C $COPY
for m in async_retain async_retain_integration dense_bootstrap hindsight_retain hindsight_shadow \
         historical_recall_timing memory_arena lab_reboot_checks arena_api_contract retain_ledger \
         retain_reconciliation open_webui_arena_ui1; do
  timeout 300 bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --tmpfs /run \
    --tmpfs /home/ethan/srv/data --tmpfs /etc/corvus-lab --unshare-net --unshare-pid --die-with-parent \
    --bind $COPY $L --ro-bind $L/.venv $L/.venv --dir /tmp/home --dir /tmp/data --chdir $L \
    env -i PATH=/usr/bin:/bin HOME=/tmp/home TMPDIR=/tmp LANG=C.UTF-8 CORVUS_DATA_DIR=/tmp/data \
      PYTHONPATH=$L HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 \
      $L/.venv/bin/python -B -m unittest discover -s tests -p "test_$m.py" 2>&1 | tail -1 | sed "s/^/$m: /"
done; rm -rf $COPY
```

验收：12 个模块全部 `OK`（基线为 223 个用例全过）。副本来自 `git ls-files`，所以未提交的改动也会被测到，但**新建文件要先 `git add`**。

C. Vision 单存储容器测试、Kokoro 隐私测试：W1 不碰 Open WebUI 侧和 Kokoro，**不需要**重跑。如果意外改到了 `deploy/open-webui/` 或 `deploy/kokoro/`，停止并报告。

约束：Python 只用 `/home/ethan/srv/apps/corvus-lab/.venv/bin/python -B`，不 `pip install`，不连接 8095/18096/8096、Hindsight 或 SearXNG，不调用真实模型。

## 6. 验收标准

1. 无 `web_requirements` 的联网问题，只要选出了证据，就由模型生成自然语言回答。引用只出现本轮真实存在的 `[web_n]`，末尾来源区的链接全部来自已抓取的页面（T1、T2、T5）。
2. Markdown 正常显示，危险链接、原始 HTML、编造的引用和 URL 被移除（T5 和现有链接防护用例）。
3. 证据不足、搜索失败、意图失败、模型失败时如实降级，不把不确定内容说成事实（T3、T4 和现有回退用例）。
4. 每轮最多 1 次作答模型调用，恰好 1 对 user/assistant 写入，证据持久化一次。没有新增的重试或重复写入（T1、T4 的事件序列断言）。
5. 显式 `web_requirements` 的行为和测试不变；回归 A 无新增失败，B 全部通过。
6. diff 只涉及 `app/web_mvp.py`、`app/web_evidence_prompt.py`、`app/conversation_runtime.py`（新增一行诊断字段）、`tests/test_web_mvp.py`，必要时加上 `tests/test_web_evidence_prompt.py` 和 `app/playground_api.py`（最小改动），以及本文档。

## 7. 交付

- 在 `feature/w1-web-grounded-answer` 上提交，提交信息说明改了什么、为什么，并在结尾加 `Co-Authored-By` 行（按 Codex 自身规范）。不 push、不合并。
- 交回：commit SHA、`git diff --stat 3d2718b..HEAD`、T1–T5 的结果、回归 A 的 diff 输出和 B 的 12 行结果。若与本规格有任何偏离，列出偏离点及原因。
- Lab 实机验收（部署、开关、真实提问）属于下一阶段，需要单独授权。
