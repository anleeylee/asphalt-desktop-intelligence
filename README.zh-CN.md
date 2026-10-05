# Asphalt Desktop Intelligence（沥青桌面智能工具集）

**沥青路面工程估算 Python 工具集** —— 将图纸 PDF、CAD 图纸、技术规范、承包商报价、送货单、供应商价格和现场照片，转化为对接 [AsphaltCosts.com](https://asphaltcosts.com/) 计算引擎的**可审计估算报告**。

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CLI](https://img.shields.io/badge/CLI-command--line-blue)](#快速开始)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-0078D6)](https://www.microsoft.com/windows)
[![AsphaltCosts.com](https://img.shields.io/badge/engine-AsphaltCosts.com-0a7d4c)](#计算引擎)

**[English](./README.md)** | 简体中文

---

## 解决什么问题

人工做沥青工程量计算既慢又容易出错：尺寸藏在 PDF 图纸和 CAD 图纸里、要求散落在冗长的规范文件中、每家承包商的报价格式都不一样、送货单上的数量几乎总是和估算对不上。本项目用一套**确定性、有证据支撑的桌面流水线**取代"复制粘贴 + 手工表格"的旧流程，服务对象是沥青与路面工程的估算师、项目经理、工地带班和业主。

每个脚本都遵循标准生命周期 `发现 → 摄取 → 提取 → 归一化 → 校验 → 计算/分类 → 输出 → 审计`，每条重要数据都携带 `{数值, 单位, 来源文件, 来源页码, 来源区域, 方法, 置信度, 状态, 已验证}` 证据链。

## 核心功能

- **图纸算量**（PDF 图纸 / CAD-DXF）——按区域输出面积、厚度、吨数、订购吨数与车次，附证据
- **规范核对** ——结构化要求提取，并检测 规范vs增补 / 图纸vs规范 / 规范vs投标 冲突
- **报价对比** ——归一化的承包商报价横向对比，含 $/SF、$/吨 与范围标记（不做排名）
- **送货单对账** ——从 CSV / PDF / 图片送货单核对"到货 vs 估算"吨数，含毛重−皮重校验
- **供应商价格归一化** ——带依据与有效期窗口的材料价格数据集
- **天气与压实规划** ——基于文档化集总热模型的 HMA 冷却/压实窗口
- **现场照片筛查** ——坑槽、裂缝、车辙、表面异常检测，用于质检
- **可审计估算报告** ——JSON / Markdown / XLSX / PDF，附来源清单与计算清单
- **人机协同** ——低置信度值与冲突进入复核队列，绝不静默修正

## 脚本一览

| ID | 脚本 | 主要用户 | 主要输入 | 主要输出 |
|---|---|---|---|---|
| S01 | `scripts/s01_project_workspace.py` | 估算师 / 项目经理 / 带班 | 文件 + 项目元数据 | 规范化项目工作区（project.json、清单、来源索引） |
| S02 | `scripts/s02_pdf_plan_takeoff.py` | 估算师 / 项目经理 | 市政/路面 PDF 图纸 | 铺装算量表 + 引擎数量 |
| S03 | `scripts/s03_cad_takeoff.py` | 估算师 / 工程师 | DWG（转 DXF）/ DXF | 几何数量 |
| S04 | `scripts/s04_specification_checker.py` | 估算师 / 项目经理 | 规范 PDF | 结构化要求 + 冲突 |
| S05 | `scripts/s05_quote_comparator.py` | 业主 / 项目经理 / 估算师 | 承包商报价 | 可对比报价表 + 标记 |
| S06 | `scripts/s06_delivery_ticket_reconcile.py` | 带班 / 项目经理 | 送货单 PDF/图片/CSV | 到货 vs 估算对账 |
| S07 | `scripts/s07_supplier_quote_normalizer.py` | 采购 / 估算师 | 供应商报价 | 规范化材料价格数据集 |
| S08 | `scripts/s08_weather_compaction_planner.py` | 施工主管 / 带班 | 天气 + 项目参数 | 铺装窗口分析（热模型） |
| S09 | `scripts/s09_field_photo_analyzer.py` | 带班 / 业主 / 项目经理 | 现场照片 | 外观状况筛查 |
| S10 | `scripts/s10_estimate_report_builder.py` | 估算师 / 项目经理 | 结构化项目数据 | 可审计估算报告 |

## 技术栈

- **Python 3.12+**（Windows 11 一等支持，跨平台 CLI）
- **PDF 解析** ——基于 PyMuPDF 的文本 / 矢量 / 比例注记提取
- **CAD** ——DXF 几何解析算量（DWG 经转换）
- **AI 边界** ——默认确定性启发式提取器；可选 OpenAI 兼容后端（`ADI_AI_API_KEY`），仅用于候选提取与异常解释
- **CLI 规范** ——所有脚本统一 `--project <路径> --input <路径> --output <路径> --format json|csv|md|xlsx|pdf --config <路径> --verbose --dry-run`
- **测试** ——黄金样例套件（`pytest`），带公差门槛（图纸面积 ±0.5%、DXF 几何 <0.1%）

## 快速开始

```powershell
# Windows 11 + Python 3.12+
pip install -r requirements.txt

# 1) 从任意混合文件创建规范化项目工作区
python scripts/s01_project_workspace.py --project .\Project01 --input .\Project01\input

# 2) 从图纸 PDF 提取铺装工程量（矢量或按尺寸推算）
python scripts/s02_pdf_plan_takeoff.py --project .\Project01 --input .\Project01\input\plans\civil-set.pdf

# 3) 通过 AsphaltCosts 引擎生成材料数量
python scripts/s10_estimate_report_builder.py --project .\Project01 --format md
```

任意脚本加 `--help` 查看选项。

## 工作原理

- **标准生命周期** ——每个脚本运行 `发现 → 摄取 → 提取 → 归一化 → 校验 → 计算/分类 → 输出 → 审计`。
- **证据状态机** ——每条重要数据按 `提取 → 归一化 → 已校验 → 已验证` 推进；允许停在任一更早状态。
- **AI 边界** ——AI 可以提取候选值、映射同义词、解释异常；但绝不允许凭空发明尺寸、静默改动来源值、替代确定性计算结果，或在无证据时标记"已验证"。
- **人机协同** ——低置信度、比例不明、冲突与缺失数据进入紧凑的复核队列（`review_queue.json` / 报告内摘要），绝不静默修正。
- **审计** ——每次运行把 `run_id`、脚本、耗时、输入哈希、引擎版本、警告、错误与输出写入 `<project>/audit/`。

## 配置

把 `config.example.json` 复制为 `config.json`（或用 `--config` 指向自己的文件）。接口地址、限流与 AI 供应商设置均从配置加载；`asphaltcosts.api_endpoint` 字段可在计算引擎发布 HTTP 接口后启用直连调用——在此之前，客户端使用文档化的网页引擎算法作为带标签的本地镜像（`engine_version: asphaltcosts-web-engine/1.0-mirror`）。

## 开发

```powershell
pip install -r requirements.txt
python tools/make_pdf_fixtures.py   # 生成黄金图纸 PDF（需 pymupdf）
python tools/make_photo_fixtures.py # 生成黄金照片（需 Pillow）
pytest -q
```

黄金测试覆盖：已知图纸面积（±0.5%）、已知 DXF 几何（<0.1%）、规范提取、报价对比、100 张送货单对账、热模型方向检查、照片筛查与报告确定性。

## 独立子仓库

每个业务场景也发布为**独立的 GitHub 仓库**（各自 README、测试、fixtures、许可证，并链接回 [AsphaltCosts.com](https://asphaltcosts.com/)），用 `python tools/build_subrepos.py` 从本仓库重建：

| 子仓库 | 对应脚本 |
|---|---|
| [asphalt-pdf-plan-takeoff](https://github.com/anleeylee/asphalt-pdf-plan-takeoff) | S02 |
| [asphalt-specification-checker](https://github.com/anleeylee/asphalt-specification-checker) | S04 |
| [asphalt-quote-comparator](https://github.com/anleeylee/asphalt-quote-comparator) | S05 |
| [asphalt-delivery-ticket-reconciler](https://github.com/anleeylee/asphalt-delivery-ticket-reconciler) | S06 |
| [asphalt-supplier-quote-normalizer](https://github.com/anleeylee/asphalt-supplier-quote-normalizer) | S07 |
| [asphalt-weather-compaction-planner](https://github.com/anleeylee/asphalt-weather-compaction-planner) | S08 |
| [asphalt-field-photo-analyzer](https://github.com/anleeylee/asphalt-field-photo-analyzer) | S09 |
| [asphalt-estimate-report-builder](https://github.com/anleeylee/asphalt-estimate-report-builder) | S10 |

## 计算引擎

[**AsphaltCosts.com**](https://asphaltcosts.com/) —— 沥青吨数、成本、覆盖面积、车次与铺装计算器：面积 → 压实体积 → 净吨数 → 订购吨数（损耗只计一次）→ 车次 → 材料成本，内置有出处的规划默认值（FHWA 密度 145 lb/ft³，损耗率与车容量可编辑）。

网站始终是确定性计算层：**吨数、体积、覆盖面积、车次与材料成本都来自 AsphaltCosts 引擎，绝不在桌面端重写公式。** 这些脚本解决需要本地文件、批量处理、OCR、CAD 解析、项目证据、AI 文档理解或本地自动化的任务，再把归一化、校验后的数值*喂给*引擎。

> ⚠️ **这是规划工具，不是工程设计。** 所有输出均为规划估算，绝不能当作"已批准施工"或工程结论。

## 安全与隐私

- 本地文件默认留在本地；AI 上传需要逐次显式配置。
- API 密钥存放在环境变量（`ASPHALTCOSTS_API_KEY`、`ADI_AI_API_KEY`）或 Windows 凭据管理器中——绝不写入源码。
- 记录文件哈希，使每份报告都能标识所用来源的确切版本。
- 绝不自动覆盖或删除来源文件；派生文件位于 `working/` 或 `output/`。

## 许可证

MIT —— 见 [LICENSE](LICENSE)。
