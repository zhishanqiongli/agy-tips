# 🚀 agy-tips：Google Antigravity CLI 踩坑与压榨指南

> **“一个月花了小两百买 Google AI Pro / Ultra 订阅，难道就只配在网页端打字聊天？”**  
> 当然不。我们的目标很单纯：把订阅自带的高级模型额度压榨到极致，能交给命令行自动化的活儿，绝不再人肉点一下。

本仓库记录了在实战中死磕 [Google Antigravity CLI](https://antigravity.google)（终端命令 `agy`）沉淀下来的**深度避坑指南、工程级自动化脚本以及多 Agent 协作工作流**。

所有的坑都是真金白银通宵踩出来的，所有的脚本都在 macOS / Linux 生产环境中日夜运转。希望能帮你省下几十个小时查各种奇怪报错的头发。

---

## 📚 踩坑与绝技目录

别按顺序硬啃，遇到哪个痛点直接点进去看：

### ⚡ 额度压榨与图片生成
* [01 · 用订阅额度白嫖画图，拒绝按量计费](tips/01-image-gen-with-subscription.md) —— 官方 SDK 只认 API key 扣费？教你直接走 CLI OAuth 免费跑 Nano Banana，一行命令搞定。

### 🛡️ 权限、认证与奇葩超时（新手必崩环节）
* [02 · `agy -p` 命令行一跑就卡死？记 1.0.3 的凭证割裂 Bug（新版已修）](tips/02-print-mode-auth-bug.md) —— 历史版本排查实录：旧版 `1.0.3` 交互与 print 模式凭证割裂（新版已切系统 Keyring 静默鉴权）。
* [03 · 别再问我要不要执行了！一键自动放行全部权限](tips/03-auto-approve-all-permissions.md) —— 支持在 `settings.json` 配 `"toolPermission": "always-proceed"`，也可用 Wrapper 注入 `--dangerously-skip-permissions`。
* [04 · 新目录 / Git Worktree 里秒超时？这不是认证挂了，是文件夹未信任](tips/04-worktree-untrusted-folder-print-timeout.md) —— 很多人排查几天都怀疑账号被风控，其实只要两行脚本把路径塞进 `trustedWorkspaces`。
* [15 · 多个终端同时开 agy 互相踢下线？排查 OAuth Token 刷新竞争](tips/15-multiple-instances-refresh-token-race-401.md) —— 并行开两三个实例干活，结果全部 401 掉线？教你用守护进程清理闲置实例。

### 🤖 混合双打：Claude Code 与 agy 施工协同
* [05 · 「施工模式」最佳实践：Claude 出脑力写卡，agy 出劳力搬砖](tips/05-claude-drives-agy-construction-mode.md) —— 让贵的 Claude 做架构和验收，让包月的 agy 闷头写代码，双剑合璧省下成千上万 Token。
* [10 · 让 Claude Code 和 agy 共享项目上下文：AGENTS.md 单一真相源](tips/10-agents-md-shared-project-context.md) —— 两个 Agent 轮流改代码怎么不打架？教你用一套规则文件统一认知。

### 🌐 专用出口与网络治理（专治地区不支持）
* [06 · 给 agy 独开一条出口线路，彻底治好 "User location is not supported"](tips/06-dedicated-exit-ip.md) —— 机场节点跳来跳去总被 Google 掐断？搭一条轻量级 SSH SOCKS5 专用通道给 agy。
* [08 · 换了独享 IP 怎么还报错？Google 查的是 ASN 归属，别被机房骗了](tips/08-exit-ip-asn-not-just-dedicated.md) —— 为什么某些云厂商的 IP 会被 Google 判定为不可用？教你挑对真正干净的线路。
* [09 · 隧道搭好了还是偶发报错？大概率是某个脚本悄悄绕开了 Wrapper](tips/09-callers-must-use-the-wrapper-not-the-binary.md) —— PATH 覆盖顺序与子进程继承代理的那些暗坑。
* [13 · 隧道偶尔断一次任务就全挂？解决重启真空期与 22 端口偶发黑洞](tips/13-tunnel-restart-gap-and-ssh22-blackhole.md) —— 用 gost 配合本地端口转发实现平滑重试。
* [14 · 隧道没断但 agy 慢如蜗牛？单条 SSH 队头阻塞排查与多路复用](tips/14-tunnel-slow-not-broken-hol-blocking.md) —— 排查 SSH 隧道拥塞控制的实战经验。

### 🎨 终端体验与舒适度调优
* [07 · 终端 Markdown 渲染与排版避坑：为什么会看到 #### 与最佳排版姿势](tips/07-terminal-markdown-rendering.md) —— 治好终端乱码、错位和原生语法不解析的强迫症。
* [11 · 自定义状态栏：一眼看清当前模型、执行模式、剩余上下文与额度](tips/11-custom-statusline.md) —— 抄作业！三行信息清清楚楚，不用手动敲命令探查。
* [12 · 汉化 /resume 会话列表：同步回写 SQLite、Proto Store 与注解](tips/12-auto-translate-resume-titles.md) —— 原生生成的全是英文短句？退出时自动翻译成中文并防止启动对账还原。
* [16 · 隐藏 /resume 中的 magpie-agy-bridge 临时会话（附启动对账避坑）](tips/16-hide-magpie-bridge-sessions-and-dual-store.md) —— 清理 0 步探测与纯临时桥接会话，剥离双工作区里的临时路径。

---

## 🛠️ 开箱即用的实用脚本

所有脚本都在 [`scripts/`](scripts/) 目录下，经过实战检验：

| 脚本文件 | 解决什么问题 | 对应文档 |
| :--- | :--- | :--- |
| [`statusline.sh`](scripts/statusline.sh) | **终端状态栏神器**：显示模型、余量、5h/7d 额度、任务一句话标题 | [Tip 11](tips/11-custom-statusline.md) |
| [`genimg.sh`](scripts/genimg.sh) | **一行命令画图**：走订阅额度，直接生成图片并保存到桌面 | [Tip 01](tips/01-image-gen-with-subscription.md) |
| [`agy-do`](scripts/agy-do) | **任务卡施工派发器**：Git Worktree 隔离 + 逃逸检测 + 自动异步验收 | [Tip 05](tips/05-claude-drives-agy-construction-mode.md) |
| [`agy-runs`](scripts/agy-runs) | **施工看板**：列出后台正在跑的施工任务、待验收及报错日志 | [Tip 05](tips/05-claude-drives-agy-construction-mode.md) |
| [`agy-wrapper`](scripts/agy-wrapper) | **智能包装层**：自动注入免授权 flag、专用出口代理、隐藏桥接会话与标题汉化 | [Tip 03](tips/03-auto-approve-all-permissions.md) / [Tip 06](tips/06-dedicated-exit-ip.md) |
| [`agy-tunnel`](scripts/agy-tunnel) | **出口隧道守护**：自建 SOCKS5 代理管理（启动/停止/状态检测/公网 IP 校验） | [Tip 06](tips/06-dedicated-exit-ip.md) |
| [`agy-ps`](scripts/agy-ps) | **进程卫士**：检测活跃与僵尸 agy 进程，避免多实例竞争刷崩 OAuth Token | [Tip 15](tips/15-multiple-instances-refresh-token-race-401.md) |
| [`agy-hide-bridge`](scripts/agy-hide-bridge) | **隐藏桥接临时会话**：移出 0 步探测与纯临时 bridge 会话，剥离双工作区临时路径（共用 [`_agy_pb.py`](scripts/_agy_pb.py)） | [Tip 16](tips/16-hide-magpie-bridge-sessions-and-dual-store.md) |
| [`agy-title-zh`](scripts/agy-title-zh) | **会话标题汉化**：支持 CLI 与桌面端离线批量汉化 `conversation_summaries.db`、`*_summaries_proto.pb` 与 `annotations/`（共用 [`_agy_pb.py`](scripts/_agy_pb.py)） | [Tip 12](tips/12-auto-translate-resume-titles.md) |
| [`check-upstream.sh`](scripts/check-upstream.sh) | **上游更新探测**：安全抓取 `upstream` 变更清单而不覆盖本地改造 | [UPSTREAM_SYNC](UPSTREAM_SYNC.md) |

---

## 💡 几个走心的人生建议（前车之鉴）

1. **别相信大模型的自我检查报告**：agy 跑完任务说“全部测试已通过”千万别信，它偷懒时也这么写。在任务卡里必须写明具体测试命令，让宿主环境或外部脚本用退出码说话。
2. **多开终端时悠着点**：Google 对 CLI 端的 OAuth Token 刷新有一套锁机制，开三四个终端同时跑容易互相打架，瞬间触发 401 全体暴毙。多任务建议用异步任务队列跑。
3. **把新目录信任当成第一反射**：如果你在脚本里调用 `agy -p` 莫名卡住没反应，先别急着抓包看网络，90% 是这个目录没在 `trustedWorkspaces` 里！

---

## 🤝 参与贡献

欢迎提 Issue 和 PR！如果你也挖掘出了新的骚操作，欢迎把心得整理到 `tips/NN-标题.md`，并在本 README 中加入索引。

