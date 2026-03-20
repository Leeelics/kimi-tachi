# GitHub 设置指南

> 将 kimi-tachi 推送到 GitHub 并启用 CI/CD

---

## 第一步：创建 GitHub 仓库

### 在 GitHub 网页上创建

1. 访问 https://github.com/new
2. 填写仓库信息：
   - **Repository name**: `kimi-tachi`
   - **Description**: `Multi-agent task orchestration for Kimi CLI (君たち)`
   - **Visibility**: Public (推荐) 或 Private
   - **Initialize**: 不要勾选任何选项（我们已有本地仓库）
3. 点击 "Create repository"

### 或者使用 GitHub CLI

```bash
# 安装 gh CLI: https://cli.github.com/
gh auth login
gh repo create kimi-tachi --public --description "Multi-agent task orchestration for Kimi CLI (君たち)"
```

---

## 第二步：推送本地仓库

```bash
# 进入项目目录
cd /home/lee/ship/kimi-tachi

# 添加远程仓库（替换 yourusername 为你的 GitHub 用户名）
git remote add origin https://github.com/yourusername/kimi-tachi.git

# 或者使用 SSH（推荐）
git remote add origin git@github.com:yourusername/kimi-tachi.git

# 验证远程仓库
git remote -v

# 推送 main 分支
git push -u origin main

# 推送所有标签
git push origin --tags
```

---

## 第三步：配置仓库设置

### 1. 保护 main 分支

访问 `https://github.com/yourusername/kimi-tachi/settings/branches`

添加规则：
- **Branch name pattern**: `main`
- **Require a pull request before merging**: ✅
  - Require approvals: 1 (如果是团队开发)
- **Require status checks to pass before merging**: ✅
  - 选择以下 checks:
    - `lint`
    - `type-check`
    - `test`
    - `validate-agents`
    - `docs`
    - `build`
- **Restrict pushes that create files larger than**: 100 MB

### 2. 启用 Discussions

访问 `https://github.com/yourusername/kimi-tachi/settings`

- 勾选 "Discussions"

### 3. 配置 Secrets（用于发布到 PyPI）

访问 `https://github.com/yourusername/kimi-tachi/settings/secrets/actions`

#### 方式 A：Trusted Publishing（推荐）

1. 在 PyPI 上创建项目：https://pypi.org/manage/projects/
2. 配置 Trusted Publisher：
   - 访问 `https://pypi.org/manage/project/kimi-tachi/settings/publishing/`
   - 添加 Publisher：
     - **Owner**: yourusername
     - **Repository name**: kimi-tachi
     - **Workflow name**: `release.yml`
     - **Environment name**: `pypi`

#### 方式 B：API Token（传统方式）

1. 在 PyPI 生成 API Token：https://pypi.org/manage/account/token/
2. 添加到 GitHub Secrets：
   - Name: `PYPI_API_TOKEN`
   - Value: 你的 PyPI token

---

## 第四步：验证 CI/CD

### 1. 创建测试 PR

```bash
# 创建新分支
git checkout -b test/ci-checks

# 做一个小的修改（例如添加一个注释）
echo "# CI Test" >> README.md

# 提交
git add README.md
git commit -m "ci: test GitHub Actions workflow"

# 推送
git push origin test/ci-checks
```

### 2. 在 GitHub 创建 PR

访问 `https://github.com/yourusername/kimi-tachi/pulls`

- 点击 "New pull request"
- 选择 `test/ci-checks` → `main`
- 填写标题和描述
- 创建 PR

### 3. 检查 CI 运行

在 PR 页面，应该看到所有 checks 运行：
- ✅ Code Quality (ruff)
- ✅ Type Check (ty)
- ✅ Tests (pytest)
- ✅ Validate Agent YAMLs
- ✅ Documentation
- ✅ Build Package

### 4. 合并 PR

确认所有 checks 通过后：
- 点击 "Merge pull request"
- 删除分支

---

## 第五步：发布第一个版本

### 1. 确保版本号正确

```bash
# 检查 pyproject.toml
grep "^version" pyproject.toml

# 检查 __init__.py
grep "__version__" src/kimi_tachi/__init__.py

# 检查 CHANGELOG.md
grep "## \[0.1.0\]" docs/CHANGELOG.md
```

### 2. 创建 Release

```bash
# 确保在 main 分支
git checkout main
git pull origin main

# 创建标签
git tag 0.1.0

# 推送标签
git push origin 0.1.0
```

### 3. 查看自动发布

- GitHub Actions 会自动运行：
  1. 验证版本号
  2. 构建包
  3. 发布到 PyPI
  4. 创建 GitHub Release

- 查看进度：
  `https://github.com/yourusername/kimi-tachi/actions`

### 4. 验证发布

```bash
# 等待几分钟后
pip install kimi-tachi
kimi-tachi --version
```

---

## 第六步：后续开发工作流

### 日常开发

```bash
# 1. 更新 main
git checkout main
git pull origin main

# 2. 创建功能分支
git checkout -b feat/new-feature

# 3. 开发并提交
# ... 编码 ...
git add .
git commit -m "feat(scope): description"

# 4. 推送到 GitHub
git push origin feat/new-feature

# 5. 创建 PR（通过 GitHub Web 或 CLI）
gh pr create --title "feat: new feature" --body "Description..."

# 6. 等待 CI 通过后合并
# 7. 删除本地分支
git checkout main
git branch -d feat/new-feature
```

### 发布新版本

```bash
# 1. 更新版本号（pyproject.toml 和 __init__.py）
# 2. 更新 CHANGELOG.md
# 3. 提交
git add -A
git commit -m "chore(release): bump version to 0.2.0"

# 4. 创建标签
git tag 0.2.0

# 5. 推送
git push origin main
git push origin 0.2.0

# 6. GitHub Actions 自动处理发布
```

---

## 故障排除

### CI 失败

```bash
# 本地复现 CI 环境
make lint
make type-check
make test

# 修复后重新推送
git add .
git commit --amend
git push origin branch-name --force
```

### PyPI 发布失败

- 检查 PyPI token 是否正确配置
- 检查版本号是否已存在于 PyPI
- 检查 `pyproject.toml` 格式

### 权限问题

```bash
# 检查远程仓库权限
git remote -v

# 如果是 HTTPS，考虑切换到 SSH
git remote set-url origin git@github.com:yourusername/kimi-tachi.git
```

---

## 相关链接

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

**恭喜！** 🎉 现在你拥有了一个完整的 CI/CD 工作流！
