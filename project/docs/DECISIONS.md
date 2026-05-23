# DECISIONS

## D-001: Bootstrap Before Feature Coding

Decision:

在写任何产品功能代码前，先建立项目治理文档、工程代理规则、任务拆分、契约和验收标准。

Reason:

本次实战评审不仅看最终作品，也看开发过程、架构清晰度、代码质量、PR 质量和 commit 分布。提前建立规则可以避免临尾突击、范围失控和文档缺失。

Impact:

后续任务必须先读取 `project/docs`，再做最小范围实现。功能完成并验证后，需要更新相关文档和任务状态。

Do Not Do:

不要在题目、MVP 闭环和任务边界不清晰时直接生成大段功能代码。

## D-002: Small PR Delivery Model

Decision:

使用小粒度 PR 交付，每个 PR 只做一件事，并包含标题、功能描述、实现思路和测试方式。

Reason:

评审规则明确关注 PR 数量与质量、commit 分布合理性。小 PR 更容易审查、回滚和讲清楚开发过程。

Impact:

大功能必须拆成多个任务，例如：Web 脚手架、后端 WebSocket、前端录音、ASR adapter、文本后处理、AI 修正、历史导出、README/demo。

Do Not Do:

不要把多个无关功能混进同一个 PR；不要空 PR 描述；不要只在最后一天一次性导入代码。

## D-003: Main Branch Must Stay Runnable

Decision:

每次合并到主分支后，主分支都必须处于可启动、可复现演示的状态。

Reason:

评委可能在任意时间查看仓库，且规则要求主分支代码保持可运行。

Impact:

每个 PR 合并前至少执行对应验证命令或手动验收，并在 PR 描述中记录验证方式。

Do Not Do:

不要合并明显无法启动、依赖缺失、配置不可复现或 README 与实际不一致的代码。

## D-004: Choose Topic 1 Voice Input Method

Decision:

本项目选择题目一“语音输入法”。

Reason:

`deep-research-report.md` 判断语音输入法更适合 72h 稳定交付：ASR 技术栈成熟、核心链路更线性、评估指标更客观、成本更可控。

Impact:

后续产品、架构、任务、API、状态和验收都围绕语音输入助手展开。

Do Not Do:

不要继续并行设计题目二“2D 游戏素材生成”的实现路线。

## D-005: Build Web Assistant MVP, Not Native IME Kernel

Decision:

将“语音输入法”收缩为“浏览器语音输入助手 / Web 语音输入工作台”，不做系统级原生输入法内核。

Reason:

真正的系统级输入法会涉及 Fcitx、Rime/librime、系统候选框、输入法协议和跨平台适配，72h 内风险过大。Web 版更容易演示浏览器录音、实时文本、历史、Markdown 导出和 AI 修正。

Impact:

核心交付是浏览器录音、WebSocket、FastAPI、ASR 转写、文本后处理、历史和导出。

Do Not Do:

不要在 MVP 阶段集成 Fcitx/Rime/librime；不要实现 PySide6 托盘、全局热键或系统级文本注入。

## D-006: Web First

Decision:

MVP 优先采用 Web frontend + FastAPI backend。

Reason:

当前代码已经形成 `frontend/` 与 `backend/` 基线；浏览器录音和 WebSocket 更适合快速形成可演示闭环，也更容易让评委按 README 复现。

Impact:

README、架构图、任务拆分和验收都以浏览器访问前端、后端启动 FastAPI 为主。

Do Not Do:

不要继续把 PySide6、sounddevice、pynput 作为首版技术栈；这些只作为早期研究记录，不作为当前实现方向。

## D-007: Local-First ASR With Optional Fallback

Decision:

优先选择本地或低成本 ASR 主链路；主候选为 `faster-whisper`，测试与联调用 mock adapter，云端 fallback 或 AI 修正可考虑 Xiaomi API。

Reason:

本地推理成本低、隐私边界清晰；mock adapter 能让前端和 WebSocket 协议先跑通；fallback 能解释成本、速度和稳定性的权衡。

Impact:

第一版先保证 WebSocket mock 闭环可运行，再接真实 `faster-whisper` adapter。Xiaomi API 不作为唯一可运行路径，避免评委缺少密钥时无法复现。

