# TODOS

## Snapshot

- Date: 2026-05-23
- Current stage: Web MVP first, desktop shell later
- Current baseline: browser recorder + FastAPI WebSocket + ASR adapters + GitHub repository

## Current Tasks

### P0-001: Initialize Bootstrap Governance

Owner: planner / controller
Status: completed

Scope:

- 创建 `project/docs` 启动文档。
- 创建根级工程代理规则文件。
- 将 72h 实战硬性规则写入项目上下文。

Do Not Touch:

- 不实现产品功能。

Acceptance:

- 项目治理文档存在。
- 根目录存在 `AGENTS.md`、`CODEX.md`、`CLAUDE.md`。

Validation:

- `rg --files`

### P0-002: Select Topic And Freeze MVP Boundary

Owner: planner / controller
Status: completed

Scope:

- 选择题目一“语音输入法”。
- 将题目收缩为可交付语音输入助手。
- 明确不做系统级 IME 内核。

Do Not Touch:

- 不引入题目二路线。

Acceptance:

- `PROJECT_CONTEXT.md` 中题目和 MVP 闭环明确。
- `DECISIONS.md` 记录选题和范围收缩。

Validation:

- 人工检查文档是否与题目来源一致。

### P0-003: Switch To Web-First Architecture

Owner: planner / controller
Status: completed

Scope:

- 将当前总方向从桌面 PySide6 改为 Web-first。
- 固化路线：浏览器录音 -> WebSocket -> FastAPI -> ASR adapter -> 前端文本展示。
- 将桌面端定义为后续壳层，而不是当前 MVP。

Do Not Touch:

- 不在当前阶段写 PySide6、Electron、Tauri 或 pywebview 桌面壳。

Acceptance:

- `PROJECT_CONTEXT.md` 是 Web-first。
- `ARCHITECTURE.md` 是 Web-first。
- `API_CONTRACTS.md` 是 WebSocket-first。
- `STATE_MATRIX.md` 是浏览器/WebSocket/ASR 状态。
- `ACCEPTANCE_CASES.md` 是 Web MVP 验收。

Validation:

- `rg -n "PySide6|pynput|sounddevice|热键|托盘|剪贴板|paste" project/docs`
- 旧桌面路线只能出现在“out of scope / later shell”语境中。

### P1-001: Create Competition Repository And First PR

Owner: project owner
Status: in_progress

Scope:

- 正式仓库：`https://github.com/lllllzzzz224/VoiceFlow-input.git`。
- 提交报名表单中的题目和仓库地址。
- 创建首个 PR，内容只包含项目脚手架、文档基线和忽略规则。

Do Not Touch:

- 不在最后一天一次性导入所有代码。
- 不提交题目无关内容。
- 不提交 `__pycache__`、模型、临时音频、`.env`。

Acceptance:

- 仓库创建时间符合批次要求。
- `PROJECT_CONTEXT.md` 记录正式仓库地址。
- `.gitignore` 排除缓存、密钥、模型和临时音频。
- PR 描述包含功能描述、实现思路和测试方式。

Validation:

- 检查仓库创建时间、PR 列表、commit 时间线。
- `rg --files` 检查无明显缓存/音频/模型提交。

### P1-002: Backend WebSocket Mock Closed Loop

Owner: backend
Status: in_progress

Scope:

- FastAPI backend 项目结构。
- `/health`。
- `/ws/transcribe`。
- 支持 `start`、binary audio chunk、`audio_chunk` JSON fallback、`end`。
- mock ASR 返回标准 `transcription_result`。
- WebSocket 测试覆盖 happy path、no audio、invalid JSON、unsupported type。

Do Not Touch:

- 不复制 faster-whisper、WhisperLive、whisper.cpp、sherpa-onnx 源码。
- 不接真实 Xiaomi API key。
- 不改 frontend 文件，除非 PR 明确为联调修复。

Acceptance:

- `python -m compileall backend/app` 通过。
- WebSocket mock smoke test 通过。
- `/health` 可用。

Validation:

- `python -m compileall backend/app`
- `python backend/tests/ws_mock_smoke.py` 或同等命令。

### P1-003: Frontend Browser Recorder Closed Loop

Owner: frontend
Status: in_progress

Scope:

- 浏览器录音按钮。
- `MediaRecorder` 获取麦克风音频。
- WebSocket 连接 `ws://localhost:8000/ws/transcribe`。
- 发送 `start`、binary chunks、`end`。
- 展示连接状态、录音状态、转写状态、错误和 transcript。
- 复制 transcript 按钮。

Do Not Touch:

- 不复制 WhisperLive 前端代码。
- 不做桌面壳。
- 不做复杂历史/Markdown/AI 修正。

Acceptance:

- 前端可打开。
- 与后端 mock 联调时能展示返回文本。
- 麦克风权限失败和 WebSocket 失败有明确提示。

