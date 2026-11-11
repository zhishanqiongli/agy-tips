# 15 · 多个终端同时开 agy 互相踢下线？排查 OAuth Token 刷新竞争导致 401

> **“任务跑到 80% 突然暴毙，我抓包排查了一整宿网络，结果罪魁祸首竟是我自己在其他窗口开着的僵尸终端！”**

看到终端里飘出这行毫无营养的报错时，绝大多数人的第一反应都是：**又断网了，或者代理节点被 Google 风控了**：

```text
Agent execution terminated due to error.
Error ID: 5346b817-...
```

> [!WARNING]
> 千万别傻乎乎拿那个 `Error ID` 去搜！那个 ID 是 **Google 服务端生成的链路追踪 ID**，在本地日志里搜一万遍也是查无此人。

真正的翻车真相，必须去翻本地原始日志：`~/.gemini/antigravity-cli/log/cli-*.log`（`agy` 默认就会把调试日志落盘，不用额外开参数）：

```text
E0828 16:07:00 errorreport.go:223] agent executor error: calling model:
  UNAUTHENTICATED (code 401): Request had invalid authentication credentials.
  Expected OAuth 2 access token, login cookie or other valid authentication credential.
```

看清楚：**HTTP 401 Unauthorized**！  
不是网络超时，不是 Connection Refused，底层网络隧道健康得不得了——而是在你的请求发出的那一微秒，**你的登录凭证刚刚被无情作废了**。

---

## 刨根问底：凭证全局共享，但刷新者有千千万

Antigravity CLI 在早期版本中曾把登录凭证保存在本地磁盘：

```text
~/.gemini/antigravity-cli/antigravity-oauth-token
```

而在新版（如 `agy 1.5.5` macOS 实测）中，OAuth 凭证已迁移至**系统钥匙串（Keyring）**中持久化（日志可见 `keyringAuth: loaded token`）。但无论落盘在文件还是钥匙串中，**当前登录账号的凭证对整机所有 `agy` 进程仍是同一份全局共享状态**！

每一个启动起来的 `agy` 进程，内部都会在后台按周期向 Google 刷新 Token。

翻开当时的并发日志，你会看到两个不同的终端实例在背地里疯狂打架（前面的数字是内部协程 ID）：

```text
I0828 11:06:19  70  browser.go:259] token refreshed, new expiry=12:06:18
I0828 12:06:18  70  browser.go:259] token refreshed, new expiry=13:06:17
I0828 13:06:29  13  browser.go:259] token refreshed, new expiry=14:06:28  <-- 实例 B 刷了新 Token
I0828 14:06:21  70  browser.go:259] token refreshed, new expiry=15:06:20  <-- 实例 A 用的老 Token 当场失效！
```

Google 的 OAuth 刷新机制是极其严格的：**一旦拿到了新的 Access Token，旧的马上作废！**  
于是悲剧发生了：
* 终端 A 正在辛辛苦苦施工写代码；
* 挂在后台 tmux 里早就被你遗忘的终端 B 到了刷新时间点，悄悄向 Google 换了新 Token；
* 终端 A 下一秒发请求调用模型，手里的 Token 已经是废纸一张，当场吃 401 暴毙！

当时去查后台进程，整个人都傻了：**机器上居然同时挂着 8 个活着的 `agy` 实例，其中两个已经在 tmux 的后台角落里默默挂了 29 个小时！**

---

## 排查过程中的两大经典天坑

### 1. 千万别用 `grep -i antigravity` 数进程
CLI 的二进制文件名字就叫 `agy`，执行 `ps aux | grep -i antigravity` 得到的结果是 0，会直接给你一种“我当前就开了一个进程，绝对不是多开”的致命幻觉。

**正确的抓鬼命令：**
```bash
ps -Ao pid,etime,%cpu,command | grep '[.]local/bin/agy '
```

### 2. 日志还在写 ≠ 有人类在用
这是最容易误判的陷阱！很多人以为“日志还在刷新说明有人在用”。错！`agy` 后台刷 Token 和上报配额的心跳协程每分每秒都在写日志，哪怕你离开电脑一天，它依然在疯狂写日志。

---

## 终极武器：编写进程看门狗脚本

为了彻底杜绝被暗箭射翻，仓库里专门编写了运维脚本 [`scripts/agy-ps`](../scripts/agy-ps)：

```bash
$ agy-ps
PID     存活时间       最后交互时间   工作目录          状态
13115   01-05:38:24   08-27 13:36   ~/coding/pay-svc   闲置 ← 可杀（回执已落盘）
92683   27:53         08-28 16:44   ~/coding/pay-svc   在用 · 正常施工中
26658   25:09         从未输入      ~/coding/pay-svc   在用
15381   07:49:19      08-28 09:18   ~/coding/auth-api  闲置 ← 可杀（已闲置 6 小时）
```

只要带上 `-k` 参数，就能一键把所有挂机无用的僵尸实例利索地清掉：
```bash
agy-ps -k
```

### 如何科学判断一个会话是否“闲置”？
* **看 CPU？** 错！agy 等你打字的时候 CPU 就是 0%。
* **看运行时长？** 错！很多大任务本来就要跑几个小时。
* **唯一可靠指标**：通过 `lsof` 找到进程绑定的日志句柄，抓取最后一次记录 `HandleUserInput`（人类在终端敲下回车）的时间戳。超过阈值没有人类输入的，才判定为挂机僵尸。

此外，我们在 [`scripts/agy-wrapper`](../scripts/agy-wrapper) 里加了一道防线：**每次启动新实例前，如果检测到并发实例数 ≥ 3，立即在终端弹出醒目的黄色警告**，把隐患扼杀在发生之前。

---

## 💡 给所有开发者的走心复盘

1. **`Agent execution terminated due to error` 只是句套话**：看到它千万别急着去怪网络或梯子，赶紧去翻 `cli-*.log` 里的真实堆栈。
2. **多开终端必遭反噬**：在本地 CLI 环境下，不要把 `agy` 当成无状态的云函数疯狂并发。没有做好隔离凭证前，尽量保持单会话专注，或者用异步队列串行跑。
3. **养成随手关会话的好习惯**：写完了敲 `/exit` 或 `Ctrl+D` 正常退出，不要老是直接把终端标签页一关了之。

