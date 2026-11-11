# 09 · 隧道搭好了还是偶发报错？大概率是某个脚本悄悄绕开了 Wrapper

> **“隧道查了，是通的；公网 IP 查了，是美区 GCP 的；自己在终端手动敲命令测了一百次，次次成功。怎么放到某个自动化 Skill 里跑，就又抽风报 `User location is not supported`？！”**

如果你也遇到了这种“薛定谔的报错”，先别怀疑人生，**问题往往不在网络隧道本身，而是调用方在暗度陈仓，悄悄绕过了你辛辛苦苦配置的 Wrapper！**

---

## 案发现场：谁动了我的 PATH？

在 [Tip 06](06-dedicated-exit-ip.md) 中，我们让代理生效的手段是：
把 Wrapper 脚本放在 `~/.local/overrides/agy`，并利用 **PATH 环境变量的优先级**，让系统在解析命令 `agy` 时，先命中 Wrapper（注入专用代理），再由 Wrapper 去拉起真实的二进制文件。

**但这个逻辑有一个致命死穴：它只在“全量依赖 PATH 解析”时才管用！**

现实开发中，有两类场景会神不知鬼不觉地把它跳过去：

### 1. 脚本里图省事，硬编码了绝对路径
很多同学（或者自动生成的文档）为了防止环境报错，喜欢在 Python 或 Shell 脚本里写死路径：
```python
# 致命陷阱：很多人自以为很严谨的写法
AGY_BIN = shutil.which("agy") or "/Users/yourname/.local/bin/agy"
```
或者在 Shell 里写死：
```bash
/Users/yourname/.local/bin/agy -p "..."  # 直接死穴！
```
调用方直接越过了 `overrides`，直接去找真正的裸二进制。裸二进制身上**根本没有被注入任何 SOCKS5 代理环境变量**，于是请求一头撞向了本地默认网络，地区报错瞬间卷土重来！

### 2. 非交互 Shell（Cron / Launchd / Subprocess）的 PATH 根本没加载
这是另一个隐形大坑：在终端里敲命令是 Interactive Login Shell，你的 `~/.zshrc` 完整执行了，PATH 排序正确；  
但如果是被外部 Agent、定时任务（Cron）、或者 Python 的 `subprocess.run(..., shell=True)` 调起，它们起的是 **Non-Interactive Shell**，很多系统的初始 PATH 压根不包含 `~/.local/overrides`！

---

## 治本之策：显式探测，把优先权抢回来

不要寄希望于 `shutil.which` 或默认 PATH 行为。在任何需要调用 `agy` 的脚本或代码里，**显式把优先探测 `~/.local/overrides/agy` 写在第一位**！

### Python 稳健写法
```python
import os
import shutil
from pathlib import Path

# 显式把 override 目录排在第一优先级
_override = Path.home() / ".local" / "overrides" / "agy"
_real = Path.home() / ".local" / "bin" / "agy"

if _override.is_file() and os.access(_override, os.X_OK):
    AGY_BIN = str(_override)
else:
    AGY_BIN = shutil.which("agy") or str(_real)
```

### Shell 稳健写法
```bash
if [ -x "$HOME/.local/overrides/agy" ]; then
  AGY_BIN="$HOME/.local/overrides/agy"
else
  AGY_BIN="$(command -v agy || echo "$HOME/.local/bin/agy")"
fi
```

---

## 踩坑后的自查清单

凡是以后写到调起 `agy` 的工具、Skill、或者自动化脚本，自问这三句话：
- [ ] 代码里有没有写死 `~/.local/bin/agy`（裸二进制）？
- [ ] 是否存在 fallback 兜底直接落到了未代理的原生路径？
- [ ] 这一段调用会不会运行在纯非交互式环境（比如 CI、定时任务、或第三方 Agent 的 Bash 工具）中？

只要牢牢把住这道门，专用代理出口才能真正做到滴水不漏。

