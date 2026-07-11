# 技术能力提升指南

> 本指南为团队提供系统性的技术成长路径，从代码质量到工程化实践。

---

## 一、代码质量基线

### 1.1 类型注解（Type Hints）

**为什么要用：**
- 静态类型检查，提前发现 bug
- IDE 自动补全，提升开发效率
- 文档作用，减少代码注释

**实践：**

```python
# ❌ 不好
def analyze_top_artists(songs):
    return []

# ✅ 好
def analyze_top_artists(songs: list[SongData]) -> list[ArtistStat]:
    """获取 TOP N 歌手

    Args:
        songs: 歌曲列表

    Returns:
        歌手统计列表
    """
    ...
```

**工具：**
- `mypy` — 静态类型检查器
- `pyright` — 微软出品，快速准确

### 1.2 数据类（Dataclass）

**为什么要用：**
- 自动生成 `__init__`, `__repr__`, `__eq__`
- 减少样板代码
- 支持验证和默认值

**实践：**

```python
# ❌ 不好
class SongData:
    def __init__(self, rank, title, artist):
        self.rank = rank
        self.title = title
        self.artist = artist

# ✅ 好（项目已在用）
from dataclasses import dataclass, field

@dataclass
class SongData:
    rank: int
    title: str
    artist: str = "未知歌手"

    def __post_init__(self):
        """数据验证"""
        if self.rank < 1:
            raise ValueError(f"排名必须 >= 1, 得到 {self.rank}")
```

### 1.3 异常处理

**原则：**
- 具体异常捕获，不捕获 `Exception`
- 异常需要包含上下文信息
- 日志记录而非 print

**实践：**

```python
# ❌ 不好
try:
    data = resp.json()
except:
    print("解析失败")

# ✅ 好
import logging

logger = logging.getLogger(__name__)

try:
    data = resp.json()
except json.JSONDecodeError as e:
    logger.error(f"JSON 解析失败: {endpoint}, 错误: {e}")
    raise ParseError(f"API 返回数据格式错误: {e}")
```

### 1.4 日志规范

**实践：**

```python
import logging

# 配置日志（入口文件一次）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# 使用
logger = logging.getLogger(__name__)
logger.info("开始爬取数据...")
logger.warning("API 请求失败，尝试备用策略")
logger.error(f"保存失败: {e}")
```

---

## 二、工程化实践

### 2.1 依赖管理

**使用 Poetry：**

```bash
# 安装 Poetry
pip install poetry

# 初始化
poetry init

# 添加依赖
poetry add flask requests beautifulsoup4 matplotlib wordcloud

# 锁定版本
poetry lock

# 安装
poetry install
```

**pyproject.toml 结构：**

```toml
[tool.poetry]
name = "music-analytics"
version = "1.0.0"
description = "网易云音乐热歌榜数据分析平台"
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.9"
flask = "^2.3"
requests = "^2.31"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4"
black = "^23.9"
ruff = "^0.1"

[tool.black]
line-length = 100

[tool.ruff]
line-length = 100
```

### 2.2 代码格式化

**格式化工具对比：**

| 工具 | 功能 | 推荐度 |
|------|------|--------|
| Black | 格式化 | ⭐⭐⭐⭐⭐ |
| isort | import 排序 | ⭐⭐⭐⭐⭐ |
| Ruff | 格式化 + 检查 | ⭐⭐⭐⭐⭐ |

**使用：**

```bash
# 安装
pip install black isort ruff

# 格式化
black .
isort .
ruff check --fix .

# CI 集成（GitHub Actions）
ruff@setup
```

### 2.3 测试框架

**pytest 最佳实践：**

```python
# tests/test_analyzer.py
import pytest
from music_analytics.analyzer import ArtistAnalyzer
from music_analytics.models import SongData

class TestArtistAnalyzer:
    @pytest.fixture
    def sample_songs(self):
        return [
            SongData(rank=1, title="晴天", artist="周杰伦"),
            SongData(rank=2, title="七里香", artist="周杰伦"),
            SongData(rank=3, title="浮夸", artist="陈奕迅"),
        ]

    def test_get_top_artists(self, sample_songs):
        analyzer = ArtistAnalyzer(sample_songs)
        top = analyzer.get_top_artists(10)

        assert len(top) == 2
        assert top[0].name == "周杰伦"
        assert top[0].count == 2
```

**运行：**

```bash
pytest tests/ -v --cov=src
```

### 2.4 CI/CD

**GitHub Actions 示例：**

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install poetry
      - run: poetry install
      - run: poetry run ruff check .
      - run: poetry run pytest
