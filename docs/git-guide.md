# Git 命令使用教程

## 一、Git 基础概念

### 1.1 什么是 Git
Git 是一个分布式版本控制系统，用于跟踪文件的变化并协调多人协作开发。

### 1.2 核心概念
- **仓库 (Repository)**: 存储项目代码和版本历史的地方
- **工作区 (Working Directory)**: 本地电脑上的项目文件夹
- **暂存区 (Staging Area)**: 临时存放即将提交的改动
- **分支 (Branch)**: 独立的开发线，用于并行开发不同功能
- **提交 (Commit)**: 将暂存区的改动保存到本地仓库
- **远程仓库 (Remote)**: 托管在网络上的仓库（如 GitHub、Gitee、GitLab）

### 1.3 常用分支命名规范
- `main` / `master`: 主分支，存放稳定代码
- `feature/xxx`: 功能开发分支
- `bugfix/xxx`: Bug 修复分支
- `hotfix/xxx`: 紧急修复分支
- `release/xxx`: 发布准备分支

---

## 二、首次配置

### 2.1 设置用户信息
```bash
git config --global user.name "Your Full Name"
git config --global user.email "your.email@example.com"
```

### 2.2 验证配置
```bash
git config --list
git config user.name
git config user.email
```

### 2.3 配置推荐
```bash
git config --global color.ui auto    # 启用颜色输出
git config --global core.editor "code --wait"  # 设置 VS Code 为默认编辑器
```

---

## 三、仓库操作流程

### 3.1 场景一：从远程仓库克隆（首次获取项目）

**完整流程：**

```bash
# 1. 克隆远程仓库到本地
git clone https://github.com/username/repository.git

# 2. 进入项目目录
cd repository

# 3. 查看远程仓库信息
git remote -v
```

### 3.2 场景二：将本地项目推送到远程仓库（新项目）

**完整流程：**

```bash
# 1. 进入本地项目目录
cd my-project

# 2. 初始化本地仓库
git init

# 3. 添加远程仓库地址（网页仓库地址）
git remote add origin https://github.com/username/repository.git

# 4. 添加所有文件到暂存区
git add .

# 5. 提交到本地仓库
git commit -m "Initial commit"

# 6. 推送到远程仓库 main 分支
git push -u origin main
```

---

## 四、日常开发流程（核心）

### 4.1 标准工作流程（推荐）

```bash
# ============ 第一步：更新本地代码 ============
# 切换到主分支
git checkout main

# 拉取远程最新代码
git pull origin main

# ============ 第二步：创建开发分支 ============
# 创建并切换到功能分支
git checkout -b feature/login-page

# ============ 第三步：开发代码 ============
# 编辑代码文件...

# ============ 第四步：提交到本地仓库 ============
# 查看改动状态
git status

# 添加改动到暂存区
git add .

# 提交到本地仓库
git commit -m "feat: add login page with form validation"

# ============ 第五步：推送到远程仓库 ============
# 推送分支到远程（首次推送）
git push -u origin feature/login-page

# 后续推送（已设置上游后）
git push
```

### 4.2 main 分支操作流程

```bash
# 更新本地 main 分支
git checkout main
git pull origin main

# 在 main 分支直接提交（仅用于紧急修复）
git add .
git commit -m "fix: critical bug in payment module"
git push origin main
```

### 4.3 分支合并流程

```bash
# 1. 先更新主分支
git checkout main
git pull origin main

# 2. 切换到开发分支
git checkout feature/login-page

# 3. 将 main 分支合并到当前分支（解决冲突）
git merge main

# 4. 切换回主分支
git checkout main

# 5. 合并开发分支到主分支
git merge feature/login-page

# 6. 推送到远程 main 分支
git push origin main

# 7. 删除本地开发分支（可选）
git branch -d feature/login-page

# 8. 删除远程开发分支（可选）
git push origin --delete feature/login-page
```

---

## 五、核心命令详解

### 5.1 仓库管理
```bash
git init                    # 初始化本地仓库
git clone <url>             # 克隆远程仓库
git remote -v               # 查看远程仓库列表
git remote add origin <url> # 添加远程仓库
git remote remove origin    # 移除远程仓库
```

### 5.2 工作区操作
```bash
git status                  # 查看文件状态
git diff                    # 查看未暂存的改动
git diff --cached           # 查看已暂存的改动
```

### 5.3 暂存与提交
```bash
git add <file>              # 添加单个文件
git add .                   # 添加所有改动（不包括删除）
git add -A                  # 添加所有改动（包括删除）
git commit -m "message"     # 提交到本地仓库
git commit -am "message"    # 跳过 add，直接提交已跟踪文件
```

