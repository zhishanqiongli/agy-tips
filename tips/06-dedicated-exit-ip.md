# 06 · 给 agy 独开一条出口线路，彻底治好 "User location is not supported"

> **“跑着跑着，刚聊得好好的，突然甩出来一句冷冰冰的报错……”**

```text
FAILED_PRECONDITION: User location is not supported for the API use
```

最搞心态的是它的**间歇性**：同一个机场节点、同一个公网 IP，一轮对话里前三个请求返回得漂漂亮亮，第四个请求突然就被拒，整轮长任务直接被当头掐断！重开一轮可能又正常了，过十分钟又开始报错。

---

## 排查时走过的那些血泪弯路

1. **频繁切节点？** 没用！一口气换了 5 个不同的日本/美区节点，照样是那种让人抓狂的间歇性抽风。
2. **怀疑登录态过期了？** 并不是。同一时刻打开浏览器网页端正常使用，本地交互模式也能拉起。
3. **怀疑是 agy 客户端的 Bug？** 依然不是。同一条代理线路下的其他 Google 云端服务也会零星报地区受限。

---

## 真正元凶：共享机房 IP 的“薛定谔状态”

市面上绝大多数机场节点，都是几百上千人共用的一组数据中心机房 IP。

Google 的地理位置判定库对这类机房 IP 的态度是极其飘忽的：**同一个 IP，在不同网关或者短时间内，可能上一秒被判在可用区，下一秒就被标记成了受限或不可用区域**。换节点之所以没用，是因为同一家机场买的往往都是同一个 C 段的机房 IP，在 Google 眼里本质上全是一路货色。

> 💡 **解决真理**：只有独占、干净、物理归属清晰的自有服务器 IP，Google 对它的判定才是百分之百稳定不飘的！

---

## 架构思路：外科手术式定点导流

我们在一台海外云服务器上（腾讯云硅谷、AWS 或任何海外 VPS 均可）通过 SSH 动态转发，在本地拉起一个专用的 SOCKS5 代理端口（如 `7899`）。

**最关键的原则：只给 `agy` 单独用，机器上其他所有网络请求一切照旧！**

> **为什么不直接在终端里 `export https_proxy`？**  
> 那样会让这台电脑上的 `curl`、`git clone`、`npm install` 全部涌进这台小 VPS，那点小带宽瞬间被挤爆，完全得不偿失。外科手术式包装才是正解。

### 整套方案的四大零件

| 组件 | 对应文件 / 配置 | 核心职责 |
| :--- | :--- | :--- |
| **隧道脚本** | [`scripts/agy-tunnel`](../scripts/agy-tunnel) | 执行 `ssh -N -D 127.0.0.1:7899` 开本地代理，带 `up/down/status/ip` 命令 |
| **开机常驻** | [`scripts/agy-tunnel.plist.template`](../scripts/agy-tunnel.plist.template) | macOS launchd 守护服务，开机自启、掉线秒级自动重连 |
| **智能外壳** | [`scripts/agy-wrapper`](../scripts/agy-wrapper) | 伪装成 `agy`，在拉起真正二进制前注入专属代理环境变量 |
| **PATH 优先级** | `~/.zshrc` | 确保 overrides 目录排在 PATH 最前，盖过系统默认二进制 |

> [!TIP]
> **自带平滑降级机制**：如果某天海外 VPS 维护断了，Wrapper 会先探测 7899，不通则自动降级退回本机通用代理端口 7897，再不通则走直连，绝不直接让命令行瘫痪！

---

## 保姆级安装四步走

### 1. 配置服务器 SSH 免密（90% 的人卡在这）

隧道能否无人值守自愈，全靠 SSH 免密登录：

```bash
# 复制公钥到服务器
ssh-copy-id ubuntu@YOUR.SERVER.IP

# 终极验证：必须秒打印 ok，绝对不能弹密码输入框！
ssh -o BatchMode=yes -o ConnectTimeout=10 ubuntu@YOUR.SERVER.IP 'echo ok'
```

> **注意**：脚本启动时带了 `BatchMode=yes`，一旦需要弹窗输密码就会立刻退出。如果免密没配好，后台守护服务就会陷入“启动→报错退出→10秒后再启”的疯狂死循环。

### 2. 部署本地脚本

```bash
mkdir -p ~/.local/bin ~/.local/overrides
cp scripts/agy-tunnel  ~/.local/bin/agy-tunnel
cp scripts/agy-wrapper ~/.local/overrides/agy
chmod +x ~/.local/bin/agy-tunnel ~/.local/overrides/agy
```

修改 `~/.local/bin/agy-tunnel` 里的 `HOST=` 为你自己的服务器 SSH 连接串（例如 `ubuntu@1.2.3.4`）。

### 3. 安装 launchd 开机自启服务（macOS）

```bash
sed "s|__AGY_TUNNEL__|$HOME/.local/bin/agy-tunnel|" \
  scripts/agy-tunnel.plist.template > ~/Library/LaunchAgents/local.agy-tunnel.plist

launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.agy-tunnel.plist
launchctl kickstart -k gui/$(id -u)/local.agy-tunnel
```
*(如果是 Linux，配置一个 systemd user unit 即可)*

### 4. 把 Overrides 目录强行置顶 PATH（zsh）

把下面这段添加到你的 `~/.zshrc` **最末尾**：

```zsh
# agy 专用出口：~/.local/overrides 必须排 PATH 第一，才能用 wrapper 盖住真二进制。
export PATH="$HOME/.local/overrides:$PATH"
if [[ -o interactive ]]; then
  autoload -U add-zsh-hook 2>/dev/null
  _agy_overrides_path() { path=("$HOME/.local/overrides" ${path:#$HOME/.local/overrides}) }
  add-zsh-hook precmd _agy_overrides_path 2>/dev/null
fi
```

> **为什么还要挂一个 precmd 钩子？**  
> 因为很多工具（nvm、pyenv、甚至 Antigravity 自己的升级脚本）在执行时会悄悄往 PATH 最前面追加路径。加了这个 hook，每次终端显示提示符前都会自动把 overrides 抢回第一位，防止 Wrapper 被静默失效！

---

## 5 秒极速验收清单

按照以下顺序敲一遍，确认每一个返回：

```bash
# 1. 确认隧道存活，且出口是你的自有服务器
agy-tunnel status          # → 输出 ✓ 通道在 (127.0.0.1:7899)
agy-tunnel ip              # → 必须返回你 VPS 的公网 IP！

# 2. 确认后台守护服务正常跑着
launchctl print gui/$(id -u)/local.agy-tunnel | head -20   # → state = running

# 3. 确认敲 agy 命令命中是 Wrapper 而不是裸二进制
zsh -lic 'whence -p agy'
# → 必须输出 /Users/你的名字/.local/overrides/agy
```

配好之后，再跑长任务施工，任凭外网风吹雨打，`agy` 顺畅无阻！

