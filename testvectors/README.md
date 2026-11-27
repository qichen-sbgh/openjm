# 跨端测试向量

协议规范见 [`../docs/tech/protocol.md`](../docs/tech/protocol.md)。这里的每个 `.jm` 都是**冻结样本**：Python、Android、iOS 三端必须给出完全一致的结果，否则说明实现有偏差——不要改样本，去查实现。

## 目录

```text
testvectors/
├── manifest.json          # 三端单测唯一入口：要什么结果，全在这里
├── make_vectors.py        # 生成脚本（需要 openjm-sdk）
├── keys.test.json         # 公开测试密钥，key_id = 254
├── plain/                 # 原始明文，用来核对解密结果
├── valid/                 # 必须解密成功的向量
└── invalid/               # 必须被拒绝的向量
```

## 测试密钥

`key_id = 254 (0xFE)`，由固定串派生，值可以随时重算：

```bash
python3 -c 'import hashlib;print(hashlib.sha256(b"openjm-test-vector-key-v1").hexdigest())'
```

这份密钥是**公开的、只给测试用**。把它写进 App 的测试 source set，不要放进 `main` 的密钥表，也不要拿它加任何真实文档。

## manifest 结构

```json
{
  "protocol": "JM01",
  "test_key_id": 254,
  "keys_file": "keys.test.json",
  "vectors": [
    {
      "id": "v03-password",
      "kind": "valid",
      "file": "valid/v03-password.jm",
      "password": "correct horse battery staple",
      "wrong_password": "wrong horse battery staple",
      "expect": { "doc_id": "…", "name": "hello-openjm.pdf", "size": 679, "pad": 0, "sha256": "…" }
    },
    {
      "id": "v90-truncated",
      "kind": "invalid",
      "file": "invalid/v90-truncated.jm",
      "error": "JMAuthError"
    }
  ]
}
```

| 字段 | 说明 |
| --- | --- |
| `kind` | `valid` 解密成功；`invalid` 必须抛错 |
| `password` | 该向量需要的口令；无口令模式不出现 |
| `wrong_password` | 用它必须得到 `JMAuthError` |
| `expect.sha256` | 解密后明文的 SHA-256 |
| `error` | 期望的错误类型：`JMFormatError` / `JMAuthError` |

## 向量清单

| id | 类别 | 覆盖点 |
| --- | --- | --- |
| `v01-plain-no-pad` | valid | 无感模式、`pad=0`、最小合法样本 |
| `v02-same-source-new-nonce` | valid | 与 v01 同一明文，`doc_id` 相同但密文完全不同（抗指纹） |
| `v03-password` | valid | 口令模式，PBKDF2 10 万次；含错误口令反例 |
| `v04-pad-max` | valid | `pad=4096` 上限，验证填充剥离 |
| `v05-large-multichunk` | valid | 约 192KB，跨多个 64KB 分块，`pad=1234` |
| `v90-truncated` | invalid | 砍掉尾部 1 字节，模拟 QQ 下载中断 |
| `v91-tampered-payload` | invalid | 载荷区翻 1 bit |
| `v92-bad-magic` | invalid | 魔数改成 `JK01` |
| `v93-too-short` | invalid | 40 字节，低于 60 字节下限 |
| `v94-unknown-key-id` | invalid | `key_id=7`，测试密钥库中没有 |
| `v95-zero-meta-len` | invalid | `meta_len` 置 0 |

## 在 openjm-sdk 里跑

```bash
pip install -e ../openjm-sdk
OPENJM_TESTVECTORS="$PWD/testvectors" python -m pytest ../openjm-sdk/tests/test_conformance.py -q
```

不设环境变量时，SDK 会自动找同级目录 `../openjm/testvectors`。

## 重新生成

只在**协议变更**或**补向量**时重跑，且重跑后三端都要重新对齐一次：

```bash
pip install -e ../openjm-sdk
python testvectors/make_vectors.py
```

nonce 与填充是随机的，所以重跑会改写所有 `.jm` 和 `manifest.json`——这是预期行为，不是 diff 噪音。生成脚本会清空并重建 `plain/`、`valid/`、`invalid/`，别把手工文件放进去。

## 加向量

1. 在 `make_vectors.py` 里加一个 `add_valid` / `add_invalid` 块，写清覆盖点；
2. 重跑脚本；
3. 三端各跑一遍，全部通过再提交；
4. 同步更新本文件的清单表。
