## Git 命令使用指南

### 一、基础配置

#### 1. 设置用户信息
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

#### 2. 查看配置信息
```bash
git config --list
git config user.name
git config user.email
```

### 二、仓库操作

#### 1. 初始化仓库
```bash
git init
```

#### 2. 克隆远程仓库
```bash
git clone <repository-url>
git clone <repository-url> <local-folder-name>
```

#### 3. 查看远程仓库
```bash
git remote -v
```

#### 4. 添加远程仓库
```bash
git remote add origin <repository-url>
```

#### 5. 移除远程仓库
```bash
git remote remove origin
```

### 三、工作流程

#### 1. 查看文件状态
```bash
git status
git status -s  # 简洁输出
```

#### 2. 添加文件到暂存区
```bash
git add <file-name>
git add .      # 添加所有改动
git add -A     # 添加所有改动（包括删除）
```

#### 3. 提交改动
```bash
git commit -m "commit message"
git commit -am "commit message"  # 跳过 add 直接提交已跟踪文件
git commit --amend              # 修改最后一次提交
```

#### 4. 推送到远程仓库
```bash
git push origin <branch-name>
git push -u origin <branch-name>  # 首次推送，设置上游
```

#### 5. 拉取远程更新
```bash
git pull origin <branch-name>
git pull  # 默认拉取当前分支
```

### 四、分支操作

#### 1. 查看分支
```bash
git branch          # 查看本地分支
git branch -a       # 查看所有分支（包括远程）
git branch -v       # 查看分支及最后提交
```

#### 2. 创建分支
```bash
git branch <branch-name>
git checkout -b <branch-name>   # 创建并切换
git switch -c <branch-name>     # 创建并切换（Git 2.23+）
```

#### 3. 切换分支
```bash
git checkout <branch-name>
git switch <branch-name>        # Git 2.23+
```

#### 4. 合并分支
```bash
git checkout <target-branch>
git merge <source-branch>
```

#### 5. 删除分支
```bash
git branch -d <branch-name>     # 删除本地分支
git branch -D <branch-name>     # 强制删除未合并分支
git push origin --delete <branch-name>  # 删除远程分支
```

#### 6. 推送新分支到远程
```bash
git push origin <branch-name>
```

### 五、撤销操作

#### 1. 撤销工作区修改
```bash
git checkout -- <file-name>
git restore <file-name>         # Git 2.23+
```

#### 2. 撤销暂存区修改
```bash
git reset HEAD <file-name>
git restore --staged <file-name>  # Git 2.23+
```

#### 3. 回退提交
```bash
git log              # 查看提交历史
git log --oneline    # 简洁历史
git log --graph      # 图形化历史

git reset --hard <commit-hash>   # 彻底回退
git reset --soft <commit-hash>   # 保留工作区
git revert <commit-hash>         # 创建新提交撤销
```

### 六、日志查看

```bash
git log                          # 完整日志
git log --oneline                # 单行显示
git log -n 5                     # 显示最近5条
git log --graph                  # 图形分支
git log --all                    # 所有分支日志
git log --oneline --graph --all  # 完整图形日志
```

### 七、标签操作

#### 1. 创建标签
```bash
git tag <tag-name>                # 轻量标签
git tag -a <tag-name> -m "message"  # 附注标签
git tag <tag-name> <commit-hash>    # 指定提交打标签
```

#### 2. 查看标签
```bash
git tag
git tag -l "v1.*"
```

#### 3. 推送标签
```bash
git push origin <tag-name>
git push origin --tags            # 推送所有标签
```

#### 4. 删除标签
```bash
git tag -d <tag-name>
git push origin :refs/tags/<tag-name>
```

### 八、冲突解决

当合并或拉取发生冲突时：
1. 查看冲突文件：`git status`
2. 手动编辑冲突文件，解决标记
3. 添加解决后的文件：`git add <file-name>`
4. 完成合并：`git commit`

冲突标记说明：
```
<<<<<<< HEAD
当前分支的内容
=======
要合并分支的内容
>>>>>>> branch-name
```

### 九、常用配置推荐

#### 1. 配置别名
```bash
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.st status
git config --global alias.logg "log --oneline --graph --all"
```

#### 2. 配置颜色输出
```bash
git config --global color.ui auto
```

#### 3. 配置默认编辑器
```bash
git config --global core.editor "code --wait"  # VS Code
git config --global core.editor "vim"          # Vim
```

### 十、团队协作流程

#### 标准工作流：
1. `git pull origin main` - 更新本地主分支
2. `git checkout -b feature/xxx` - 创建特性分支
3. 开发代码
4. `git add .` - 添加改动
5. `git commit -m "feat: add xxx"` - 提交
6. `git push origin feature/xxx` - 推送到远程
7. 创建 Pull Request / Merge Request
8. 代码审查通过后合并到主分支

#### 提交规范（推荐）：
- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `style:` 代码格式
- `refactor:` 代码重构
- `test:` 测试更新
- `chore:` 构建/工具更新

---

### 快捷键参考
| 命令 | 说明 |
|------|------|
| `git st` | 查看状态 |
| `git co <branch>` | 切换分支 |
| `git br` | 查看分支 |
| `git ci -m "msg"` | 提交 |
| `git logg` | 图形化日志 |