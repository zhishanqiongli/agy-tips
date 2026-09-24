# 11 · 自定义状态栏：一眼看清当前模型、执行模式、剩余上下文与额度

> **测试环境**：`agy`（Antigravity CLI），`settings.json` 原生支持 `statusLine` 配置项，macOS / Linux 实测有效（2026-08-15）。

在命令行里用 Agent 写代码，最让人心慌的就是**盲盒体验**：
* 对话跑了十几轮，上下文到底吃了百分之多少了？会不会马上被截断？
* 当前到底切到了哪个模型？推理强度是 Low 还是 High？
* 这个月的 Google 订阅额度还剩多少？距离下一次配额重置还有多久？

每次想知道都要停下来敲命令查一下，极其败兴。其实 `agy` 早就藏了一个强大的**状态栏自定义钩子**，抄一下这份作业，你的终端底部能立刻变成极度舒服的战情监控板！

---

## 最终效果预览

每次终端刷新，底部都会常驻三行清晰、优雅的彩色状态栏：

```text
macbook-pro · ~/Documents/my-project (git:main*)
3.7 Flash · exec med skip · ctx 95% · 5h 93% ~02:44 · 7d 92%
正在重构订单支付超时自动关闭逻辑
```

* **第一行（主机与位置）**：机器名 · 当前工作目录（带 Git 分支名与修改标记，颜色清晰区分）。
* **第二行（核心战情）**：模型简称 · 执行模式（exec/plan/accept） + 推理强度（low/med/high） + 权限沙箱状态 · 当前会话上下文剩余百分比 · 5 小时内配额余量与恢复时间点 · 7 天额度大盘。
* **第三行（会话焦点）**：当前任务一句话摘要（与 Claude Code 会话联动，切司机也不丢焦点）。

---

## 30 秒配置指南

在你的全局配置文件 `~/.gemini/antigravity-cli/settings.json` 中加入这一段：

```json
{
  "statusLine": {
    "type": "command",
    "command": "/Users/xiaochen/github/agy-tips/scripts/statusline.sh"
  }
}
```

> [!NOTE]
> **底层运作机制**：  
> 每当 Agent 状态有更新（执行了一次命令、生成了一段回复），`agy` 就会把包含了 `model`、`context_window`、`quota`、`mode`、`workspace` 等信息的 JSON 状态包，通过标准输入（`stdin`）喂给你的脚本。你的脚本只需要从标准输出（`stdout`）打印拼好的字符串，CLI 就会负责渲染到底部。

---

## 脚本核心设计精粹

完整可以直接拿去用的脚本见 [`scripts/statusline.sh`](../scripts/statusline.sh)，里面的几个细节值得品味：

1. **自动提取精简模型名**：原始字段返回的是冗长的 `"Gemini 3.7 Flash (Medium)"`，脚本用 `sed` 顺滑地剔除了厂商前缀和括号说明，在狭窄的终端里只留核心字眼 `3.7 Flash`。
2. **上下文余量实时换算**：从 `.context_window.remaining_percentage` 拿到浮点数，自动四舍五入为直观的百分比整数。
3. **额度预警与恢复倒计时**：读取 `.quota["gemini-5h"]` 和 `.quota["gemini-weekly"]`，把秒级时间戳直接换算成“几点几分恢复”，打工人再也不用自己心算时差。
4. **CJK（中日韩）字符宽度对齐**：中文在终端里占 2 个字符宽度，直接按字节或者字符截断会导致排版错位甚至截出乱码。脚本里实现了一个小巧的 `cw`（char width）函数，按照 Unicode 编码区间判断全角/半角，优雅截断。
5. **双司机联动（Claude Code 协同）**：读取 `~/.claude/session-title/<session_id>` 文件，无论你这一轮是用 Claude 规划还是用 agy 施工，状态栏上的那一句话任务标题始终同步！

---

## 为什么强烈推荐这套实现？

* **极致轻量，零外部重依赖**：除了 `jq`（`brew install jq`）之外，全部采用 POSIX 纯 Shell 内置能力编写，无论是本地 Mac 还是远端 Linux 服务器，考过去就能跑。
* **协议双向兼容**：同时兼容 agy 原生的 `quota.gemini-*` 与 Claude Code 风格的 `rate_limits.*` 字段，一处编写，两处复用。
* **原生 ANSI 转义色彩**：手写 ANSI 颜色码，不依赖任何第三方 Python 库或终端能力探测，兼容各种黑白灰终端与现代 GPU 终端。

