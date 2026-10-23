# Corvus Personality P0.4 — Lab Integration

**Final engineering status: controlled activation PASS; restoration VERIFIED.**
**Commit closeout: blocked by uncommitted date/Arena prerequisites. P0.2 BLOCK remains.**

The operator completed the authorized activation and restoration. The live profile
is now disabled and PERS-A restored. See the
[final engineering log](../project-logs/2026-10-22-personality-p0.4-lab-acceptance.md)
for actual requests, hashes, isolation evidence, remaining limits, and the reason
no independent commit can safely be made on the current Lab HEAD.

The following is the original offline preparation record. Its statements about
not applying code or activating the profile describe that earlier stage only;
the final log above supersedes them for current runtime and acceptance status.

## Archived offline preparation

**Status: OFFLINE_INTEGRATION_PASS / READY_FOR_CONTROLLED_LAB_ACTIVATION_REVIEW**

本目录是当前 Lab 代码的离线快照与待审查补丁，**不是已部署代码**。未修改活动 Lab/Production 工作树、配置、数据库或服务，未 commit/push。P0.2 BLOCK 结论保持不变。

## 实际接入位置

- 普通 API：`app/playground_api.py` → `process_turn()` → 现有 `system_prompt_fn=compile_personality_system_prompt` → 日期说明及已有 Voice/Web 上下文 → Working Context → 原模型调用。
- Pipe 仅传递原请求；没有新增客户端人格、模型或 Thinking 字段，没有修改 Pipe。
- Arena：`run_arena_turn()` 在 recall 之前编译人格一次，传入主路的冻结回调。当前 Lab 已有修改会捕获主路最终系统提示（含日期），Shadow 直接复用，不重新解析版本。P0.4 新测试覆盖中途配置变化仍保持两路一致，近期消息相同，只有历史证据提供者不同，Shadow 不新增 canonical 写入。

接入复用 P0.3 提交 `8b863ec95b8c133951e166c8b60d6335b764f7db` 的同一个 `personality/` 包，没有第二个模块、Prompt Builder 或服务。应用源码无需为 P0.4 再改动。

## Profile 与默认状态

当前既有 PERS-A 不变，新 Profile 选择默认关闭。已发布的 `0.1.0` 原样保留。它与 PERS-A 各有一句身份声明，不能作为本次“单一身份”验收的激活版本。

本次准备的 `corvus-companion@0.1.1` 仅将第一条重复的“You are Corvus”声明改为“Put long-term companionship first.”，其余 Core Identity 与 expression 均与 `0.1.0` 相同。这是接入所需的身份声明去重，不是新一轮风格调优；没有执行真实人格对话。版本号独立递增以保留 `0.1.0` 的不可变性。

**本次唯一完成 P0.4 离线验证的版本为 `corvus-companion@0.1.1`。** 它仍待人工批准；`0.1.0`、P0.2 候选和其他版本均不属于本次激活批准范围。未来操作人员必须预检精确 ID/版本，不可假定所有历史 Profile 都已通过单一身份验收。

样例 `personality/config.env.example` 仍设置 `CORVUS_PERSONALITY_ENABLED=FALSE`，不自动加载。未来经单独授权受控启用时，三个变量须明确为：

```text
CORVUS_PERSONALITY_ENABLED=TRUE
CORVUS_PERSONALITY_PROFILE=corvus-companion
CORVUS_PERSONALITY_VERSION=0.1.1
```

这只是文档示例，未写入实际服务环境。Loader 缺失/无效选择回退原 PERS-A，不控制 Thinking、TTS、Hindsight 或模型传输。

## 隔离与快照

- Lab：`lab/ow2e-console`，代码 `/home/ethan/srv/apps/corvus-lab`，API `18096`，数据 `/home/ethan/srv/data/corvus/lab`。
- Production：`main`，代码 `/home/ethan/srv/apps/small-vram-companion`，API `8096`，数据 `/home/ethan/srv/data/corvus/private`。
- 两个运行进程的 cwd 与对应代码目录相符，均未配置 PYTHONPATH 或人格选择变量。Lab 实际 systemd InaccessiblePaths 包含 Production 代码和 private/demo 数据目录；两套虚拟环境和人格目录分离。
- Lab 有已有的未提交 W1/日期/Arena/Vision 等修改。快照保留它们，P0.4 没有覆盖、提交或回滚这些修改。
- `manifest.json` 保存两套工作树的 HEAD、状态、索引及所有 tracked 文件哈希；服务仅保存白名单环境项及完整环境的哈希，不输出密钥。

所有测试在 bwrap 私有挂载空间运行：固定 Lab 路径映射离线副本，真实数据目录被 tmpfs 遮蔽，网络和 PID 命名空间隔离，模型/召回均用既有测试桩。未访问实际模型或记忆数据。

## 验收结果

八个脚本通过，共 89 个 unittest cases（另有模块级断言）：Profile 15、新 Lab 接入 8、Arena 22、Arena API 8、Pipe 25、Arena UI 11、原人格契约与普通 Web/API 契约。新增接入八项均通过。所有守卫记录的网络/私人数据访问违规为零。

既有跳过：Pipe 子进程用例因离线守卫禁用 subprocess；Arena UI 的固定源码集成测试类因未提供 `CORVUS_OW2D_ARCHIVE` 跳过。未把这些跳过宣称为通过。

基线快照在加入 P0.4 前已经有三处日期断言失败：原人格测试一处、Arena 两处，仍期待无日期的旧提示。只在离线副本更新这两个测试文件，使断言覆盖已存在的日期说明/实际系统提示；没有修改日期实现或放宽人格一致性要求。

结果见 `test-summary.json`、`baseline-logs/` 与 `integration-logs/`。`tests/test_personality_lab_integration.py` 校验两个 Arena 模型输入的共享前缀完全一致，身份声明一次、原 PERS-A 规则一次，近期历史一致，主路写入和 Shadow 零 canonical 写入契约保持。

## 交付与回退

`changes/` 只包含相对本次 Lab 快照新增/修改的文件，`integration.patch` 是相同内容的待审查补丁，不含 Lab 既有脏改动。应用前必须重新检查实际 Lab 目标文件哈希与 manifest 的快照一致，存在漂移或冲突即停止，不强制覆盖。

本次不安装代码或环境、不执行服务重启。下一阶段经单独授权，才可在维护窗口将审核过的代码和精确 Profile 接入 Lab，验证上下文预算、真实问答及服务隔离；不能据离线结果宣告人格行为通过。

回退方式：关闭人格版本选择（FALSE 或移除三个变量），回到原 PERS-A 和现有日期/安全上下文。若需回退代码，仅恢复激活前备份的 Personality 文件并移除本次新增文件；保留 W1、日期、Arena、Vision 等原有修改，不 reset/clean，不回滚共享数据库。未来若需重启使环境生效，仅能另行授权操作 Lab API。
