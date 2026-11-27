# `.jm` 容器协议规范

| 项 | 值 |
| --- | --- |
| 状态 | 已冻结（frozen） |
| 协议版本 | `JM01`（magic `"JM01"`，头部 `version = 0x01`） |
| 文档版本 | v1（原地更新，不改文件名） |
| 最后更新 | 2026-11-27 |

任何字节级改动都必须升协议版本（`JM02`），不允许在 `JM01` 上做“兼容性微调”。
冻结样本在 `testvectors/`，三端实现必须让它全部通过；历史版本看对应 tag。

---

## 1. 术语

| 名称 | 含义 |
| --- | --- |
| 发送端 | 把明文文件封装成 `.jm` 的一方（当前是 Python SDK） |
| 消费端 | 打开 `.jm`、校验、解密、渲染的一方（Android / iOS） |
| 根密钥 | 32 字节共享密钥，按 `key_id` 版本化，随 App 分发，不进仓库 |
| 测试密钥 | `key_id = 0xFE`，仅用于 `testvectors/`，公开且固定 |

## 2. 字节序

所有多字节无符号整数一律 **大端序（Big-Endian）**。AES-CTR 的 128-bit 计数器同样按大端序递增——这一条在 iOS 上是必踩的坑，见 §6。

## 3. 物理布局

```text
+-------------------------------------------------------------------+
| Fixed Header (28 Bytes, 明文)                                      |
|   [0..3]   magic     : 4B  ASCII "JM01"                            |
|   [4]      version   : 1B  0x01                                    |
|   [5]      alg       : 1B  0x01 (AES-128-CTR + HMAC-SHA256)        |
|   [6]      flags     : 1B  bit0=1 口令模式；其余位必须为 0           |
|   [7]      key_id    : 1B  1..255；口令模式为 0x00                   |
|   [8..23]  nonce     : 16B CSPRNG                                  |
|   [24..27] meta_len  : 4B  uint32，EncryptedMeta 长度               |
+-------------------------------------------------------------------+
| Encrypted Stream (AES-128-CTR 连续密钥流，大端序 128-bit 计数器)     |
|   EncryptedMeta      : meta_len 字节（紧凑 UTF-8 JSON 的密文）       |
|   EncryptedPayload   : size 字节（原始明文的密文）                    |
|   EncryptedPadding   : pad 字节（0..4096 随机填充的密文）             |
+-------------------------------------------------------------------+
| Trailer (32 Bytes)                                                |
|   hmac               : 32B HMAC-SHA256(mac_key, Header || Stream)  |
+-------------------------------------------------------------------+
```

关键点：**Meta、Payload、Padding 共用一条连续密钥流**，不要为每段重新起计数器，否则三端字节永远对不上。

## 4. 密钥派生（RFC 5869 HKDF-SHA256）

三端都只需要平台自带能力：Python `hashlib`/`hmac`，Android `javax.crypto`，iOS `CommonCrypto`。

```text
1. IKM
   无感模式 (flags & 0x01 == 0): IKM = ROOT_KEYS[key_id]              # 32B
   口令模式 (flags & 0x01 == 1): IKM = PBKDF2-HMAC-SHA256(
                                      password = UTF8(pwd),
                                      salt     = nonce,
                                      iter     = 100000,
                                      dklen    = 32)

2. PRK = HMAC-SHA256(key = nonce, msg = IKM)                          # 32B，nonce 当 salt

3. T1  = HMAC-SHA256(key = PRK, msg = "JM01-KEYS" || 0x01)            # 32B
   T2  = HMAC-SHA256(key = PRK, msg = T1 || "JM01-KEYS" || 0x02)      # 32B

4. enc_key = T1[0:16]      # AES-128 密钥
   iv      = T1[16:32]     # CTR 初始计数器（大端序 128-bit）
   mac_key = T2[0:32]      # HMAC-SHA256 密钥
```

`info` 常量固定为 ASCII `"JM01-KEYS"`（9 字节），末尾追加单字节计数器 `0x01` / `0x02`。

