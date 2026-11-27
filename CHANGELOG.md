# 变更日志

本仓只记录**协议、规范、向量、文档结构**的变化；实现变更记在各自仓库的 CHANGELOG。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [`docs/process/iteration.md`](docs/process/iteration.md) §2。

## [Unreleased]

### Changed
- 文档拆分为 `requirements/` / `tech/` / `test/` / `process/` 四个域，新增文档导航与文档规范；
- 文档文件名去掉版本号（`requirements.md` / `protocol.md` / `test-plan.md` / `acceptance.md`），一类一份、原地更新，不建版本副本与存档目录；
- `docs/test/acceptance.md`：FR-12 / FR-13 由 ⬜ 升到 🟡（沙盒落盘与书架去重已有自动化用例，真机待验），FR-04 / FR-08 / FR-11 同步移动端进展；
- `docs/test/test-plan.md`：自动化现状同步到移动端 13 例，L2 口径改为「Android 本地可回放、CI 无向量仓时 skip」，本地环境补上 Windows；
- `docs/tech/mobile.md`：状态由「骨架已落地，未编译验证」改为「Android 导入链路已实现」，并更新未做项；
- `docs/process/iteration.md`：M2 状态改为进行中；
- `docs/test/acceptance.md`：FR-14 / FR-15 / FR-16 由 ⬜ 升 🟡（PDF 渲染已接、进度在内存层回写，真机未验）；
- `docs/test/test-plan.md`：移动端用例数更新为 15 例，并注明 CI 里 9 例 skip、书架/进度 6 例照跑；
- `docs/tech/mobile.md`：状态改为「导入链路 + PDFium 渲染已实现」，新增「已知代价」一节（APK 体积、渲染无法自动化）；
- `docs/process/iteration.md`：M2 状态更新为「导入/沙盒/去重/PDF 渲染已完成，余封面与进度落库」；
- `docs/test/acceptance.md`：FR-12 / FR-13 升 ✅（模拟器实测：沙盒只有明文、重复导入不丢进度），FR-16 补上「模拟器已渲染」；
- `docs/test/test-plan.md`：环境一节补模拟器 AVD（`android-36;default;x86_64`，WHPX 无头），自动化现状加「模拟器 E2E 4 步已跑通」；
- `docs/tech/mobile.md`：注明链路已在 Android 16 模拟器端到端跑通；
- `docs/test/acceptance.md`：FR-14 由 🟡「封面未做」改为「模拟器已验证封面与进度标签」；
- `docs/tech/mobile.md` / `docs/process/iteration.md`：封面实现后同步「已写 / 未做」与 M2 进度；
- `docs/tech/mobile.md`：新增 §5.1「持久化选型」（JSON vs 内存 vs Room KMP 的取舍与替换成本）；
- `docs/test/acceptance.md`：FR-15 升 ✅（持久化 + 模拟器杀进程实测），`test-plan.md` 用例数同步到 20；
- `docs/process/iteration.md`：M2 标记完成（模拟器验证，真机兼容留 M3），`decisions.md` 待定项补「书架持久化实现」；
- `docs/test/test-plan.md`：模拟器 E2E 明确定义为「一条命令」（`openjm-mobile/tools/emulator-e2e.ps1 -Fresh`），并入迭代收口步骤；
- `docs/test/acceptance.md`：FR-04 / FR-17 升 ✅（口令弹窗已接；免密续读由「只存明文」结构性满足），`docs/tech/mobile.md` 未做项去掉口令弹窗；
- `docs/tech/mobile.md`：未做项去掉「页内偏移恢复」，§8 更新 APK 体积口径（release 16MB）；`docs/test/test-plan.md` 模拟器 E2E 改为 6 步；
- 2026-11-27 决定：**用模拟器代替真机验收**（`iteration.md` 的 M3 与 `test-plan.md` 的真机口径同步改写），FR-07 / FR-08 由 ⬜ 升 🟡（模拟器已验证，真实 QQ / SAF 未验）；
- `docs/tech/mobile.md`：「已写」补导入进度反馈与自适应图标；
- `docs/tech/mobile.md`：「已写」补书架管理（改名/删除）、阅读页页码条与深色主题。

### Added
- `docs/process/iteration.md`：版本体系、分支与提交、合并门禁、协议变更 SOP、DoD、发布与回滚；
- `docs/test/test-plan.md`、`docs/test/acceptance.md`：测试分层与需求追溯矩阵；
- `docs/requirements/requirements.md`：FR-01..FR-19、NFR-01..NFR-05 与验收口径；
- CI 增加文档卫生检查：相对链接可达、文档头齐全、`docs/` 文件白名单（防文档越堆越多）；
- `.gitattributes`：`testvectors/**` 按二进制处理，修掉 Git for Windows 默认 `core.autocrlf=true` 把 `plain/*.pdf` 转成 CRLF、导致本地 `check_vectors.py` 误报「明文 sha256 与清单不符」的问题。

## [proto-v1] - 2026-11-27

### Added
- `.jm` v1 协议冻结：28B 明文头、AES-128-CTR、HKDF-SHA256 派生、尾部 32B HMAC-SHA256；
- 11 个跨端测试向量（5 valid + 6 invalid），`key_id=254` 公开测试密钥；
- 向量结构校验 CI（长度恒等式、明文 sha256、头部字段）；
- `docs/tech/key-registry.md`：key_id 分配与轮换流程。
