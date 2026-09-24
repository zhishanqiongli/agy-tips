# 12 · 汉化 /resume 英文会话标题：包装层退出时自动异步回写 SQLite

> **强迫症日常崩溃现场**：明明你从头到尾都在用字正腔圆的中文跟 `agy` 对话，某天敲开 `/resume` 想要找回之前的上下文接着写代码，结果终端列表里弹出来的一水儿全是长串英文大写标题（比如 `Partner Meeting Calendar Update`、`Database Connection Pool Refactor`）……在终端里靠中文拼音搜索毛都搜不到，找个会话全靠肉眼硬翻译。

---

## 刨根问底：为什么死活不给中文标题？

扒了一下网络请求与日志，发现这是 Google 后端写死的“霸王条款”：
每当一个会话完成首轮对话后，`agy` 会调用远端的总结接口（`GetCascadeConversationTitle`）生成会话概括。该服务的 Prompt 硬编码了必须返回“3-5 个词的英文 Title Case 短语”。客户端设置里完全没有提供任何语言切换的选项。

---

## 侦探突破口：发现本地 SQLite 数据库

既然远端接口改不了，那本地缓存呢？

排查发现，`agy` 在本地为所有历史会话建了一个非常规整的 SQLite 数据库：
* **文件路径**：`~/.gemini/antigravity-cli/conversation_summaries.db`
* **核心数据表**：`conversation_summaries`
* **关键字段**：`preview`（正是每次敲 `/resume` 时渲染在列表里、且用来接收键盘模糊搜索的标题字符串！）

> 💡 **灵光一闪**：只要把 SQLite 里的 `preview` 字段替换成中文，`/resume` 界面就会立刻全部显示为中文，而且敲中文首字母或者汉字就能秒级过滤匹配！

---

## 终极解法：双轮驱动自动化

整套自动化机制由两个组件无缝联动，完全不需要人肉干预：

### 1. 轻量级批量翻译脚本（`scripts/agy-title-zh`）

仓库中的 [`scripts/agy-title-zh`](../scripts/agy-title-zh) 会自动连接数据库，筛选出尚未翻译的纯英文 `preview` 标题，毫秒级调取翻译接口换成地道中文，然后原子性写回 SQLite。

随时可以手动跑一次，清洗现有的全部历史记录：
```bash
agy-title-zh -v
```

### 2. 在 Wrapper 退出钩子中无感调用

最爽的姿势是让它在每次会话结束退出时**自动在后台静默跑**。把这一段挂进我们的 `~/.local/overrides/agy`（即 `scripts/agy-wrapper`）：

```bash
# ~/.local/overrides/agy 末尾
set -- ${ADD_DIR:+--add-dir "$ADD_DIR"} "$@"
case " $* " in
  *" --dangerously-skip-permissions "*) "$REAL" "$@" ;;
  *) "$REAL" --dangerously-skip-permissions "$@" ;;
esac
RC=$?

# 会话正常退出后，在后台悄悄拉起汉化脚本，零等待、不卡终端
( which agy-title-zh >/dev/null 2>&1 && agy-title-zh >/dev/null 2>&1 & )

exit $RC
```

---

## 成果对比（治好了多年强迫症）

| 原生 Google 生成的英文标题 | 退出后自动汉化效果 |
| :--- | :--- |
| `Partner Meeting Calendar Update` | **合作伙伴会议日历更新** |
| `Dida Data Synchronization` | **嘀嗒数据同步** |
| `Ghostty AGY Font Color Issue` | **Ghostty 终端字体颜色问题** |
| `Conference Sponsorship Invoice Processing` | **大会赞助发票报销处理** |
| `PingCAP Wxcli Task Review` | **微信命令行工具任务复盘** |

现在每次敲 `/resume`，所有的历史会话清清楚楚，支持拼音模糊搜索，再也不用在一堆英文专有名词里抓瞎了！

