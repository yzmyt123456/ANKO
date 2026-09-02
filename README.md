<div align="center">

# 🎲 Anko · 安科创作平台

**让骰子决定命运的走向 —— 人物卡 · 剧情 · 自定义骰娘 · AI 助力的安科创作平台**

一个模块化、可拓展的开源安科创作平台。基于 **Python / FastAPI** 构建,支持保存人物卡、撰写剧情、召唤专属骰娘,并内置 **AI 快速建档** 与 **插件系统**,开箱即用,自由扩展。

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square&logo=fastapi&logoColor=white)
![Vue](https://img.shields.io/badge/Vue-3-4FC08D?style=flat-square&logo=vue.js&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=flat-square)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)

</div>

---

## 📖 目录

- [✨ 功能特性](#-功能特性)
- [📸 界面预览](#-界面预览)
- [🚀 快速开始](#-快速开始)
- [📁 项目结构](#-项目结构)
- [📡 API 概览](#-api-概览)
- [🧝 自定义骰娘](#-自定义骰娘)
- [🤖 AI 助手](#-ai-助手)
- [🧩 插件开发](#-插件开发)
- [🧪 测试](#-测试)
- [🛠 技术栈](#-技术栈)
- [🗺 路线图](#-路线图)
- [📄 许可](#-许可)

---

## ✨ 功能特性

| 能力 | 说明 |
|---|---|
| 📇 **人物卡** | 多模板:通用 + **DND 5e**;自定义属性组、称号、头像、背景、标签、扩展字段;网格卡片 + 详情抽屉 |
| 🎯 **DND 鉴定** | 属性 / 技能(察觉、奥秘、游说等 18 项)/ 豁免鉴定:自动计算 `1d20+修正(+熟练加值)`,支持 DC 成败判定,裸 20 大成功 / 裸 1 大失败 |
| 📖 **剧情创作** | 故事线 + 剧情条目;时间线式阅读,条目可关联登场人物与掷骰记录 |
| 🧝 **自定义骰娘** | 名字 / 人设 / 开场白 / 默认骰子 / 判定阈值 / 命运修正,全部可配置,存库即生效 |
| 🎲 **骰子引擎** | 纯 AST 表达式解析(安全,非 eval):`1d100`、`2d6+3`、`(1d6+1)*2`;经典安科 d100 判定,大成功 / 大失败 |
| 🤖 **AI 快速建档** | 粘贴大段角色描述 → AI 自动拆分出名字 / 称号 / 背景 / 属性 / 标签并填入表单 |
| 📊 **掷骰记录** | 每次掷骰落库,含每粒骰子明细与判定结果,可回查剧情 |
| 🧩 **插件系统** | 插件可注册自定义判定规则、扩展 API 路由、扩展骰子修正器,零侵入核心代码 |
| 📱 **响应式界面** | Vue 3 单页应用,桌面 / 移动端自适应;无需 Node 构建,后端直接托管 |

## 📸 界面预览

> 截图占位 —— 启动项目后可见完整界面

```
┌─────────────────────────────────────────────────────────────┐
│  🎲 安科      │  首页 / 人物卡 / 剧情 / 骰娘 / 掷骰台        │
├───────────────┴─────────────────────────────────────────────┤
│  深色侧边栏导航                                                │
│                                                               │
│   · Hero 横幅 + 统计卡片(人物卡/故事线/骰娘/掷骰次数)         │
│   · 人物卡:网格卡片 + 创建弹窗 + 详情抽屉 + 🤖 AI 快速建档     │
│   · 剧情:时间线阅读 + sticky 创作面板                         │
│   · 掷骰台:四色判定高亮 + 历史记录                            │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求
- Python ≥ 3.10

### 🚀 一键启动(推荐)

项目在**虚拟环境**中运行,以下脚本会自动完成"创建虚拟环境 → 安装依赖 → 启动":

```bash
# Windows(双击或命令行运行):
start.bat

# macOS / Linux(需先赋予执行权限):
chmod +x start.sh
./start.sh
```

启动后浏览器打开 **http://127.0.0.1:8000**(前端页面)或 **http://127.0.0.1:8000/docs**(API 文档)。

### 手动安装与启动

```bash
# 1. 克隆仓库
git clone https://github.com/yzmyt123456/ANKO.git
cd ANKO

# 2. 创建虚拟环境
python -m venv .venv

# 3. 激活(Windows)
.venv\Scripts\activate
# 或 macOS / Linux:
# source .venv/bin/activate

# 4. 安装依赖(在虚拟环境内)
pip install -e ".[dev]"

# 5. 启动
python run.py

# 6. 打开浏览器
# 前端页面: http://127.0.0.1:8000
# API 文档: http://127.0.0.1:8000/docs
```

> 💡 服务器默认监听 `127.0.0.1:8000`,可用 `python run.py --port 9000` 修改端口。
> 💡 所有依赖只安装在本项目的 `.venv` 虚拟环境中,不会污染系统 Python。


## 📁 项目结构

```
anko/
├── anko/                      # 核心包(业务与框架解耦)
│   ├── app.py                 # 应用工厂 create_app(组装一切)
│   ├── config.py              # 配置加载(config/settings.yaml)
│   ├── core/                  # 抽象层:存储接口 + 插件基类
│   │   ├── interfaces.py      # Storage 抽象接口(可换数据库实现)
│   │   └── plugin.py          # AnkoPlugin 基类 + PluginContext
│   ├── models/                # ORM 模型(人物卡/剧情/骰娘/记录)
│   ├── schemas/               # API 请求/响应模型(Pydantic v2)
│   ├── storage/               # 存储层(SQLite 实现,接口化可替换)
│   ├── dice/                  # 骰子引擎
│   │   ├── expression.py      # 骰子表达式解析与求值(AST,安全)
│   │   ├── rules.py           # 判定规则(默认 d100,可注册扩展)
│   │   ├── maids.py           # 骰娘配置对象
│   │   └── engine.py          # DiceEngine 主引擎
│   ├── ai/                    # AI 助手(OpenAI 兼容客户端 + 解析服务)
│   ├── services/              # 业务服务层(人物卡/剧情/骰娘)
│   ├── api/routers/           # REST 路由
│   ├── plugins/               # 插件加载器
│   └── static/                # 前端资源(Vue 3 SPA,无需构建)
├── plugins/                   # ★ 你的插件都放这里
├── config/
│   └── settings.yaml          # 全局配置(含 AI / 数据库 / 骰娘)
├── scripts/                   # 工具脚本(冒烟测试/前端校验)
└── tests/                     # 测试(58 个用例)
```

## 📡 API 概览

基础前缀 `/api`,完整交互式文档见 `/docs`。

## 🧝 自定义骰娘

创建骰娘时通过 `settings` 配置判定规则与命运修正:

```json
{
  "name": "傲娇小掷",
  "personality": "嘴上说才不帮你,却悄悄把骰子擦干净。",
  "greeting": "哼,要掷就快说!",
  "default_expression": "1d100",
  "settings": {
    "threshold": 60,
    "crit_success": 96,
    "crit_fail": 4,
    "modifiers": [{"type": "add", "value": 3}]
  }
}
```

| 配置项 | 说明 |
|---|---|
| `threshold` | 成功阈值,出目 > 阈值即成功(默认 50) |
| `crit_success` | 大成功临界(默认 95) |
| `crit_fail` | 大失败临界(默认 5) |
| `modifiers` | 命运修正:支持 `add`(加值)、`multiply`(倍率),插件可注册更多类型 |

支持任意骰子表达式:`1d100`、`d20`、`2d6+3`、`(1d6+1)*2`、`4d6` 等。

## 🤖 AI 助手

**人物卡创建弹窗**内置"AI 快速建档":粘贴一大段角色描述,AI 自动拆分出
名字 / 称号 / 背景 / 属性 / 标签并填入表单,确认后保存。

### 配置(兼容所有 OpenAI 格式接口)

编辑 `config/settings.yaml`:

```yaml
ai:
  enabled: true
  base_url: "https://api.deepseek.com/v1"   # DeepSeek / OpenAI / 通义 / Kimi 等
  api_key: "sk-你的key"
  model: "deepseek-chat"                    # 如 gpt-4o-mini / qwen-plus
```

> 🦙 **本地 Ollama**:`base_url: "http://127.0.0.1:11434/v1"`、`model: "qwen2.5"`、`api_key` 填任意值,完全免费离线运行。

## 🧩 插件开发

平台的核心设计目标就是**可拓展**。插件放在 `plugins/` 目录,自动加载:

```python
from fastapi import APIRouter
from anko.core.plugin import AnkoPlugin
from anko.dice.rules import Judgement, JudgementRule


class D20Rule(JudgementRule):          # 1. 注册自定义判定规则
    name = "d20-binary"
    def applies(self, expression: str) -> bool:
        return expression.strip().lower() == "d20"
    def judge(self, total: int, expression: str, config: dict) -> Judgement:
        return Judgement("success", "成功", f"出目 {total} ≥ 10:成功。") if total >= 10 \
            else Judgement("fail", "失败", f"出目 {total} < 10:失败。")

class MyPlugin(AnkoPlugin):
    name = "my-plugin"
    version = "0.1.0"

    def setup(self, context):          # 2. 注册规则 + 扩展 API
        context.dice_engine.register_rule(D20Rule())
        router = APIRouter(prefix="/my", tags=["我的插件"])
        @router.get("/hello")
        def hello():
            return {"msg": "hi"}
        context.add_router(router)

plugin = MyPlugin()                    # 约定:模块内 `plugin` 变量会被自动加载
```

参考示例插件 `plugins/example/`,它注册了 `d20-binary` 规则并提供一个 `/api/example/ping` 路由。

**其他拓展方式**:

| 需求 | 做法 |
|---|---|
| 加新 API 路由 | 写插件,`context.add_router(router)` |
| 加自定义判定规则 | 继承 `JudgementRule` + `register_rule()` |
| 加新数据实体 | `models/` + `schemas/` + `services/` + `api/routers/` 各加一个文件 |
| 换数据库 | 实现 `Storage` 接口的新类,替换 `SqliteStorage` |
| 实体加字段 | 全部实体预留 `extra` JSON 字段,直接使用 |

## 🧪 测试

```bash
pytest
```

目前包含 **58 个测试用例**:骰子表达式解析、判定规则、引擎修正、
人物卡/剧情/骰娘/掷骰 API、AI 解析(JSON 提取/规范化/路由错误处理)、插件加载。

```bash
python scripts/smoke_test.py        # 端到端冒烟测试
python scripts/check_frontend.py    # 前端引用一致性校验
python scripts/check_html.py        # HTML 标签配平校验
node scripts/check_vue_template.mjs # Vue 模板编译校验
```

## 🛠 技术栈

- **后端**:Python 3.10+ · FastAPI · SQLAlchemy 2.0 · SQLite · Pydantic v2
- **前端**:Vue 3(本地加载,零构建)· 原生 CSS(现代 Dashboard 风格)
- **AI**:OpenAI 兼容 API(httpx 直连,无厂商绑定)
- **质量**:pytest · pytest-asyncio · 手写 AST 骰子引擎(安全无 eval)

## 🗺 路线图

- [ ] 剧情条目的内联掷骰与结果插入
- [ ] AI 生成剧情大纲 / 续写建议
- [ ] AI 骰娘人设扮演(掷骰时"她"会说话)
- [ ] 用户账户与多设备同步
- [ ] PostgreSQL / MySQL 存储支持
- [ ] 安科卡片导出(长图 / Markdown)

## 📄 许可

[MIT License](LICENSE) © 2026 Anko Contributors

---

<p align="center">
  <sub>用 🎲 掷出你的故事 —— Anko 安科创作平台</sub>
</p>


| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/characters` | 创建人物卡 |
| GET | `/api/characters` | 人物卡列表 |
| GET | `/api/characters/{id}` | 人物卡详情 |
| PUT | `/api/characters/{id}` | 更新人物卡 |
| DELETE | `/api/characters/{id}` | 删除人物卡 |
| POST | `/api/stories` | 创建故事线 |
| POST | `/api/stories/{id}/entries` | 追加剧情条目 |
| GET | `/api/stories/{id}/entries` | 剧情条目列表 |
| GET | `/api/maids` | 骰娘列表 |
| POST | `/api/maids` | 创建自定义骰娘 |
| PUT | `/api/maids/{id}` | 修改骰娘 |
| DELETE | `/api/maids/{id}` | 删除骰娘 |
| POST | `/api/rolls` | 掷骰(指定骰娘/表达式/是否落库) |
| GET | `/api/rolls` | 掷骰历史 |
| GET | `/api/ai/status` | 查询 AI 配置状态 |
| POST | `/api/ai/parse-character` | AI 解析角色描述 → 人物卡草稿(支持 default / dnd5e) |
| GET | `/api/templates` | 人物卡模板列表 |
| GET | `/api/templates/{id}` | 模板完整定义(分组字段 + 鉴定项) |
| POST | `/api/characters/{id}/checks` | DND 鉴定(属性/技能/豁免),可带 `dc` 判定 |
| GET | `/api/example/ping` | 示例插件路由 |

## 🎯 DND 5e 角色卡与鉴定

创建人物卡时选择 **"DND 5e"** 模板,即可填写精细字段:

- **基础**:阵营 / 种族背景 / 职业 / 等级
- **六维属性**:力量 / 敏捷 / 体质 / 智力 / 感知 / 魅力(输入值自动算修正)
- **战斗**:HP / AC / 法术豁免 DC / 熟练加值 / 护甲受训
- **熟练**:豁免、技能、武器、工具熟练与语言
- **法术**:施法属性 / 法术位 / 掌握法术 / 掌握戏法
- **特质**:职业特性 / 专长 / 信仰 + 起始装备

**鉴定辅助**:打开人物卡详情抽屉,点击属性格或技能/豁免徽章即可掷骰:

```
丰川祥子 的「察觉」:1d20-1 = 14
丰川祥子 的「奥秘」:1d20+4 = 5   ← 奥秘在技能熟练中:智力(+2)+熟练加值(+2)
丰川祥子 的「魅力豁免」:1d20+7 = 17
```

- 修正 = `(属性值 - 10) // 2`(DND 5e 规则)
- 技能/豁免命中熟练列表时自动追加熟练加值
- 裸 **20** 大成功、裸 **1** 大失败;提供 `dc` 时按 `出目+修正 ≥ DC` 判定
- AI 建档也支持 DND:粘贴整张卡文本,AI 自动填入全部字段

