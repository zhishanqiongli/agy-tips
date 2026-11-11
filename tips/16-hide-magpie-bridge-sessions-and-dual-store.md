# 16 · 隐藏 `/resume` 里的 `magpie-agy-bridge` 临时会话，并绕开启动对账覆盖

> **强迫症日常崩溃现场**：自从开启了 `"pickerGrouping": "grouped"`（按工作区分组），某天在终端敲 `/resume` 想找回正经项目对话，结果列表里冒出一排 `magpie-agy-bridge-xxxxxx`、`magpie-agy-models-xxxxxx` 的临时目录分组……更离谱的是，明明用 SQLite 删掉了或改了标题，下一次刚运行 `agy`，它们转眼又原封不动“复活”了！

---

## 刨根问底：为什么清了又复活、还专挑桥接会话冒头？

排查 `agy 1.5.5` 与外部桥接插件（`opencode-agy-cli-auth` / `magpie`）后，定位到三层叠加机理：

1. **新版 `/resume` 按 `workspace_uris` 分组暴露了临时路径**
   自 `1.1.26` 起，`agy` 新增了 `"pickerGrouping": "grouped"` 设置，会按会话的 `workspace_uris` 分组展示（`workspaceBasename`）。
   外部插件调用 `agy acp` 时会在 `/private/var/folders/.../T/magpie-agy-*` 下建临时工作区：
   * 仅探活/查模型的会产生 **0 步幽灵记录**；
   * 纯在临时目录跑完对话的会产生 **纯临时工作区 `step > 0` 会话**（`session-cleaner` 默认只清 0 步幽灵，因此漏过它们）；
   * 另有部分挂在真实项目下的对话，会在 `workspace_uris` 里同时夹带真实目录与 `magpie-agy-bridge-*` 临时目录，照样污染分组。

2. **三端同步 + 启动对账机制（删库不删根就会复活）**
   `agy`（`manager.go` / `store_client.go` / `reconcile_summaries.go`）在启动时维护着一套双存储对账链路：
   * **Proto Store**：`~/.gemini/antigravity-cli/jetbox_summaries_proto.pb`（`CascadeTrajectorySummaries`）；
   * **SQLite Store**：`~/.gemini/antigravity-cli/conversation_summaries.db`（`conversation_summaries`、`raw_summary` BLOB 与 `conversations_fts`）；
   * **会话实体文件**：`conversations/<cid>.db` 与 `brain/<cid>`。
   只要实体 `.db` 或 `jetbox_summaries_proto.pb` 还在，下一次任意 `agy` 进程启动都会跑 `summary store: starting background reconciliation`，把被单方面删改的记录重新同步回来！

---

## 终极解法：`agy-hide-bridge` 分级无损隐藏 + 退出自动挂钩

仓库新增了 [`scripts/agy-hide-bridge`](../scripts/agy-hide-bridge)（依赖同目录下的共用底层模块 [`scripts/_agy_pb.py`](../scripts/_agy_pb.py)），按以下策略一次根治，且**绝不暴力删文件**：

| 会话类型 | 判定条件 | 处理动作 |
| :--- | :--- | :--- |
| **0 步探测 / 纯临时 bridge 会话** | `step_count == 0` 或 `workspace_uris` 去掉 `magpie-agy-*` 后为空 | 将 `conversations/<cid>.db*`、`brain/<cid>`、`annotations/<cid>.pbtxt` **移入** `~/.gemini/antigravity-cli/backups/bridge-hidden-<时间>/`；同步从 SQLite、`conversations_fts`、`jetbox_summaries_proto.pb` 与 `cache/*.json` 中移除 |
| **挂有真实项目的双工作区会话** | `step_count > 0` 且包含正常项目目录 | **完整保留对话**，仅从 `workspace_uris`、`raw_summary`（字段 `9` 与 `17.1` / `17.7`）、`jetbox_summaries_proto.pb`、`conversations_fts` 与 `cache/conversation_metadata.json` 中剥离 `magpie-agy-*` 临时路径 |

### 手动试跑与执行

```bash
# 先预览统计，不写任何文件
agy-hide-bridge --dry-run -v

# 正式执行（自动生成滚动 .bak 并移出实体到 backups/）
agy-hide-bridge -v
```

### 挂进 `agy-wrapper` 实现退出自动隐藏

在 [`scripts/agy-wrapper`](../scripts/agy-wrapper) 退出钩子中，先于 [`scripts/agy-title-zh`](../scripts/agy-title-zh) 后台执行 `agy-hide-bridge`，既能保证后续新产生的探测/桥接会话自动消失，也能顺带避免翻译脚本浪费请求去翻译临时会话：

```sh
(
  if command -v agy-hide-bridge >/dev/null 2>&1; then
    agy-hide-bridge >/dev/null 2>&1
  elif [ -x "$HOME/.local/bin/agy-hide-bridge" ]; then
    "$HOME/.local/bin/agy-hide-bridge" >/dev/null 2>&1
  fi
  if command -v agy-title-zh >/dev/null 2>&1; then
    agy-title-zh >/dev/null 2>&1
  elif [ -x "$HOME/.local/bin/agy-title-zh" ]; then
    "$HOME/.local/bin/agy-title-zh" >/dev/null 2>&1
  fi
) >/dev/null 2>&1 &
```

> [!TIP]
> 如需把脚本装到 `~/.local/bin/`，建议直接用软链接 `ln -sf` 指向仓库 `scripts/`，或将 `_agy_pb.py`、`agy-hide-bridge` 与 `agy-title-zh` 一并复制过去。