## 5. EncryptedMeta

紧凑 JSON（无空格、`separators=(",", ":")`）、UTF-8、长度上限 65536 字节：

```json
{"doc_id":"9f86d081884c7d659a2feaa0c55ad015","name":"深入理解计算机系统.pdf","ext":"pdf","size":15482910,"pad":1732,"ts":1764229000}
```

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `doc_id` | string | 明文 `SHA-256` 前 16 字节的小写 hex（32 字符）；消费端用它做书架去重与进度续接 |
| `name` | string | 原始文件名（含扩展名）。消费端必须取纯文件名，防路径穿越 |
| `ext` | string | 小写扩展名，用于多格式路由 |
| `size` | int64 | 明文精确字节数；解密时按此截断以剥离填充 |
| `pad` | int32 | 尾部随机填充长度，0..4096 |
| `ts` | int64 | 封装时刻，Unix 秒 |

发送端可以追加自定义字段（如 `source`），消费端必须忽略不认识的字段。

## 6. 校验流程与错误语义

消费端**必须**按以下顺序执行，且在校验通过前不得把明文落到最终路径：

1. 文件总长 `< 60` → `JMFormatError`
2. 解析 28 字节头：magic / version / alg / `1 <= meta_len <= 65536` 任一不合法 → `JMFormatError`
3. 派生密钥；`key_id` 在本地密钥表中不存在 → `JMFormatError`
4. 对 `Header || EncryptedStream`（即整文件去掉最后 32 字节）计算 HMAC，与尾部 32 字节**常量时间**比对，失败 → `JMAuthError`
5. 解密 `EncryptedMeta`，解析 JSON（`meta_len` 段只解密、不写入）
6. 断言 `28 + meta_len + size + pad + 32 == 文件总长`，不等 → `JMFormatError`

错误语义是产品文案的依据：

| 错误 | 用户可见含义 |
| --- | --- |
| `JMFormatError` | 这不是 `.jm` 文件 / 协议版本不支持 / 文件结构坏了 |
| `JMPasswordRequiredError` | 需要口令 |
| `JMAuthError` | 下载不完整、已损坏、被改过，或口令错误 |

`JMAuthError` 有意把“截断”和“口令错误”合并成同一个错误：HMAC 是唯一判据，不做额外猜测。

## 7. 发送端行为要求

- **脱敏命名**：默认输出 `doc_YYYYMMDD_XXXXXXXX.jm`（8 位随机 hex），真实文件名只存在于加密 Meta 中。
- **随机化**：每次封装必须新生成 16B nonce，并在 0..4096 内随机取 `pad`。同一份 PDF 两次封装，输出不得有任何字节关联。
- **原子落盘**：先写隐藏 `.tmp`，完成后 `rename` 覆盖；中途失败必须删除临时文件。
- **不压缩**：PDF 本身已压缩，二次压缩只增加耗时与耗电。
- **口令模式**：`key_id` 恒写 `0x00`，`flags` 置 bit0；口令永不出现在 Meta 里。

## 8. 版本与保留值

- `magic = "JM01"` 中 `01` 与 `version = 0x01` 同义；未来协议大改时两者一起变。
- `version ≠ 1` 必须直接拒绝，不做向下兼容猜测。
- `key_id = 0xFE (254)` **保留给跨端测试向量**，生产环境不得把它当正式密钥下发。
- `key_id = 0x00` 仅表示口令模式。
- `flags` 除 bit0 外全部保留，当前必须写 0、读时忽略但不得据此改变解密路径。

## 9. 一致性验收

三端实现必须通过 `testvectors/manifest.json` 里的全部向量：

- `kind = "valid"`：`verify` 返回的 `doc_id/name/size/pad` 与清单一致，`decrypt` 输出的 SHA-256 与清单一致
- `kind = "invalid"`：抛出清单 `error` 指定的错误类型
- 带 `wrong_password` 的向量：用错误口令必须抛 `JMAuthError`

向量不足 12 个时不代表覆盖完整，新增字段或新路径必须补向量。
