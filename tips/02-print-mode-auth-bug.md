# 02 · `agy -p` 命令行一跑就卡死？记 1.0.3 的凭证割裂 Bug（新版已修）

> **测试环境与现状**：原 Bug 实测于 `agy 1.0.3`（macOS，2026-05-31）。  
> **新版已修复**：在当前 `agy 1.5.5` 实测中，`agy -p` 已改由系统钥匙串静默鉴权（日志可见 `keyringAuth: loaded token` → `Print mode: silent auth succeeded`），不再依赖老旧的 `~/.gemini/oauth_creds.json`；且自 `1.1.13` 起也原生支持直接通过 `GEMINI_API_KEY` 环境变量鉴权。下文保留 `1.0.3` 时的排查实录，供排查旧版本或同类凭证割裂问题参考。

这绝对是每个想把 `agy` 接入工程化、跑自动化流水线的工程师都会撞上的第一个“幽灵 Bug”：

> **明明自己在终端敲 `agy` 进去交互聊天好好的，怎么一放到后台脚本、或者加个 `-p` 参数，就立刻开始疯狂弹认证超时？**

---

## 诡异的受灾现场

直接看报错，交互模式下丝般顺滑，但只要尝试**非交互式调用**，百分之百卡死：

```bash
$ agy --dangerously-skip-permissions -p "一句话：国内有哪些零代码平台？"
Authentication required. Please visit the URL to log in:
  https://accounts.google.com/o/oauth2/auth?...&client_id=1071006060591-...
Waiting for authentication (timeout 30s)...
Error: authentication timed out.
```

这个坑的打击面极其广泛，所有指望走后台静默调用的地方全军覆没：
* `agy -p` / `agy --print` 命令行脚本
* `agy-mcp`（其底层的 `mcp__agy__ask` 等工具其实就是 `agy -p` 的封装）直接陷入 600 秒超时
* Python / Node 里的任何 `subprocess` 自动化调用

---

## 刨根问底：凭证到底去哪了？

经过通宵抓包和排查，真相令人啼笑皆非：

> **`agy` 的 print 模式和交互模式，OAuth 凭证机制是割裂的！你在交互界面登录拿到的新 Token，根本不会落盘同步给 print 模式去读。**

### 抓包实锤证据链

```bash
# 1. 查看本地凭证文件：修改时间还停在远古时期，里面的 access_token 早就过期了
ls -la ~/.gemini/oauth_creds.json
python3 -c "import json,datetime as t; d=json.load(open('$HOME/.gemini/oauth_creds.json')); \
print('文件里的过期时间:', t.datetime.fromtimestamp(d['expiry_date']/1000))"

# 2. 但是看一下后台交互进程：人家明明活得好好的，而且正在顺畅地调 Google API！
ps aux | grep 'agy --dangerously' | grep -v grep
tail ~/.gemini/antigravity-cli/log/cli-*.log  # 看到发往 Google 的请求一切正常
```

**真正原因**：交互进程启动时，在**内存里**拿 `refresh_token` 换到了新的 `access_token`，自己用得很开心，**但它压根没把新 Token 写回 `~/.gemini/oauth_creds.json`！**

而 print 模式每次都是新起一个独立进程，一上来只能去读磁盘上那个老旧过期的 JSON 文件。读出来发现过期了，于是自作主张发起全新的 OAuth 流程——偏偏非交互模式下既没法弹浏览器，也没法等用户扫码，30 秒一到直接超时暴毙。

---

## 那些我们踩过、但**完全没卵用**的尝试

为了不让你走弯路，以下偏方可以直接省掉：
* ❌ **杀光进程重试**：把所有后台僵尸进程、agy-mcp 全杀干净，再跑 `agy -p` —— 照样弹浏览器认证。
* ❌ **运行 `agy update`**：提示已是最新版本 1.0.3，官方当时还没推补丁。
* ❌ **重新在交互模式里登录**：登录再多次，磁盘上 `oauth_creds.json` 的修改时间和内容依旧纹丝不动。
* ❌ **写脚本手动刷 Token**：试图自己拿 `refresh_token` 请求 Google OAuth 接口？直接被 Google 拒了并提示 `client_secret is missing`，因为 client_secret 硬编码在 Antigravity 二进制内部，外部拿不到。

---

## 应对策略与生存姿势

如果你当前停留在 1.0.3 版本上，必须正视现实：
1. **自动化 / MCP 深度调用暂缓**：非交互模式在修好前确实不可用，别在它身上死磕自动化流水线。
2. **需要急用 Gemini 怎么破**：如果业务非要跑代码自动化，只能暂时绕开 `agy`，走官方的 Gemini API（`generativelanguage.googleapis.com`）。**但请注意：那走的是 API Key 按 Token 付费，享受不到包月订阅的白嫖福利。**

---

## 如何验证你当前版本是否修好了？

当你更新了新版 CLI 后，不用写一堆复杂脚本，敲这一行就能秒测：

```bash
agy --dangerously-skip-permissions --print-timeout 60s -p "say hi"
```

* **如果秒回或者正常输出文本**：恭喜你，官方终于把 Token 刷回磁盘的逻辑修好了！
* **如果依然弹出 `Authentication required`**：说明凭证割裂的坑还在，继续保持关注。