Do Not Do:

不要同时接入多个 ASR 引擎导致范围膨胀；不要提交未说明许可证或成本的模型/服务；不要把 API key 写入仓库。

## D-008: Objective Evaluation Is Part Of The Product

Decision:

项目必须包含基础评估材料：端到端延迟、转写质量、成功/失败次数、错误案例和导出效果。

Reason:

题目要求平衡准确度、易用性、响应速度和成本。评估材料能让路演表达从“能跑”提升到“可证明地有用”。

Impact:

需要准备测试短句、WebSocket 测试、手动测试流程和 README 中的评估说明。

Do Not Do:

不要只用主观演示证明效果；不要隐藏失败样例。

## D-009: Use Reference Projects Without Code Copying

Decision:

GitHub 高分项目只作为架构、API 使用方式、产品边界和风险判断的参考，不复制大段源码、README、示例 UI、测试数据或目录结构。

Reason:

比赛规则明确要求自主完成，代码或技术抄袭、代码重复率超过 50% 将取消资格。直接复制参考仓库会带来学术诚信、许可证和评审风险。

Impact:

实现时优先通过包管理器安装依赖并调用公开 API；自有代码只写适配层、WebSocket 协议、UI、后处理、评估和业务胶水。所有参考来源必须在 README 或 `OPEN_SOURCE_COMPLIANCE.md` 中列明。

Do Not Do:

不要 git clone 参考项目到本仓库；不要 vendoring `faster-whisper`、`WhisperLive`、`whisper.cpp`、Vosk、sherpa-onnx、Fcitx、Rime 等项目源码；不要照搬它们的 README、benchmark 表格或示例结构。

## D-010: Freeze First Implementation Stack

Decision:

首版实现栈采用 Browser frontend + FastAPI + WebSocket + faster-whisper + mock adapter。Xiaomi API 作为可选 AI 修正或 fallback，whisper.cpp/Vosk/sherpa-onnx 作为后续研究路线。

Reason:

当前项目已经完成简单前后端搭建；该组合能最快形成“浏览器录音 -> 后端转写 -> 前端文本回显”的演示闭环。

Impact:

后续脚手架、模块命名和任务拆分围绕 `frontend/`、`backend/`、WebSocket 协议、ASR adapter、postprocess、history/export 展开。

Do Not Do:

不要在首版同时实现 whisper.cpp、Vosk、sherpa-onnx 和多个云服务；不要把 fallback 做成阻塞 MVP 的主任务。

## D-011: Tauri Desktop Shell Is A Later Bonus

Decision:

如果 Web MVP、真实 ASR、历史导出和 demo 资料都稳定完成且仍有时间，再使用 Tauri 套壳做桌面版。桌面端方向保留，但不抢当前 Web MVP 的关键路径。

Reason:

Tauri 可以复用现有 Web 前端，桌面端加分但不是核心验收路径。提前做桌面壳会分散 WebSocket、ASR、后处理和 demo 的关键交付注意力。

Impact:

当前 PR 不实现 Tauri。后续如启动桌面壳，必须单独开 PR，并保证 Web 版仍可独立运行。桌面壳应复用现有 `frontend/` 和 `backend/`，不重写 ASR、WebSocket、后处理、历史和导出逻辑。

Do Not Do:

不要在 Web MVP 未跑通前引入 Tauri、Electron、pywebview 或其他桌面壳；不要为桌面壳重写业务逻辑。

## D-012: Preserve Desktop Research And Reference Projects

Decision:

保留桌面端后续需要的方法和参考项目，但把它们记录为“later desktop / future native IME research”，不是当前实现任务。

Reason:

Web 先跑通可以快速交付；桌面壳和原生输入法路线仍有答辩价值和后续拓展价值，不能从项目上下文里丢失。

Impact:

文档中必须保留 `faster-whisper`、`whisper.cpp`、`WhisperLive`、`sherpa-onnx`、Fcitx/Rime 的参考定位。后续桌面端优先 Tauri，未来真正原生输入法只作为路线说明。

Do Not Do:

不要把“当前不做桌面”理解为“删除桌面路线”；也不要把参考项目源码拉进仓库。
