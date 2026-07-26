# Git 命令速查手册

---

## 目录

1. [仓库操作命令](#1-仓库操作命令)
2. [工作区与暂存区命令](#2-工作区与暂存区命令)
3. [分支操作命令](#3-分支操作命令)
4. [远程仓库命令](#4-远程仓库命令)
5. [提交与日志命令](#5-提交与日志命令)
6. [撤销与回退命令](#6-撤销与回退命令)
7. [合并与变基命令](#7-合并与变基命令)
8. [标签操作命令](#8-标签操作命令)
9. [配置与帮助命令](#9-配置与帮助命令)
10. [其他常用命令](#10-其他常用命令)

---

## 1. 仓库操作命令

| 命令 | 功能说明 | 示例 |
|------|----------|------|
| `git init` | 在当前目录初始化新的 Git 仓库 | `git init` |
| `git clone <url>` | 克隆远程仓库到本地 | `git clone https://github.com/user/repo.git` |
| `git clone <url> <dir>` | 克隆到指定目录 | `git clone https://github.com/user/repo.git my-project` |
| `git init --bare` | 创建裸仓库（用于共享服务器） | `git init --bare repo.git` |

---

## 2. 工作区与暂存区命令

| 命令 | 功能说明 | 示例 |
|------|----------|------|
| `git status` | 查看工作区和暂存区状态 | `git status` |
| `git status -s` | 简洁模式查看状态 | `git status -s` |
| `git diff` | 查看工作区与暂存区的差异 | `git diff` |
| `git diff <file>` | 查看指定文件的差异 | `git diff index.html` |
| `git diff --cached` | 查看暂存区与 HEAD 的差异 | `git diff --cached` |
| `git add <file>` | 将指定文件添加到暂存区 | `git add README.md` |
| `git add .` | 添加所有改动（不含删除） | `git add .` |
| `git add -A` | 添加所有改动（含删除） | `git add -A` |
| `git add -u` | 添加已跟踪文件的改动 | `git add -u` |
| `git reset HEAD <file>` | 将文件从暂存区撤回 | `git reset HEAD README.md` |
| `git restore <file>` | 撤销工作区修改（Git 2.23+） | `git restore index.html` |
| `git restore --staged <file>` | 撤销暂存区修改（Git 2.23+） | `git restore --staged index.html` |
| `git clean -f` | 删除未跟踪的文件 | `git clean -f` |
| `git clean -df` | 删除未跟踪的文件和目录 | `git clean -df` |

---

## 3. 分支操作命令

| 命令 | 功能说明 | 示例 |
|------|----------|------|
| `git branch` | 列出本地分支 | `git branch` |
| `git branch -a` | 列出所有分支（含远程） | `git branch -a` |
| `git branch -v` | 显示分支及最后提交 | `git branch -v` |
| `git branch -vv` | 显示分支与远程追踪关系 | `git branch -vv` |
| `git branch <name>` | 创建新分支 | `git branch feature/login` |
| `git branch -d <name>` | 删除已合并的分支 | `git branch -d feature/login` |
| `git branch -D <name>` | 强制删除分支 | `git branch -D feature/login` |
| `git checkout <branch>` | 切换到指定分支 | `git checkout main` |
| `git checkout -b <name>` | 创建并切换到新分支 | `git checkout -b feature/payment` |
| `git checkout -b <name> <remote>/<branch>` | 基于远程分支创建本地分支 | `git checkout -b feature/dev origin/develop` |
| `git switch <branch>` | 切换分支（Git 2.23+） | `git switch main` |
| `git switch -c <name>` | 创建并切换分支（Git 2.23+） | `git switch -c feature/new` |
| `git branch -m <old> <new>` | 重命名分支 | `git branch -m feature/login feature/auth` |
| `git branch --move <old> <new>` | 强制重命名分支 | `git branch --move old-name new-name` |

---

## 4. 远程仓库命令

| 命令 | 功能说明 | 示例 |
|------|----------|------|
| `git remote` | 列出远程仓库 | `git remote` |
| `git remote -v` | 列出远程仓库及 URL | `git remote -v` |
| `git remote add <name> <url>` | 添加远程仓库 | `git remote add origin https://github.com/user/repo.git` |
| `git remote rename <old> <new>` | 重命名远程仓库 | `git remote rename origin upstream` |
| `git remote remove <name>` | 删除远程仓库 | `git remote remove origin` |
| `git remote show <name>` | 显示远程仓库详细信息 | `git remote show origin` |
| `git fetch <remote>` | 拉取远程仓库更新（不合并） | `git fetch origin` |
| `git fetch <remote> <branch>` | 拉取指定分支 | `git fetch origin main` |
| `git pull <remote> <branch>` | 拉取并合并指定分支 | `git pull origin main` |
| `git pull --rebase <remote> <branch>` | 拉取并变基 | `git pull --rebase origin main` |
| `git push <remote> <branch>` | 推送到远程分支 | `git push origin main` |
| `git push -u <remote> <branch>` | 推送并设置上游追踪 | `git push -u origin feature/login` |
| `git push --force <remote> <branch>` | 强制推送（覆盖远程） | `git push --force origin main` |
| `git push <remote> --delete <branch>` | 删除远程分支 | `git push origin --delete feature/login` |
| `git push <remote> :<branch>` | 删除远程分支（简写） | `git push origin :feature/login` |

---

## 5. 提交与日志命令

| 命令 | 功能说明 | 示例 |
|------|----------|------|
| `git commit` | 提交暂存区到本地仓库 | `git commit` |
| `git commit -m "<msg>"` | 带消息提交 | `git commit -m "feat: add login page"` |
| `git commit -am "<msg>"` | 跳过暂存，直接提交已跟踪文件 | `git commit -am "fix: resolve bug"` |
| `git commit --amend` | 修改最后一次提交 | `git commit --amend` |
| `git commit --amend -m "<msg>"` | 修改提交消息 | `git commit --amend -m "updated message"` |
| `git log` | 查看提交历史 | `git log` |
| `git log --oneline` | 简洁单行显示日志 | `git log --oneline` |
| `git log -n <num>` | 显示最近 N 条日志 | `git log -n 10` |
| `git log --graph` | 图形化显示分支 | `git log --graph` |
| `git log --all` | 显示所有分支日志 | `git log --all` |
| `git log --oneline --graph --all` | 完整图形化日志 | `git log --oneline --graph --all` |
| `git log --author="<name>"` | 按作者筛选日志 | `git log --author="John"` |
| `git log --since="<date>"` | 按时间筛选（如 "2024-01-01"） | `git log --since="2024-01-01"` |
| `git log --until="<date>"` | 按时间筛选截止 | `git log --until="2024-01-31"` |
| `git log --grep="<pattern>"` | 按提交消息筛选 | `git log --grep="fix"` |
| `git log <file>` | 查看指定文件的提交历史 | `git log README.md` |
| `git log -p <file>` | 查看文件的详细变更 | `git log -p index.html` |
| `git show <commit>` | 查看指定提交的详情 | `git show abc123` |
| `git show <commit>:<file>` | 查看提交中指定文件的内容 | `git show abc123:README.md` |
| `git reflog` | 查看所有操作日志 | `git reflog` |

---

## 6. 撤销与回退命令

| 命令 | 功能说明 | 示例 |
|------|----------|------|
| `git checkout -- <file>` | 撤销工作区文件修改 | `git checkout -- index.html` |
| `git reset --soft <commit>` | 回退提交，保留工作区和暂存区 | `git reset --soft HEAD~1` |
| `git reset --mixed <commit>` | 回退提交，保留工作区（默认） | `git reset HEAD~1` |
| `git reset --hard <commit>` | 彻底回退，丢弃所有改动 | `git reset --hard HEAD~1` |
| `git reset --hard <remote>/<branch>` | 重置为远程分支状态 | `git reset --hard origin/main` |
| `git revert <commit>` | 创建新提交撤销指定提交 | `git revert abc123` |
| `git revert <start>..<end>` | 撤销一系列提交 | `git revert HEAD~3..HEAD` |
| `git stash` | 暂存工作区改动 | `git stash` |
| `git stash save "<msg>"` | 带消息暂存 | `git stash save "work in progress"` |
| `git stash list` | 列出所有暂存 | `git stash list` |
| `git stash apply` | 应用最近一次暂存 | `git stash apply` |
| `git stash apply stash@{n}` | 应用指定暂存 | `git stash apply stash@{0}` |
| `git stash pop` | 应用并删除暂存 | `git stash pop` |
| `git stash drop` | 删除最近一次暂存 | `git stash drop` |
| `git stash drop stash@{n}` | 删除指定暂存 | `git stash drop stash@{0}` |
| `git stash clear` | 清空所有暂存 | `git stash clear` |

---

## 7. 合并与变基命令

| 命令 | 功能说明 | 示例 |
|------|----------|------|
| `git merge <branch>` | 合并指定分支到当前分支 | `git merge feature/login` |
| `git merge --no-ff <branch>` | 禁用快进合并，强制创建合并提交 | `git merge --no-ff feature/login` |
| `git merge --abort` | 取消合并，恢复到合并前状态 | `git merge --abort` |
| `git rebase <branch>` | 将当前分支变基到指定分支 | `git rebase main` |
| `git rebase -i <commit>` | 交互式变基，可编辑提交历史 | `git rebase -i HEAD~5` |
| `git rebase --abort` | 取消变基，恢复原状 | `git rebase --abort` |
| `git rebase --continue` | 解决冲突后继续变基 | `git rebase --continue` |
| `git cherry-pick <commit>` | 将指定提交应用到当前分支 | `git cherry-pick abc123` |
| `git cherry-pick <commit1> <commit2>` | 应用多个提交 | `git cherry-pick abc123 def456` |
| `git cherry-pick --abort` | 取消 cherry-pick | `git cherry-pick --abort` |

---

## 8. 标签操作命令

| 命令 | 功能说明 | 示例 |
|------|----------|------|
| `git tag` | 列出所有标签 | `git tag` |
| `git tag <name>` | 创建轻量标签 | `git tag v1.0.0` |
| `git tag -a <name> -m "<msg>"` | 创建附注标签 | `git tag -a v1.0.0 -m "version 1.0.0"` |
| `git tag <name> <commit>` | 为指定提交打标签 | `git tag v1.0.0 abc123` |
| `git tag -d <name>` | 删除本地标签 | `git tag -d v1.0.0` |
| `git push <remote> <tag>` | 推送标签到远程 | `git push origin v1.0.0` |
| `git push <remote> --tags` | 推送所有标签到远程 | `git push origin --tags` |
| `git push <remote> :refs/tags/<tag>` | 删除远程标签 | `git push origin :refs/tags/v1.0.0` |
| `git show <tag>` | 查看标签详情 | `git show v1.0.0` |

---

## 9. 配置与帮助命令

| 命令 | 功能说明 | 示例 |
|------|----------|------|
| `git config --list` | 列出所有配置 | `git config --list` |
| `git config <key>` | 查看指定配置 | `git config user.name` |
| `git config --global <key> <value>` | 设置全局配置 | `git config --global user.name "John"` |
| `git config --local <key> <value>` | 设置仓库级配置 | `git config --local user.email "dev@example.com"` |
| `git config --unset <key>` | 移除配置 | `git config --unset user.name` |
| `git help <command>` | 查看命令帮助 | `git help commit` |
| `git <command> --help` | 查看命令帮助（简写） | `git commit --help` |
| `git version` | 查看 Git 版本 | `git version` |

---

## 10. 其他常用命令

| 命令 | 功能说明 | 示例 |
|------|----------|------|
| `git blame <file>` | 查看文件每行的修改记录 | `git blame README.md` |
| `git blame -L <start>,<end> <file>` | 查看指定行范围的修改记录 | `git blame -L 10,20 README.md` |
| `git grep <pattern>` | 在仓库中搜索内容 | `git grep "TODO"` |
| `git grep -n <pattern>` | 显示行号 | `git grep -n "TODO"` |
| `git grep --files-with-matches <pattern>` | 显示匹配的文件 | `git grep --files-with-matches "TODO"` |
| `git archive` | 打包仓库 | `git archive --format=zip HEAD -o repo.zip` |
| `git archive --prefix="repo/" HEAD` | 打包并添加前缀目录 | `git archive --prefix="repo/" HEAD -o repo.tar.gz` |
| `git submodule add <url>` | 添加子模块 | `git submodule add https://github.com/user/lib.git` |
| `git submodule init` | 初始化子模块 | `git submodule init` |
| `git submodule update` | 更新子模块 | `git submodule update` |
| `git submodule update --recursive` | 递归更新子模块 | `git submodule update --recursive` |
| `git gc` | 清理垃圾文件，优化仓库 | `git gc` |
| `git fsck` | 检查仓库完整性 | `git fsck` |
| `git count-objects -v` | 查看仓库对象统计 | `git count-objects -v` |

---

## 常用别名配置

```bash
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.pl pull
git config --global alias.ps push
git config --global alias.logg "log --oneline --graph --all"
git config --global alias.df diff
git config --global alias.mer merge
```

---

## 符号说明

| 符号 | 说明 |
|------|------|
| `<url>` | 远程仓库 URL |
| `<file>` | 文件名或路径 |
| `<branch>` | 分支名称 |
| `<commit>` | 提交哈希值 |
| `<tag>` | 标签名称 |
| `<name>` | 名称（分支/标签/远程仓库） |
| `<remote>` | 远程仓库名称（通常为 origin） |
| `<msg>` | 提交消息或标签消息 |
| `<num>` | 数字 |
| `<date>` | 日期（格式：YYYY-MM-DD） |
| `<pattern>` | 搜索模式或正则表达式 |

---

> **提示**：使用 `git help <command>` 可查看任意命令的完整文档。