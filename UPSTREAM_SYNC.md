# 上游更新与安全入库工作流 (Upstream Sync & Ingestion Guide)

## 📌 背景与核心原则

本仓库已切换为个人维护版本：
- **`origin`**：个人 GitHub 仓库（用于保存本地定制文档、自动化脚本与后续新增技巧）
- **`upstream`**：原作者上游仓库（`https://github.com/andyleimc-source/agy-tips.git`）

为了保护本地的定制成果与知识库体系：
> [!IMPORTANT]
> **切勿直接执行 `git pull upstream main` 或盲目合并 `upstream/main`！**
> 任何来自上游的更新，都必须经过**「只抓取 → 比对差异 → 按需挑选 → 本地化润色 → 正式入库」**的流程。

> [!TIP]
> **首次从上游仓库切换为个人维护时的一次性 Remote 配置**：
> ```bash
> git remote rename origin upstream
> git remote add origin <你的个人 GitHub 仓库 URL>
> ```

---

## 🛠️ 标准入库四步法

### 第一步：抓取上游元数据（安全无害）
仅同步上游引用，绝不触碰本地工作区和文件：
```bash
git fetch upstream
```

### 第二步：审查上游变更
检查上游是否有新提交，以及具体变动了哪些文件：
```bash
# 1. 查看上游有哪些新提交（本地没有的）
git log HEAD..upstream/main --oneline

# 2. 查看涉及变更的文件清单与统计
git diff --stat HEAD..upstream/main
```
- 若两行命令**均无输出**：说明上游无新内容，本地已同步。
- 若有输出：记录下新增或变动的文件列表。

---

### 第三步：针对性入库处理（核心步骤）

根据变更类型，采取不同的入库方式：

#### 场景 A：上游新增了新技巧（如 `tips/17-xxx.md`）或新脚本
直接从上游分支中**单独检出**该文件，不影响其他文件：
```bash
# 单独提取新增的文件
git checkout upstream/main -- tips/17-新技巧名称.md
git checkout upstream/main -- scripts/新脚本.sh
```
**入库重构与润色标准**：
1. 补充 `> **场景**：...` 核心痛点与背景引言。
2. 保持层级分明（使用清晰的小标题、代码块与关键警示语法）。
3. 将新条目同步登记到 [README.md](README.md) 的「踩坑与绝技目录」或「开箱即用脚本表格」中。

#### 场景 B：上游修正了已有脚本或文档（Bugfix）
查看具体代码或内容的改动差异：
```bash
# 查看某个文件的具体改动细节
git diff HEAD..upstream/main -- scripts/agy-wrapper
```
**入库标准**：
- 如果是脚本逻辑 Bug 修复，将关键代码补丁合并到本地对应脚本。
- 如果是踩坑知识补充，在本地对应文档中保留本地风格并追加该知识点。

---

### 第四步：完成入库提交并推送个人库
整理完成后，提交并推送到你的 `origin`：
```bash
git add tips/ README.md scripts/
git commit -m "sync: 入库上游更新 (Tip XX / 脚本修正)"
git push origin main
```

---

## ⚡ 快捷检查命令

您也可以直接运行快捷检测脚本（默认检测 `upstream`，可通过 `AGY_TIPS_UPSTREAM_REMOTE` 覆盖）：
```bash
./scripts/check-upstream.sh
```
该脚本会自动拉取 `upstream` 并分析是否有待入库的新文档、新脚本或提交。