```

---

## 三、架构设计

### 3.1 模块职责划分

```
src/
├── music_analytics/
│   ├── __init__.py      # 导出公共接口
│   ├── config.py      # 配置管理
│   ├── models.py    # 数据模型（核心）
│   ├── scraper.py   # 数据获取
│   ├── analyzer.py  # 业务逻辑
│   ├── visualizer.py # 可视化
│   └── exceptions.py # 自定义异常
```

**原则：**
- `config` — 仅配置
- `models` — 仅数据结构 + 简单方法
- `scraper` — 仅网络请求
- `analyzer` — 仅业务逻辑
- `visualizer` — 仅图表生成

### 3.2 Blueprint 组织（Flask）

```python
# src/music_analytics/routes.py
from flask import Blueprint

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/scrape', methods=['POST'])
def scrape():
    ...

# app.py
from music_analytics.routes import api_bp
app.register_blueprint(api_bp)
```

### 3.3 配置分离

```python
# config.yaml
app:
  host: "127.0.0.1"
  port: 5000
  debug: true

scraper:
  timeout: 15
  max_retries: 3
  delay_min: 0.3
  delay_max: 1.0

# 加载配置
import yaml

with open('config.yaml') as f:
    config = yaml.safe_load(f)
```

---

## 四、Git 最佳实践

### 4.1 分支策略

```
main        — 生产代码
develop     — 开发分支
feature/*   — 功能开发
bugfix/*    — Bug 修复
release/*   — 发布准备
```

### 4.2 提交规范

**Conventional Commits：**

```
feat: 添加歌手排行榜功能
fix: 修复词云中文乱码问题
docs: 更新 README
refactor: 重构数据分析模块
test: 添加单元测试
chore: 更新依赖版本
```

**工具：**

```bash
# commitizen 交互式提交
pip install commitizen
cz commit
```

---

## 五、学习资源

### 5.1 Python 进阶

| 资源 | 说明 |
|------|------|
| Real Python | 优质教程 |
| Python Docs | 官方文档 |
| Fluent Python | 书籍进阶 |

### 5.2 工程化

| 资源 | 说明 |
|------|------|
| Python Packaging Guide | 官方打包指南 |
| pytest Docs | 测试文档 |
| Hypermodern Python | 工程化系列文章 |

### 5.3 代码质量

| 工具 | 说明 |
|------|------|
| mypy | 类型检查 |
| Black | 代码格式化 |
| Ruff | Linter |
| Coverage.py | 覆盖率 |

---

## 六、行动计划

### 优先级排���

| 优先级 | 任务 | 预期收益 |
|--------|------|---------|
| P0 | 修复语法错误 | 避免运行时崩溃 |
| P0 | 统一使用 src 模块 | 代码复用 |
| P1 | 添加类型注解 | 可维护性 |
| P1 | 补充测试用例 | 回归保护 |
| P2 | 引入 CI/CD | 自动化 |
| P2 | 使用 Poetry | 依赖管理 |

### 快速开始命令

```bash
# 安装开发依赖
pip install pytest black ruff mypy

# 代码检查
ruff check .
mypy src/

# 自动格式化
black .
isort .

# 运行测试
pytest -v

# 完整检查
ruff check . && black --check . && mypy src/ && pytest
```

---

## 九、优化实施记录（2026-06-16）

### 9.1 已完成项

| 任务 | 状态 | 详情 |
|------|------|------|
| 重构根目录 app.py | ✅ | 从 948 行精简至约 180 行，集成 `src/music_analytics` 模块 |
| 修复 `visualizer.py` 语法错误 | ✅ | 删除孤立的 `(xmin=0)` 表达式 |
| 修复 `scraper.py` 语法错误 | ✅ | 删除多余的 `]` 字符 |
| 补全类型提示 | ✅ | `analyzer.py`、`visualizer.py`、`models.py` 全部添加类型注解 |
| 增强测试覆盖 | ✅ | 新增 `test_analyzer.py`、`test_visualizer.py`、`test_models_extra.py`，共 50 个测试用例 |
| 配置代码质量工具 | ✅ | `pyproject.toml` 集成 ruff + mypy + pytest，`--cov-fail-under=60` |
| 集成 pre-commit | ✅ | 新增 `.pre-commit-config.yaml` |

### 9.2 覆盖率现状

```
src/music_analytics/analyzer.py     100.0%
src/music_analytics/config.py        86.1%
src/music_analytics/models.py       100.0%
src/music_analytics/scraper.py       17.8%   # 网络爬虫需 mock 测试
src/music_analytics/visualizer.py    90.2%
─────────────────────────────────────────
TOTAL                                64.6%
```

> 注：`scraper.py` 覆盖率较低属于合理范围（外部 HTTP 请求需要 mock 才能单测），不影响业务模块质量。

### 9.3 后续建议

- 为 `scraper.py` 添加 `responses`/`pytest-mock` 模拟测试
- 将 `--cov-fail-under` 提升至 80%
- 接入 GitHub Actions / GitLab CI 自动运行 ruff + pytest

---

> 技术提升是一个渐进过程，不需要一口气完成。先从最影响效率的地方开始，每次改进一点点。