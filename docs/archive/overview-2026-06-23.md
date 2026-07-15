# 功能恢复完成报告

**时间**: 2026-06-23
**目标**: 将已实现但未集成的 HistoryManager 和 Scheduler 模块接入主应用

---

## 已恢复功能

### 历史数据持久化 (HistoryManager)
| API 路由 | 方法 | 功能 |
|---|---|---|
| `/api/history/charts` | GET | 获取所有已保存榜单名称 |
| `/api/history/snapshot_dates/<chart>` | GET | 获取榜单的快照日期列表 |
| `/api/history/snapshot/<chart>` | GET | 获取最新快照（支持 `?timestamp=` 查历史） |
| `/api/history/trend` | GET | 单曲排名趋势（传 chart_name/song_title/artist） |
| `/api/history/rank_changes/<chart>` | GET | 前后快照排名变化对比 |
| `/api/history/cleanup` | POST | 清理过期数据 |
| `/api/history/save` | POST | 手动保存当前数据 |

### 定时调度器 (Scheduler)
| API 路由 | 方法 | 功能 |
|---|---|---|
| `/api/scheduler/status` | GET | 查询运行状态 |
| `/api/scheduler/start` | POST | 启动定时刷新 |
| `/api/scheduler/stop` | POST | 停止定时刷新 |
| `/api/scheduler/run_now` | POST | 立即执行一次爬取 |

### 自动持久化
- 每次手动「刷新数据」自动保存到历史记录（热歌榜）
- 调度器每次定时执行也会自动保存所有榜单

---

## 前端新增

- **调度器面板**：Header 按钮 → 展开折叠面板，含运行状态指示灯 + 启停/立即执行按钮
- **保存历史按钮**：Header 区域，一键保存当前数据
- **排名变化追踪**：歌曲列表下方，下拉选择榜单后展示前后快照排名变化表

---

## 修改文件

| 文件 | 变更 |
|---|---|
| `app.py` | +导入 HistoryManager/Scheduler，+11 个 API 路由，-do_scrape 自动保存 |
| `templates/index.html` | +调度器面板 HTML/CSS/JS，+历史数据区域 HTML/CSS/JS |
| `src/music_analytics/history.py` | 无变更（已完整实现） |
| `src/music_analytics/scheduler.py` | 无变更（已完整实现） |

---

## 历史数据现状

SQLite DB 中已有 6 个榜单的历史快照：热歌榜、飙升榜、新歌榜、原创榜、抖音榜、韩国榜
