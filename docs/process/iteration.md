# 迭代规范

| 项 | 值 |
| --- | --- |
| 状态 | 生效，v1 |
| 最后更新 | 2026-11-28 |
| 适用范围 | `openjm` / `openjm-sdk` / `openjm-mobile` / `astrbot_plugin_openjm` 四仓 |

这份文件是“怎么推进工作”的唯一约定。它只管流程，不管技术——技术看 [`tech/`](../tech/)，需求看 [`requirements/`](../requirements/)。

---

## 1. 仓库职责

| 仓库 | 拥有什么 | 不许做什么 |
| --- | --- | --- |
| `openjm` | 协议规范、决策记录、测试向量、需求/测试/流程文档 | 不写业务实现 |
| `openjm-sdk` | 发送端实现 | 不定义协议、不许自己造向量 |
| `openjm-mobile` | 消费端实现（Android + iOS） | 同上 |
| `astrbot_plugin_openjm` | 群聊自动化（发号 → 出 `.jm`），只做调用编排 | 不实现协议、不自己造向量、不复制 SDK 代码（依赖要 pin tag） |

**判断某样东西该放哪**：能被其它仓库“引用为依据”的，放总仓；只能被一个仓库使用的，放那个仓库。

## 2. 版本体系

三套版本号互相独立，别混：

| 对象 | 版本 | 载体 | 何时 +1 |
| --- | --- | --- | --- |
| 协议 | `JM01`（magic + `version=0x01`） | 文件头 | 字节级语义变化时必须升 `JM02` |
| 文档 | `v1`、`v2`（文档头字段，**不进文件名**） | `docs/` | 需求或规范有实质变化，而非错别字 |
| SDK | `0.x.y`（SemVer） | `pyproject.toml` + tag | 接口/行为变化 |
| App | `0.x.y`（versionName） | `build.gradle.kts` + tag | 可分发的行为变化 |
| 插件 | `0.x.y` | `metadata.yaml` + tag | 玩家可见行为变化（配置项/指令/媒体格式） |

Tag 命名（四仓统一）：

```text
proto-v1        # 总仓，协议冻结点，向量随 tag 走
docs-v2         # 总仓，需求/测试文档大改（可选）
sdk-v0.1.0      # SDK 仓
app-v0.1.0      # 移动端仓
plugin-v0.1.0   # 插件仓
```

两个实现仓（SDK / mobile）README 首屏必须有一行 `compatible: proto-v1`，协议升级时同步改；
插件仓不实现协议，它只需要把依赖 pin 到某个 `sdk-vX.Y.Z`。

## 3. 迭代节奏

- **里程碑（M）**：交付级目标，对应 [`README`](../../README.md) 的路线图，通常跨多个迭代。
- **迭代（I）**：默认 **1 周**。周一开、周五收，收口必须产出一个可验证增量（不是“写了一半”）。

每个迭代开始时，在 PR 里写三行：本轮目标、验收方式、不做什么。收口时把结果（跑了什么、过了几项、已知问题）写回同一个 PR——仓库里不留迭代记录文件。

个人开发也别省这三行——它防的是“一周过去但说不清做了什么”。

### 3.1 当前阶段

里程碑按平台拆，**Android 先行、iOS 冻结**（依据 [`decisions.md`](../tech/decisions.md) D10）：

| 里程碑 | 目标 | 进入条件 | 状态 |
| --- | --- | --- | --- |
| M1 Android 地基 | `assembleDebug` 通过；11 个向量在 Android 侧全过 | 无 | ✅ 完成（2026-11-27） |
| M2 Android 闭环 | 导入 → 私有沙盒 → 书架去重 → PDFium 阅读 → 进度恢复 | M1 完成 | ✅ 完成（2026-11-27，模拟器验证；真机兼容留 M3） |
| M3 真机兼容 | QQ 唤起与 SAF 兜底在设备上可用 | M2 完成 | 改为模拟器验收（2026-11-27 决定）：VIEW/SEND 用 `am start` 模拟、SAF 在模拟器上验；ROM 差异项按需抽验，不作为发版门槛 |
| M4 iOS 对齐 | 编译校对 CommonCrypto → 唤起 → PDFKit | M3 完成（Android 稳定） | 冻结 |

里程碑状态只在这里维护，README 只放一句指向本表。

**v1 范围已冻结（2026-11-28）**：FR-18（多格式路由）与 FR-19（零落盘 Seek）不做，NFR-01（移动端性能采样）不计入门槛。
v1 的功能需求到此封口——P0 / P1 全部交付，P2 两条转入 v2 清单。剩下的只有发版准备（生产密钥、版本号与 tag），不是功能开发。

## 4. 分支与提交

**主干开发**（trunk-based），`main` 永远可构建、CI 永远绿。分支只活几天：

```text
feat/<短描述>      新功能
fix/<短描述>       缺陷
docs/<短描述>      仅文档
chore/<短描述>     构建/依赖/CI
proto/<短描述>     协议或向量变更（单独走，见 §6）
```

提交信息用 Conventional Commits，scope 固定这几个：

```text
feat(sdk): ...        feat(mobile): ...      feat(proto): ...
fix(sdk): ...         docs(req): ...         test(vectors): ...
ci: ...               chore: ...
```

一次提交只做一件事。**禁止**把“改协议 + 改实现 + 顺手重构”塞进同一个提交——协议改动要能被单独 revert。