### 5.4 分支操作
```bash
git branch                  # 查看本地分支
git branch -a               # 查看所有分支（含远程）
git branch -v               # 查看分支及最后提交
git checkout <branch>       # 切换分支
git checkout -b <branch>    # 创建并切换分支
git merge <branch>          # 合并指定分支到当前分支
git branch -d <branch>      # 删除本地分支
git branch -D <branch>      # 强制删除未合并分支
```

### 5.5 远程操作
```bash
git pull origin <branch>    # 拉取远程分支更新
git push origin <branch>    # 推送到远程分支
git push -u origin <branch> # 首次推送并设置上游
git fetch origin            # 拉取远程更新（不合并）
```

---

## 六、撤销与回退操作

### 6.1 撤销工作区修改
```bash
git checkout -- <file>      # 撤销单个文件的未暂存改动
git restore <file>          # Git 2.23+ 推荐方式
```

### 6.2 撤销暂存区修改
```bash
git reset HEAD <file>       # 将文件从暂存区撤回
git restore --staged <file> # Git 2.23+ 推荐方式
```

### 6.3 回退提交
```bash
git log                     # 查看提交历史
git log --oneline           # 简洁格式查看
git log --graph             # 图形化查看分支

git reset --soft <commit>   # 回退但保留工作区和暂存区
git reset --mixed <commit>  # 回退保留工作区（默认）
git reset --hard <commit>   # 彻底回退，丢弃所有改动
git revert <commit>         # 创建新提交撤销指定提交
```

---

## 七、冲突解决

### 7.1 冲突产生场景
- 合并分支时
- 拉取远程代码时
- 多人修改同一文件的同一部分

### 7.2 冲突解决步骤

```bash
# 1. 查看冲突文件
git status

# 2. 打开冲突文件，手动解决标记
<<<<<<< HEAD
当前分支的内容
=======
要合并的内容
>>>>>>> branch-name

# 3. 解决后添加文件
git add <file>

# 4. 完成合并提交
git commit
```

---

## 八、团队协作最佳实践

### 8.1 提交规范（Conventional Commits）
```bash
git commit -m "feat: add user registration"
git commit -m "fix: resolve login error"
git commit -m "docs: update API documentation"
git commit -m "refactor: optimize database query"
git commit -m "test: add unit tests for payment"
```

### 8.2 分支管理策略（Git Flow）
1. `main`: 主分支，稳定版本
2. `develop`: 开发分支，整合功能
3. `feature/*`: 功能开发分支
4. `release/*`: 发布准备分支
5. `hotfix/*`: 紧急修复分支

### 8.3 日常协作流程
1. 每天开始前拉取最新代码
2. 开发新功能使用独立分支
3. 定期推送分支到远程备份
4. 完成后创建 Pull Request
5. 代码审查通过后合并

---

## 九、常见问题与解决方案

### 9.1 推送失败
```bash
# 原因：本地代码落后于远程
# 解决方案：先拉取合并
git pull origin main
# 解决冲突后再推送
git push origin main
```

### 9.2 忘记添加文件到暂存区
```bash
# 解决方案：修改最后一次提交
git add missed-file.txt
git commit --amend
# 如果已推送，需要强制推送（谨慎使用）
git push --force origin main
```

### 9.3 误删分支
```bash
# 查看最近操作记录
git reflog
# 恢复分支
git checkout -b <branch-name> <commit-hash>
```

### 9.4 配置 SSH 免密登录（推荐）
```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your.email@example.com"

# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 将公钥添加到 GitHub/Gitee 账户设置中
```

---

## 十、命令速查表

| 场景 | 命令 |
|------|------|
| 克隆仓库 | `git clone <url>` |
| 创建分支 | `git checkout -b <branch>` |
| 提交代码 | `git add . && git commit -m "msg"` |
| 推送到远程 | `git push origin <branch>` |
| 拉取更新 | `git pull origin <branch>` |
| 查看状态 | `git status` |
| 查看日志 | `git log --oneline` |
| 合并分支 | `git merge <branch>` |
| 解决冲突 | 编辑文件 → `git add` → `git commit` |

---

## 附录：配置别名

```bash
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.pl pull
git config --global alias.ps push
git config --global alias.logg "log --oneline --graph --all"
```

使用别名后：
```bash
git st    # 相当于 git status
git co main  # 相当于 git checkout main
git logg   # 相当于 git log --oneline --graph --all
```