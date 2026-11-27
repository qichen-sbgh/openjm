# openjm 文档导航

先看这张表，再看具体文档。三仓只有这里放文档——`openjm-sdk` 和 `openjm-mobile` 的 README 只写“怎么用”和“缺什么”，设计、需求、测试都在本仓。

| 你想知道 | 看这里 |
| --- | --- |
| 这东西到底要解决什么问题、做到什么算完成 | [`requirements/requirements.md`](requirements/requirements.md) |
| `.jm` 文件的字节长什么样 | [`tech/protocol.md`](tech/protocol.md) |
| 为什么是 AES-CTR 而不是加密 ZIP | [`tech/decisions.md`](tech/decisions.md) |
| 发送端怎么设计、错误怎么分 | [`tech/sdk.md`](tech/sdk.md) |
| 移动端怎么唤起、怎么单遍导入 | [`tech/mobile.md`](tech/mobile.md) |
| 密钥怎么编号、怎么轮换 | [`tech/key-registry.md`](tech/key-registry.md) |
| 测什么、怎么测、还差多少 | [`test/test-plan.md`](test/test-plan.md) |
| 每条需求验到什么程度了 | [`test/acceptance.md`](test/acceptance.md) |
| 分支、提交、PR、发布怎么走 | [`process/iteration.md`](process/iteration.md) |
| 文档写在哪、怎么写 | [`process/doc-rules.md`](process/doc-rules.md) |

## 文档地图

```text
docs/
├── README.md               # 本文件：导航
├── requirements/
│   └── requirements.md     # 要什么、做到什么算完成
├── tech/
│   ├── protocol.md         # 字节格式（冻结）
│   ├── decisions.md        # 为什么这么选，含被否方案
│   ├── sdk.md              # 发送端设计
│   ├── mobile.md           # 移动端设计
│   └── key-registry.md     # key_id 登记与轮换
├── test/
│   ├── test-plan.md        # 分层、环境、缺陷分级、退出标准
│   └── acceptance.md       # 追溯矩阵、真机清单
└── process/
    ├── iteration.md        # 迭代规范
    └── doc-rules.md        # 文档规范
```

文档之外的两处：`testvectors/` 是冻结样本与生成脚本（[说明](../testvectors/README.md)），`.github/` 是 CI 与 PR 模板。

## 四条约定

1. **同一份事实只写一处**，其余地方链接过去。复制的文档一定会两边不一致。
2. **需求 / 技术 / 测试三件套同进同退**：改了行为，测试追溯矩阵的状态要跟着动；改了字节语义，四件（协议、决策、向量、两仓 `compatible:`）一起动。矩阵见 [`iteration.md`](process/iteration.md) §7。
3. **文档里的命令必须能直接跑**。跑不通的命令比没有命令更糟。
4. **一个主题一份文件，原地更新**。文件名不带版本号和日期，没有 `v2` 副本、没有 `archive/`；历史交给 git 和 `CHANGELOG.md`。迭代过程记录写在 PR 里，不落成仓库文件。
