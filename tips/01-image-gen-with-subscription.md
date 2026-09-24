# 01 · 用订阅额度白嫖画图，拒绝按量计费

> **场景**：手里明明买了 Google AI Pro / Ultra 的订阅，每个月大把额度闲着。想在脚本或者项目自动化里调用顶级生图模型（Nano Banana），却不想再去 Google Cloud 绑信用卡买按量扣费的 API Key——这冤枉钱咱们一分都不花，直接薅订阅本身的额度！

---

## 为什么不能用官方 SDK？

很多人第一反应是去装官方的 `google-antigravity` Python SDK。结果一翻文档心凉半截：

> 官方 SDK **只支持通过 `GEMINI_API_KEY` 鉴权**。

只要传了 API Key，每一张图都是真金白银走账单。**走 SDK 这条路，你的订阅等于白买，根本省不了钱。**

想要合法合规复用现有的订阅包月额度，唯一的合法通道就是 **CLI 工具（`agy`）**。因为 CLI 支持通过 OAuth 绑定你的个人订阅账号。

---

## 核心招式：一行命令自动出图

不用开 GUI，直接在终端里敲这一行：

```bash
agy -p "生成一张 1024x1024 的小狗照片，背景蓝色渐变，保存到 ~/Desktop/dog.png" \
    --dangerously-skip-permissions
```

### 关键参数解析（少一个都跑不通）

| 参数 | 为什么必须加？ |
| :--- | :--- |
| `-p` / `--print` | **非交互模式（Print Mode）**。让 agy 接收到 Prompt 之后闷头干活，出完图立刻退出来，不要停在输入框里等你聊天。 |
| `--dangerously-skip-permissions` | **灵魂所在，千万不能漏！** agy 在准备写文件或者调生图工具时，默认会停下来弹提示问你 `[Y/n]`。非交互模式下终端没有人类去敲回车，漏了这个参数它就会一直在那干等，直到 30 秒超时暴毙。 |

---

## 动手前的前置检查（避坑第一步）

别急着跑脚本，先花 10 秒钟确认两件事：

```bash
# 1. 确认你当前登录的是个人订阅账号（OAuth），而不是配了 API Key
agy plugin list

# 2. 检查生图插件装上没（默认安装包可能没勾选 Nano Banana）
agy plugin list | grep -iE "image|banana|nano"
```

> [!TIP]
> 如果第 2 步查出来空空如也，别慌：打开 Antigravity 的桌面客户端，去 **Plugin Marketplace**（插件市场）搜索 **Nano Banana** 点击安装，CLI 会自动共享这个插件配置。

---

## 懒人福利：封装成开箱即用的 Shell 脚本

每次手敲这一大长串太累？仓库里已经帮你封装好了 [`scripts/genimg.sh`](../scripts/genimg.sh)：

```bash
./scripts/genimg.sh "日落时分的赛博朋克霓虹城市，雨后街道倒影" ./out/cyberpunk.png
```

在日常业务代码里也可以直接通过子进程调用，非常丝滑：

**Node.js 调用姿势：**
```js
const { execSync } = require('child_process');
execSync(`~/scripts/genimg.sh "${prompt}" "${outPath}"`);
```

**Python 调用姿势：**
```python
import subprocess
subprocess.run(["~/scripts/genimg.sh", prompt, out_path], check=True, shell=False)
```

---

## 💡 几个走心的血泪教训

1. **别以为买了 Ultra 就能无限刷图**：Nano Banana Pro 在 2026 年 2 月收紧过配额策略，生图有独立的每日配额上限。即使你掏了 $200/月，拿它当批量爬虫图库刷也是会被暂时限流的，合理安排任务间隔。
2. **服务器 / CI 上跑怎么办**：服务器没有图形界面没法扫码登录。通常的做法是在本地 Mac/Linux 机器上登录好，把凭证目录（`~/.gemini/antigravity-cli/` 等）直接打包 scp 过去。注意 Token 有效期，过期还是需要刷新。
3. **安全警示**：`--dangerously-skip-permissions` 虽然爽，但它是把最高权限交给了模型。如果是在线上服务中接收不可信用户的 Prompt，千万做好敏感词与路径注入过滤，别让模型顺手帮你把系统文件给删了。