## 5. 合并门禁（PR 三条硬规则）

1. **CI 必须绿**。红了不许合，不许“先合了再修”。
2. **行为变更必须带测试**。改了什么行为，就要有一条能证明它的用例；实在无法自动化的，在 PR 描述里写手工验证步骤和结果。
3. **文档同步**。按 §7 的矩阵判断这次改动波及哪些文档，波及就必须在同一次 PR 里改完。

PR 描述用 [`.github/pull_request_template.md`](../../.github/pull_request_template.md) 的模板，其中“影响面”一栏必须勾选，不许留空。

## 6. 协议变更 SOP（v1 已冻结）

改协议不是改代码，走这条线：

1. **提案**：在总仓开 issue，写清楚“现在哪里不够用、不改会怎样、改了什么”。
2. **定版本**：只要动了字节语义（头部、派生、Meta、校验顺序），就是 `JM02`，**不允许**在 `JM01` 上做“兼容微调”。
3. **改规范**：就地更新 [`protocol.md`](../tech/protocol.md)（不新建 `protocol-v2.md`），把文档头的协议版本改成 `JM02`，并同步 [`decisions.md`](../tech/decisions.md)。
4. **重生成向量**：`python testvectors/make_vectors.py`，提交新向量与 `manifest.json`。
5. **三端对齐**：SDK 与移动端各跑一遍，所有向量通过，结果贴 PR。
6. **打 tag**：`proto-v2`，两个实现仓 README 的 `compatible:` 行同步升级。
7. **兼容说明**：明确“旧文件还能不能打开、旧 App 还能不能用新文件”。默认要求：新 App 能解旧文件。

只加验证用例、不动字节语义的，不算协议变更，只算向量补充（走 `test(vectors)`）。

## 7. 变更影响矩阵

| 改了什么 | 必须同时更新 |
| --- | --- |
| 需求（增删改 FR） | `requirements/requirements.md` + `test/acceptance.md` 追溯矩阵 |
| 字节语义 | `tech/protocol.md` + `tech/decisions.md` + 向量 + 两个实现仓的 `compatible:` |
| 实现行为（不改协议） | 对应仓库代码 + 测试 + `tech/` 里对应的设计文档 |
| 测试策略 | `test/test-plan.md` + `acceptance.md` |
| 流程 | `process/iteration.md` 或 `doc-rules.md` 本身 |
| 密钥用途/轮换 | `tech/key-registry.md` |

## 8. 完成定义（DoD）

| 改动类型 | 完成 = |
| --- | --- |
| 功能 | 代码 + 测试 + 文档三件套 + CI 绿 + 追溯矩阵状态更新 |
| 缺陷 | 复现用例（先红后绿）+ 修复 + 回归结论 |
| 协议/向量 | 规范 + 决策记录 + 向量 + 三端回放结果 + tag |
| 文档 | 内容准确 + 交叉引用可达（没有死链）+ CHANGELOG 一行 |
| 依赖/构建 | 能构建 + CI 绿 + 说明为什么引这个依赖（一句就够） |

## 9. 发布与回滚

- **SDK**：`sdk-vX.Y.Z` tag → 本地 `pip install` 验证 → 通知使用方升级。
- **App**：推送 `app-vX.Y.Z` tag，GitHub Actions 注入密钥与签名材料出包并挂 Release（见 `openjm-mobile` 的 `release.yml`）；群内直发 APK。
- **插件**：推送 `plugin-vX.Y.Z` tag；AstrBot 侧是 git 拉取，用户更新插件目录即可。发布前把 `requirements.txt` 里的 SDK pin 指到对应 `sdk-vX.Y.Z`。
- **回滚**：App 回滚 = 重发上一个版本的包；SDK 回滚 = 回退 tag 并说明原因；插件回滚 = 回退 tag 并通知用户重拉。
- **密钥**：轮换流程见 [`key-registry.md`](../tech/key-registry.md)，移除旧密钥是**单独一次发布**，不许和功能一起发。

## 10. 记录

| 记录 | 位置 | 频率 |
| --- | --- | --- |
| 变更日志 | 各仓 `CHANGELOG.md` | 每次合并到 main |
| 迭代小结 / 验收记录 | PR 描述（合上即进 git 历史，**不落成仓库文件**） | 每迭代 |
| 决策 | `docs/tech/decisions.md` | 每次做个取舍 |
| 已知问题 | 各仓 issue | 随时 |

仓库里只留“当前有效”的东西：没有按日期命名的迭代目录，没有 `docs/iterations/`，没有 `archive/`。要翻历史就翻 git。

## 11. 跨仓同步

总仓是唯一真相，同步靠 **tag + 一行声明 + CI**，不靠 submodule、不靠复制粘贴：

```text
总仓打 proto-v1 ──▶ SDK/mobile 的 README 写 compatible: proto-v1
                 └─▶ CI 按 tag 拉向量，跑不过就是红的

SDK 打 sdk-v0.1.0 ──▶ 插件 requirements.txt pin 到该 tag
                    └─▶ 插件 CI 装这个 tag 跑测试，装不上就是红的
```

仓库之间**不复制代码**。唯一允许的代码依赖是两处，都有明确边界：

- 总仓的向量生成脚本导入 SDK（`testvectors/make_vectors.py`）；
- 插件通过 pip 依赖 SDK 包，并 pin 到 tag——不是把 SDK 源码拷进插件。

其余一切只共享规范与样本。
