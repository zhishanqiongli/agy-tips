# 12 · 汉化 /resume 英文会话标题：退出时同步回写 SQLite 与 annotations

> **强迫症日常崩溃现场**：明明你从头到尾都在用字正腔圆的中文跟 `agy` 对话，某天敲开 `/resume` 想要找回之前的上下文接着写代码，结果终端列表里弹出来的一水儿全是长串英文大写标题（比如 `Partner Meeting Calendar Update`、`Database Connection Pool Refactor`）……在终端里靠中文搜索根本搜不到，找个会话全靠肉眼硬翻译。

---

## 刨根问底：为什么死活不给中文标题？

拆解二进制字符串与请求链路后，发现这是底层标题生成链路写死的规则：
1. **内置英文格式提示词**：`agy`（以及 Antigravity IDE / 客户端内置的 `language_server`）里硬编码了如下系统提示词：
   `You are a conversation title generator. ... Respond with ONLY a short conversation title (3-5 words, title-cased, no prefix) describing the USER's intent.`
   它**既没有**要求跟随用户语言，**又明确要求** `3-5 words, title-cased`（英文词数与首字母大写规范），模型自然稳定输出英文短语。
2. **独立旁路调用**：标题生成走独立的后台摘要请求或远端接口 `/google.gca.aicode.v1main.JetskiRemoteAgentProxyService/GenerateConversationTitle`（注：`GetCascadeConversationTitle` 其实是 protobuf 消息 `TrajectoryDescription` 读取字段的 getter，并非远端 RPC 名称），不读取你的 `GEMINI.md` / `AGENTS.md` 中文全局规则，客户端设置里也没有暴露语言切换开关。

---

## 侦探突破口：本地多处持久化存储结构

既然请求侧没有开关，就只能从本地存储入手。在 `agy 1.5.5+` 中，会话标题与首句摘要并非只存在一个字段里，而是分布在同一套本地目录中（CLI 目录为 `~/.gemini/antigravity-cli/`）：

* **SQLite 数据库**：`~/.gemini/antigravity-cli/conversation_summaries.db`
  * `conversation_summaries.title`：自动生成的会话标题；
  * `conversation_summaries.preview`：首轮请求摘要/预览；
  * `conversation_summaries.raw_summary`：序列化的 `CascadeTrajectorySummary` protobuf BLOB（其中字段 `1` 对应 `summary`/`preview`，字段 `15.1` 对应 `annotations.title`）。**注意**：新版 `RecordToSummary` 会优先读取 `raw_summary`，若只改 `preview` 文本列，重启后台对账时可能无效甚至被还原；
  * `conversations_fts`：`chunk_index = -1` 的表头行存有供 `/resume` 搜索（`title:<query>`）使用的 `title`。
* **Proto Store（关键对账源头）**：`~/.gemini/antigravity-cli/jetbox_summaries_proto.pb`
  * 存储 `CascadeTrajectorySummaries` map，每次 `agy` 启动时 `store_client.go` 会跑 `summary store: starting background reconciliation (trigger=startup)`，把其中的记录同步覆盖进 SQLite。**如果只改 SQLite 而不改 `jetbox_summaries_proto.pb`，下次哪怕跑一句 `agy -p` 也会被瞬间刷回英文！**
* **明文注解文件**：`~/.gemini/antigravity-cli/annotations/<conversation_id>.pbtxt`，记录 `title:"..."`。

> 💡 **关键结论**：汉化脚本必须**四处同步更新**：SQLite（`title`、`preview`、`raw_summary` 字段 `1` 与 `15.1`）、`conversations_fts` 表头、`jetbox_summaries_proto.pb` 以及 `annotations/*.pbtxt`，才能彻底防止启动对账覆盖并在 `/resume` 列表与中文检索中同时生效。

---

## 终极解法：双轮驱动自动化

整套自动化机制由两个组件无缝联动，完全不需要人肉干预：

### 1. 批量汉化脚本（`scripts/agy-title-zh`）

仓库中的 [`scripts/agy-title-zh`](../scripts/agy-title-zh) 会自动备份数据库，筛选待汉化的纯英文 `title` / `preview` 与 `annotations/*.pbtxt`（跳过纯路径、URL 与斜杠命令），优先探测可用代理并支持直连回退，批量翻译成中文后原子性同步写回上述 SQLite 列、protobuf BLOB、FTS5 索引与 `.pbtxt` 文件。

随时可以手动试跑或全量执行：
```bash
# 仅试译统计，不落盘
agy-title-zh --dry-run -v

# 全量汉化（自动写一份 .bak 滚动备份）
agy-title-zh -v
```

### 2. 在 Wrapper 退出钩子中无感调用

最爽的姿势是让它在每次会话结束退出时**自动在后台静默跑**。在 `~/.local/overrides/agy`（即 [`scripts/agy-wrapper`](../scripts/agy-wrapper)）末尾挂载：

```sh
# 会话退出后在后台异步汉化会话标题，不阻塞终端
(
  if command -v agy-title-zh >/dev/null 2>&1; then
    agy-title-zh >/dev/null 2>&1
  elif [ -x "$HOME/.local/bin/agy-title-zh" ]; then
    "$HOME/.local/bin/agy-title-zh" >/dev/null 2>&1
  fi
) >/dev/null 2>&1 &

exit $RC
```

---

## 成果对比（治好了多年强迫症）

| 原生生成的英文标题 | 退出后自动汉化效果 |
| :--- | :--- |
| `Partner Meeting Calendar Update` | **合作伙伴会议日历更新** |
| `Dida Data Synchronization` | **嘀嗒数据同步** |
| `Ghostty AGY Font Color Issue` | **Ghostty 终端字体颜色问题** |
| `Conference Sponsorship Invoice Processing` | **大会赞助发票报销处理** |
| `PingCAP Wxcli Task Review` | **微信命令行工具任务复盘** |

现在每次敲 `/resume`，所有历史 CLI 会话都会显示清晰的中文标题，并同步支持 FTS 中文关键词筛选！