Validation:

- 手动浏览器测试。
- 与 backend mock 服务联调。

### P1-004: Align WebSocket Contract Between Frontend And Backend

Owner: integration
Status: pending

Scope:

- 对齐后端当前 envelope：`{ type: "transcription_result", result: { success, data, error, meta } }`。
- 前端从 `message.result.data.raw_text` 读取文本。
- 统一错误展示。

Do Not Touch:

- 不在前端自行发明另一个协议。
- 不随意重命名后端 `type` 字段。

Acceptance:

- 前端可正确处理 `ack`、`transcription_result`、`error`。
- 后端测试和前端手动联调都通过。

Validation:

- 手动录音一次。
- 空音频或无后端场景验证。

### P1-005: Integrate Faster-Whisper Adapter

Owner: backend
Status: pending

Scope:

- 通过 pip 依赖调用 `faster-whisper`。
- 实现 `FasterWhisperAdapter`。
- 保持 mock adapter 可用。
- 输出同一个 `transcription_result` 合约。
- 记录 `engine=faster_whisper`、`latency_ms`、`model`、`cost_cents=0`。

Do Not Touch:

- 不 vendor `faster_whisper/` 源码。
- 不让模型下载阻塞 mock 联调。

Acceptance:

- mock 测试仍通过。
- 有模型环境时真实短句可转写。
- 模型缺失或失败时返回稳定错误。

Validation:

- compileall。
- mock 测试。
- opt-in faster-whisper 手动测试。

### P1-006: Text Postprocess

Owner: backend
Status: pending

Scope:

- 自动标点基础规则。
- 热词修正。
- 中英文混输空格清理。
- 保留 `raw_text`，追加 `final_text`。

Do Not Touch:

- 不使用 LLM 编造内容。
- 不隐藏 raw transcript。

Acceptance:

- 固定测试句能看到修正效果。
- 失败时 raw transcript 仍可用。

Validation:

- 单元测试或手动固定句测试。

### P1-007: Optional Xiaomi AI Correction

Owner: backend
Status: pending

Scope:

- Xiaomi API adapter 作为可选 AI 修正。
- 未配置 API key 时禁用，不影响本地/mock 路径。
- Provider 失败时 fallback 到 raw/rule postprocess。

Do Not Touch:

- 不提交 API key。
- 不把 Xiaomi API 做成唯一可运行路径。
- 不在日志中打印鉴权信息。

Acceptance:

- missing-key path 可解释。
- mock/test path 可验证成功和失败。
- README 说明隐私、成本和用途。

Validation:

- mock 或测试 key 验证。

### P1-008: History And Markdown Export

Owner: frontend + backend
Status: pending

Scope:

- 保存最近 transcript 历史。
- 展示 engine、latency、时间。
- 支持 Markdown 导出。

Do Not Touch:

- 不默认保存原始音频。
- 不上传历史。

Acceptance:

- 多次识别后可查看历史。
- 可导出 Markdown。

Validation:

- 手动录音 3 次后导出。

### P1-009: Desktop Shell Later

Owner: future
Status: pending

Scope:

- Web MVP 跑通后，如仍有时间，再使用 Tauri 套壳。
- 桌面壳复用前端页面和本地 FastAPI 服务。
- 保留桌面端方法论：本地服务、离线模型、可选托盘/快捷键、桌面打包。
- 保留参考路线：`whisper.cpp` 低配离线、`sherpa-onnx` VAD/热词/流式增强、Fcitx/Rime 原生输入法边界研究。

Do Not Touch:

- 不在 Web MVP 未跑通前做桌面端。
- 不重新写一套业务逻辑。
- 不引入 Electron、pywebview 或其他桌面壳作为并行路线。

Acceptance:

- Web 端核心功能已稳定。
- README 已有 Web 启动和演示路径。
- Tauri 桌面壳不破坏 Web 版本。
- 桌面壳章节明确复用现有 Web/Backend，不重写核心逻辑。

Validation:

- 后续单独 PR 和单独验收。

### P1-010: Final README, Demo And Compliance

Owner: project owner
Status: pending

Scope:

- 完成 README。
- 放置 demo 视频链接。
- 列出依赖、许可证、原创范围、启动方式、评估结果。
- 列明 `faster-whisper`、WhisperLive、whisper.cpp、sherpa-onnx 等直接依赖/参考用途。

Do Not Touch:

- 不隐藏 demo 链接。
- 不遗漏第三方模型/库说明。
- 不复制参考项目 README 段落。

Acceptance:

- README 首页显眼展示 demo 链接。
- 干净环境按 README 可启动。
- `OPEN_SOURCE_COMPLIANCE.md` 与 README 一致。

Validation:

- 按 README 从零启动。
- 播放 demo 链接并确认可访问。
- `rg --files` 检查无缓存、模型、音频、密钥。
