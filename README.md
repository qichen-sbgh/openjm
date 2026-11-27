# openjm

`.jm` 加密文档容器。发送端把 PDF 封装成 `.jm` 丢进 QQ 群，接收端点开、校验、解密，落进自己的书架里读。

这个仓库是**协议与契约的单一真相**：规范、跨端测试向量、密钥登记都在这儿，另外两个仓库围着它对齐。

| 仓库 | 角色 | 技术栈 |
| --- | --- | --- |
| **`openjm`**（本仓） | 协议 v1 规范、跨端测试向量、密钥登记、路线图 | Markdown + Python（生成脚本） |
| [`openjm-sdk`](https://github.com/qichen-sbgh/openjm-sdk) | 发送端加密 SDK、校验/解密参考实现 | Python 3.9+ / `cryptography` |
| [`openjm-mobile`](https://github.com/qichen-sbgh/openjm-mobile) | 阅读器 App（Android + iOS） | Kotlin Multiplatform + Compose Multiplatform |

## 为什么拆三个仓库

发送端和消费端的代码没有一行能复用（一边 Python，一边 Kotlin 原生加密），合在一起只会让三套 CI 互相干扰。真正需要共享的不是代码，是**字节级行为**——所以共享物落在这里：`docs/tech/protocol.md` 定规则，`testvectors/` 定答案。

跨仓约定只有三条：

1. **协议版本只有一个真相。** 本仓打 tag `proto-v1`，向量跟着 tag 走；另两仓 README 第一行写 `compatible: proto-v1`，CI 按 tag 取向量。不用 submodule 三仓互挂。
2. **根密钥哪都不进。** 三个仓库都只有 `keys.example.json` / `keys.test.json`，真钥匙走密码管理器，登记表见 [`docs/tech/key-registry.md`](docs/tech/key-registry.md)。
3. **对齐验收放本仓。** 谁能解哪个向量，看下面的状态表，不看群消息。

## 快速开始

```bash
# 1) 装 SDK（首次）
git clone https://github.com/qichen-sbgh/openjm-sdk ../openjm-sdk
pip install -e ../openjm-sdk

# 2) 用一个向量验证链路
export OPENJM_KEY_FILE="$PWD/testvectors/keys.test.json"
python -m openjm verify testvectors/valid/v01-plain-no-pad.jm

# 3) 跑全部向量
OPENJM_TESTVECTORS="$PWD/testvectors" python -m pytest ../openjm-sdk/tests/test_conformance.py -q
```

真实文档加密（生产密钥自行准备，格式见 [`docs/tech/key-registry.md`](docs/tech/key-registry.md)）：

```bash
$OPENJM_KEY_FILE=~/keys/prod.json python -m openjm encrypt 深入理解计算机系统.pdf
# → doc_20261127_a1b2c3d4.jm
```

## 三端对齐状态

| 实现 | 头部解析 | 无感模式 | 口令模式 | 填充剥离 | 反例 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| Python（`openjm-sdk`） | ✅ | ✅ | ✅ | ✅ | ✅ | 向量全过 |
| Android（`openjm-mobile`） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | 骨架待实现 |
| iOS（`openjm-mobile`） | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | 骨架待实现，注意 `kCCModeOptionCTR_BE` |

## 文档

三仓的文档都收在这里，导航见 [`docs/README.md`](docs/README.md)：

```text
docs/README.md                    # 文档导航，先看这个
docs/requirements/requirements.md # 需求：场景、FR/NFR、非目标、验收口径
docs/tech/protocol.md             # 协议规范（冻结）
docs/tech/decisions.md            # 技术决策与被否方案
docs/tech/sdk.md                  # 发送端设计
docs/tech/mobile.md               # 移动端设计
docs/tech/key-registry.md         # key_id 分配与轮换，不记密钥值
docs/test/test-plan.md            # 分层、环境、缺陷分级、退出标准
docs/test/acceptance.md           # 需求→用例追溯矩阵、真机清单
docs/process/iteration.md         # 迭代规范：版本、分支、门禁、DoD、发布
docs/process/doc-rules.md         # 文档规范：命名、模板、清理
testvectors/                      # 11 个冻结向量 + 生成脚本
.github/                          # CI 与 PR 模板
```

改代码之前先看 [`docs/process/iteration.md`](docs/process/iteration.md)：三仓的版本号、分支命名、合并门禁、协议变更 SOP 都在里面。

## 协议关键决策

| 项 | 定稿 | 一句话理由 |
| --- | --- | --- |
| 加密 | AES-128-CTR 全量流式 + 尾部 32B HMAC-SHA256 | 全量密文防扫描、硬件加速、天然支持 Seek |
| 密钥 | 内置根密钥无感直开（`key_id` 版本化）+ `Flags` 预留口令模式 | 日常分发零输入摩擦，高敏文档按需加口令 |
| 防风控 | 随机 nonce + 脱敏文件名 + 加密 Meta + 0–4KB 随机填充 | 消除哈希指纹、明文文件名与固定体积特征 |
| 完整性 | Encrypt-then-MAC，常量时间比对 | 一次比对同时挡截断、损坏、篡改与口令错误 |
| 消费端 | KMP + CMP 共享协议与 UI，PDF 渲染走平台原生 | Android 用 PDFium、iOS 用 PDFKit，避开 ROM 字体与缩放问题 |
| 本地存储 | 校验通过即解密进私有沙盒，不留 `.jm`、不导出明文 | 省一半空间，二次打开秒开，书架按 `doc_id` 去重 |

## 路线

- [x] 协议 v1 冻结、Python 参考实现、跨端测试向量集
- [ ] KMP 共享加密核心与两端 `expect/actual` 互测
- [ ] QQ 唤起真机兼容性（`.jm.1`、`application/octet-stream`、SAF 兜底）
- [ ] 书架 + 阅读进度闭环，群内灰度包
- [ ] 远期：超大 PDF 零落盘按需解密（CTR 随机偏移，v1 协议无需改动）

## 不做什么

- 不做高强度密码学对抗：根密钥内置在 App 里，目标是躲过群文件扫描与误撞哈希，不是对抗逆向。
- 不做阅后即焚、不做明文导出分享：文档进沙盒就只在该 App 内可见。
- 不在 v1 上做兼容性微调：任何字节级改动都升 `version`。
