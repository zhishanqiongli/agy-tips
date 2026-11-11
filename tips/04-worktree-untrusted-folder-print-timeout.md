# 04 · 新目录 / Worktree 里秒超时？这不是认证挂了，是文件夹未信任

> **测试环境**：`agy`（macOS，2026-07-14 实测）。请注意：这与 [02 · print 模式认证失效](02-print-mode-auth-bug.md) **完全是两码事**，千万别搞混！

很多同学第一次用脚本跑自动化或者结合 `git worktree` 开新分支让 `agy` 施工时，都会被下面这个场面吓得不轻：

```bash
$ cd /path/to/repo/.worktrees/some-branch
$ agy --dangerously-skip-permissions --print-timeout 45m -p "帮我把这个测试修一下"
Error: timeout waiting for response
```

整整等了一分钟，终端里连一个字符都没打印，直接报超时退出。

更诡异的是：**明明登录账号是好的，代理也是好的，换回老目录跑同一句命令秒回，但只要一进新目录或者刚创建的 worktree 就瞬间暴毙**。

---

## 3 秒钟快速自测：你到底撞上了哪个坑？

遇到非交互模式卡死，先别急着去抓包或重新登录，用下面这个表格一分钟定性：

| 维度 | [Tip 02 认证失效 Bug](02-print-mode-auth-bug.md) | **本篇：文件夹未信任（真凶）** |
| :--- | :--- | :--- |
| **交互模式会弹什么？** | 弹 Google OAuth 网页登录链接 | 弹一个黄色/蓝色的**「是否信任此文件夹？」**确认框 |
| **换回以前跑过的老目录** | 依旧超时报错 | **立马正常返回！** ← 决定性判据 |
| **事故根因** | 内存 Token 未落盘 | 新目录的绝对路径不在信任白名单里 |
| **能否在本地搞定？** | 1.0.3 上改不了源码只能等官方 | **能！写两行脚本就地解决** |

> [!TIP]
> **黄金判据**：把卡住的这句 `agy -p ...` 复制到一个你以前天天用的老项目目录里跑一下。如果老目录能跑，新目录超时，那 100% 就是撞上了这篇讲的**文件夹未信任**。

---

## 刨根问底：为什么会悄无声息地卡住？

`agy` 内部维护了一张受信任工作区列表，保存在：

```text
~/.gemini/antigravity-cli/settings.json  →  "trustedWorkspaces": [ ... ]
```

这里的坑在于：**它是精确绝对路径匹配，完全不认父目录！**

即使你的家目录 `/Users/yourname` 或者项目根目录 `/Users/yourname/my-project` 早就被你信任过八百遍了，只要你为了隔离环境新建了一个 Git Worktree（比如 `/Users/yourname/my-project/.worktrees/feature-a`），在 `agy` 眼里这就是个全新且可疑的陌生路径。

* **在交互模式下**：它会老老实实弹一个对话框问你“是否信任该目录”。
* **在 `-p`（Print 模式）下**：因为没有交互界面，弹不出这个确认框，内部逻辑就傻傻地无限阻塞在那里，直到外层触发 `timeout`。
* **参数误区**：很多人以为加了 `--dangerously-skip-permissions` 就万事大吉，但那个参数**只管工具操作权限（改代码、跑终端），根本不管目录信任机制**，所以依然会被拒之门外！

---

## 彻底解决：起进程前，自动把路径塞进白名单

既然知道了它认的是 JSON 里的绝对路径，那我们在启动自动化任务前，用一段幂等的 Python 脚本把它自动写进去即可。

### 自动化流水线标准写法（写进你的 CI / 派活脚本）

```bash
TARGET_DIR="$(pwd)"  # 或者你要让 agy 施工的目标目录绝对路径
AGY_SETTINGS="$HOME/.gemini/antigravity-cli/settings.json"

if [ -f "$AGY_SETTINGS" ]; then
  python3 - "$AGY_SETTINGS" "$TARGET_DIR" <<'PY'
import json, sys
path, wt = sys.argv[1], sys.argv[2]
try:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
except Exception:
    d = {}

tw = d.setdefault("trustedWorkspaces", [])
if wt not in tw:
    tw.append(wt)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    print(f"已自动添加目录信任: {wt}")
PY
fi

# 之后再跑 agy -p，秒进，绝不再卡死！
agy --dangerously-skip-permissions -p "执行施工..."
```

---

## 一劳永逸方案：把自动信任烧录进日常 Shell 环境

如果你平时经常在终端里切换不同项目，烦透了每次进新目录都要敲回车点“信任”，可以直接在你的 `~/.zshrc` 或 `~/.bashrc` 里加一层静默的函数封装：

```bash
# 每次敲 agy 时，先静默把当前目录加入信任列表
_agy_trust_pwd() {
  local settings="$HOME/.gemini/antigravity-cli/settings.json"
  [[ -f "$settings" ]] || return 0
  python3 - "$settings" "$PWD" <<'PY' 2>/dev/null
import json, sys
path, wd = sys.argv[1], sys.argv[2]
try:
    with open(path, "r") as f:
        d = json.load(f)
    tw = d.setdefault("trustedWorkspaces", [])
    if wd not in tw:
        tw.append(wd)
        with open(path, "w") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
except Exception:
    pass
PY
}

agy() {
  case "$1" in
    acp|agent|agents|changelog|help|install|mcp|mic-serve|models|plugin|plugins|remote-control|update|-h|--help|-v|--version)
      command agy "$@" ;;          # 纯查询或协议子命令原样放行，不污染配置与参数
    *)
      _agy_trust_pwd                # 真正干活前，先把当前目录自动信任
      command agy --dangerously-skip-permissions "$@" ;;
  esac
}
```

### 为什么这版封装最安全？
1. **彻底静默**：执行失败也加了 `try/except` 和 `2>/dev/null`，绝不会因为读写配置失败导致 `agy` 本身起不来。
2. **区分命令**：查版本、查模型列表等原生子命令完全不碰信任列表。
3. **交互与后台通吃**：不管是自己敲终端还是脚本调用，只要走的是这个函数，全流程零弹窗打扰。

---

## 验证修复成果

随便找个从没创建过的临时测试目录：

```bash
mkdir -p /tmp/agy-trust-test && cd /tmp/agy-trust-test
# 运行测试命令
agy --dangerously-skip-permissions --print-timeout 60s -p "只回复两个字：通过"
```

* **终端返回“通过”**：说明信任注入成功，以后进新 worktree 再也不用担心秒超时！

