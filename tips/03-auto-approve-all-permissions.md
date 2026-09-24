# 03 · 别再问我要不要执行了！一键自动批准全部权限

> **测试环境**：`agy`（Antigravity CLI），macOS 实测 2026-07-08。

用 AI 辅助写代码本该是享受，但如果它改三个文件就要停下来问你三次确认，简直能把人逼疯：

```text
Accept this file edit?
> 1. Yes, accept this change
  2. No, reject this change
```

重构一个模块动辄十几二十个文件，你只能像个毫无感情的打卡机器一样坐在电脑前疯狂敲回车点 `Yes`。要是想去泡杯咖啡让它自己跑后台无人值守？对不起，它改完第一个文件就卡在那等你了。

---

## 临时解法：命令行挂全局 Flag

其实官方藏了一个全局参数（敲 `agy --help` 可以翻到）：

```text
--dangerously-skip-permissions   Auto-approve all tool permission requests without prompting
```

单次运行加上它，整个会话立刻丝般顺滑，所有的文件修改、命令执行全部自动放行，绝不再弹窗打扰：

```bash
agy --dangerously-skip-permissions -i "帮我重构这个模块的所有网络请求"
```

> [!NOTE]
> **别搞混了**：还有一个弱一点的参数叫 `--mode accept-edits`，它**仅对文件修改**自动批准，一旦模型想要执行测试命令或者建文件夹，依然会跳出来问你。要想彻底解放双手，认准 `--dangerously-skip-permissions`。

---

## 终极解法：写个 Wrapper 彻底告别手敲

谁愿意每次开终端都敲这么长一串字母？最省心的姿势就是写个轻量的 Shell Wrapper，把系统原生的 `agy` 替换成**永远默认带这个参数**的版本。

思路很简单：在 PATH 前面加一个优先目录（例如 `~/.local/overrides`），把真二进制放到 `~/.local/bin/agy-real`，然后在 `~/.local/overrides/agy` 放如下脚本：

```bash
#!/bin/sh
# agy wrapper：默认自动批准所有工具权限，别每一步都停下来问！
# 已经手动带该 flag 时不重复注入；子命令（models/update/plugin…）也能安全透传

case " $* " in
  *" --dangerously-skip-permissions "*)
    exec "$HOME/.local/bin/agy-real" "$@" ;;
  *)
    exec "$HOME/.local/bin/agy-real" --dangerously-skip-permissions "$@" ;;
esac
```

别忘了给它加上执行权限：
```bash
chmod +x ~/.local/overrides/agy
```

### 这个脚本的精妙之处

1. **自动去重**：哪怕你的其他自动化脚本里显式传了 `--dangerously-skip-permissions`，正则匹配也不会重复塞入两次导致参数解析异常。
2. **位置靠前，子命令零报错**：flag 放在参数最前，`agy models`、`agy update` 这种子命令依然可以完美识别，完全不会冲突报错。
3. **一次配置，全家桶生效**：不管是终端手动交互模式，还是 `agy -p` 批处理模式，抑或是被 Claude 等外部工具派发施工，只要调用 `agy`，全部自动继承全自动批准策略！

验证是否生效：
```bash
agy models  # 能正常输出模型列表，说明 wrapper 工作正常且没打断子命令
```

---

## 很多人好奇：为什么不能在某个 JSON 配置里改？

我也去翻过源码和配置文件。遗憾的是，`agy` 目前根本没有提供明文的全局权限配置项。它的权限记忆是按照会话分别保存在 **Protobuf 二进制文件**（`~/.gemini/antigravity-cli/implicit/*.pb`）里的，根本没有一个类似于 `settings.json -> "autoApprove": true` 的全局布尔开关。

因此，上面这套 **PATH 拦截 + Wrapper 注入** 是目前最干净、最稳定的唯一通用解法。

---

## ⚠️ 泼点冷水：风险一定要心里有数

参数名叫 `dangerously` 真的不是官方跟你开玩笑。

一旦启用，**模型获得的是你终端的完全行动权**。它要是看某个文件夹不爽执行了 `rm -rf`，或者手抖把关键环境文件覆盖了，可没人按暂停键。

* **安全适用场景**：你明确信任当前项目的上下文、在独立的 Git Worktree / 临时分支里施工、或者是在全自动测试沙箱中。
* **双重保险建议**：可以同时配合 `--sandbox` 参数（在终端隔离沙盒中运行），或者只在特定代码项目内配置该 Wrapper，避免波及日常全局环境。

