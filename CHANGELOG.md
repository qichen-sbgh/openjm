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
- `docs/process/iteration.md`：M2 状态改为进行中。

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
