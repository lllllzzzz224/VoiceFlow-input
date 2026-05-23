# PROJECT_CONTEXT

## Product

- Name: VoiceFlow Input（语音输入助手）
- Topic: 题目一：语音输入法
- Repository: https://github.com/lllllzzzz224/VoiceFlow-input.git
- Product form: Web voice input workspace, not a native OS input method.
- Target user:
  - 需要快速把语音转成可复制文本的学生、办公用户和开发者。
  - 需要处理中英混合输入、会议摘录、想法记录和长文本草稿的用户。
  - 作品评委与路演面试官。
- Problem:
  - 手动输入长文本效率低。
  - 原生系统输入法工程范围过大，不适合 72h MVP。
  - 普通转写工具如果没有实时反馈、文本修正、历史记录和导出能力，难以体现“输入效率工具”的产品价值。
- Product promise:
  - 用户在浏览器中点击录音，前端通过 WebSocket 把音频流发送到 FastAPI 后端。
  - 后端用 `faster-whisper` 或 mock/fallback adapter 转写，返回实时/准实时文本。
  - 产品提供自动标点、中英文混输修正、AI 修正、历史记录和 Markdown 导出能力。
  - 如果 Web MVP 稳定且仍有时间，再用 Tauri 套壳复用同一套 Web 前端和本地 FastAPI 后端，形成桌面版。

## Topic Source

- Batch time: 2026-05-23 00:00 到 2026-05-25 23:59（Asia/Shanghai）。
- Selected topic: 题目一，语音输入法。
- Requirement: 开发一个语音输入法产品，帮助用户提高文本输入效率；需要了解用户需求并实现输入法开发，平衡准确度、易用性、响应速度、成本等关键因素。
- Research source:
  - `deep-research-report.md` 建议选择题目一，并主动收缩为可交付 MVP。
  - `VLM-report.md` 建议优先借鉴 `faster-whisper`、`whisper.cpp`、`WhisperLive`、`sherpa-onnx` 的架构思想，但不复制源码。

## MVP Closed Loop

```text
浏览器录音 -> WebSocket 音频分片 -> FastAPI 后端 -> ASR adapter -> 文本后处理 -> 前端实时展示 -> 复制 / 历史记录 / Markdown 导出
```

## Delivery Strategy

```text
Phase 1: Web MVP
  browser recorder -> WebSocket -> FastAPI -> mock/faster-whisper -> transcript UI

Phase 2: Product polish
  punctuation -> hotwords -> mixed Chinese/English cleanup -> history -> markdown export -> Xiaomi AI correction

Phase 3: Desktop shell, only if time remains
  Tauri shell -> reuse existing frontend -> launch/connect local FastAPI backend -> optional tray/global shortcut later
```

## Current Phase

- Stage: Web 前后端基础结构已建立，正在对齐 WebSocket mock 闭环与后续真实 ASR 联调。
- In scope:
  - 浏览器录音。
  - WebSocket 流式或准实时传输。
  - FastAPI `/health` 与 `/ws/transcribe`。
  - `faster-whisper` 主 ASR adapter。
  - mock adapter 用于前端联调和测试。
  - Xiaomi API 作为可选 AI 修正或云端 fallback，不作为唯一可运行路径。
  - 自动标点、热词修正、中英文混输清理。
  - 历史记录、复制文本、Markdown 导出。
  - README、demo 视频、第三方依赖与原创范围说明。
- Out of scope:
  - 原生系统输入法内核。
  - Fcitx/Rime/librime 集成。
  - 当前阶段不做桌面托盘、全局热键、系统级文本注入。
  - 自训练 ASR 模型。
  - 持续后台监听、唤醒词常驻、说话人分离。
  - 复制或 vendoring GitHub 参考项目源码。

## Preserved Future Desktop Direction

桌面端没有被取消，只是不进入当前关键路径。后续如果时间允许，优先使用 Tauri 套壳：

- 复用 `frontend/` 页面，不重写 UI。
- 复用 `backend/` FastAPI 和 ASR adapters，不重写识别逻辑。
- 桌面壳只负责窗口、启动本地服务、打包和可选系统集成。
- 可选增强：系统托盘、全局快捷键、自动复制/粘贴、离线模型包。

桌面阶段仍可参考：

- `faster-whisper`: 主 ASR 引擎。
- `whisper.cpp`: 低配/纯离线/量化模型 fallback。
- `WhisperLive`: 实时产品形态、chunk buffer、WebSocket 思路。
- `sherpa-onnx`: VAD、热词、标点恢复、流式 ASR 工程增强。
- `Fcitx/Rime`: 只作为未来真正原生输入法路线的边界研究，不作为 72h MVP 依赖。

## Hard Constraints

- Runtime: Web frontend + FastAPI backend；主分支合并后必须保持可运行。
- Budget: 优先本地推理和开源依赖；如果使用 Xiaomi API，必须记录用途、成本、隐私和 fallback。
- Dependencies: 新增第三方库必须在 `project/docs/DECISIONS.md` 和 README 中说明用途、许可证和原创边界。
- Security:
  - 不提交密钥、token、私有配置、个人隐私音频。
  - `.env`、模型、临时音频、缓存和 `__pycache__` 必须被 `.gitignore` 排除。
  - Xiaomi API key 只能通过本地环境变量或未提交配置注入。
- Open source integrity:
  - 不 git clone 参考项目到本仓库。
  - 不复制第三方源码、README 文案、示例 UI、benchmark 表格或仓库结构。
  - 只阅读 README/API/架构，使用公开依赖或自己实现 adapter。
- Competition:
  - GitHub repository: https://github.com/lllllzzzz224/VoiceFlow-input.git
  - 所有 commit 时间戳必须落在 2026-05-23 00:00 到 2026-05-25 23:59 之间。
  - 开发周期内保持持续 PR 和 commit 记录。
  - PR 标题、功能描述、实现思路、测试方式必须清晰。
  - README 必须显眼放置 demo 视频链接、启动方式、依赖说明、原创范围说明。
  - 仓库权限规则原文存在冲突：同时出现“2026-05-25 23:59 前可私有”和“2026-05-25 00:00 起需公开”。保守策略：提交截止前确保仓库公开可访问，并尽早确认报名表单要求。

## Success Criteria

1. 用户能在浏览器中完成“录音 -> 后端识别 -> 文本展示”的核心闭环。
2. WebSocket 协议支持 start、音频 chunk、end、result、error 基础状态。
3. mock adapter 可稳定联调；`faster-whisper` adapter 能在配置模型后转写短句。
4. 支持基础标点、热词和中英文混输清理；AI 修正作为增强且不编造内容。
5. 支持历史记录、复制和 Markdown 导出。
6. README 清楚说明这是 Web 语音输入助手式 MVP，而非完整 OS 原生输入法。
7. 作品提供延迟、识别质量、提交成功率和失败案例说明。
8. PR 和 commit 分布能体现持续开发过程，主分支随时可运行。

## Read Order For New Dialogs

1. `project/docs/PROJECT_CONTEXT.md`
2. `project/docs/DECISIONS.md`
3. `project/docs/ARCHITECTURE.md`
4. `project/docs/TODOS.md`
5. `project/docs/API_CONTRACTS.md`
6. `project/docs/STATE_MATRIX.md`
7. `project/docs/ACCEPTANCE_CASES.md`
8. `project/docs/AGENT_REUSABLE_PATTERN.md`（涉及 ASR、LLM 或其他 AI 行为时）
9. `project/docs/OPEN_SOURCE_COMPLIANCE.md`
