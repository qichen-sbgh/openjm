# 发送端 SDK 设计

| 项 | 值 |
| --- | --- |
| 状态 | 已实现（v0.1.0，tag `sdk-v0.1.0`） |
| 最后更新 | 2026-11-28 |
| 代码 | [`openjm-sdk`](https://github.com/qichen-sbgh/openjm-sdk) |
| 关联协议 | [`protocol.md`](protocol.md) |

本文件写设计取舍与接口约定；**实现细节以代码为准**，协议字节以规范为准。

## 1. 形态

一个 Python 包 + 一个 CLI，没有服务、没有 GUI：

```python
from openjm import JMCrypto, load_root_keys
crypto = JMCrypto(load_root_keys("keys.json"))
result = crypto.encrypt_file("报告.pdf")     # → doc_20261127_a1b2c3d4.jm
```

```bash
python -m openjm encrypt 报告.pdf
python -m openjm inspect doc_20261127_a1b2c3d4.jm
python -m openjm verify  doc_20261127_a1b2c3d4.jm
python -m openjm decrypt doc_20261127_a1b2c3d4.jm -o ./out --original-name
```

CLI 是给 QQ 机器人流水线用的“能直接塞进 shell 的入口”，库 API 是给需要拿到 Meta 的脚本用的。两者共用同一套实现，不做第二份逻辑。

## 2. 接口约定

| 方法 | 作用 | 关键约定 |
| --- | --- | --- |
| `inspect_header(path)` | 只读 28B 头 | 不解密、不碰密文，用于判断“要不要口令” |
| `encrypt_file(...)` | 封装 | 返回 `doc_id` / 原始大小 / 填充长度 / 是否口令；原子落盘 |
| `verify_file(...)` | 只校验 | 返回解密后的 Meta，不产生明文文件；用于预检 |
| `decrypt_file(...)` | 校验 + 解密 | 先 `verify` 再解密，按 `size` 截断剥离填充 |

`default_key_id` **只影响加密**：只做校验/解密时，可以装一套密钥而默认 id 不在其中（CLI 的 `verify` 依赖这一点）。

## 3. 错误语义

| 异常 | 触发 | 调用方该做什么 |
| --- | --- | --- |
| `JMFormatError` | 魔数/版本/长度不合法、`key_id` 未知 | 让发送方重新封装 |
| `JMPasswordRequiredError` | 口令文件未给口令 | 弹口令输入 |
| `JMAuthError` | HMAC 不过（截断/损坏/篡改/口令错） | 提示重新下载或重试口令 |

三类错误是**唯一**的判断依据，不要在调用方用字符串匹配或 `stat` 大小去猜。

## 4. 关键实现约束

1. **64KB 分块流式**：内存占用与文件大小无关；`encrypt_file` 需要两遍读源文件（先算 `doc_id` 再加密），本地文件可接受。
2. **原子落盘**：写隐藏 `.tmp`，完成后 `os.replace`；`except` 分支必须删临时文件。
3. **不压缩**：PDF 已压缩，二次压缩只增耗电。
4. **随机化不可省**：nonce 与填充长度都必须用 `secrets` / `os.urandom`，不要用 `random`。
5. **key_id 校验在加密时做**：构造期不校验默认 id（见 §2），避免“只想验一下”却被拦。

## 5. 测试

- 单测：往返、同源不同密文、口令模式、截断、篡改、坏魔数、未知 key_id、分块边界、原子落盘、CLI；
- 跨端一致性：回放总仓 `testvectors/`，找不到向量时自动 skip；
- 当前状态：30 个用例全绿，CI 覆盖 Python 3.9 / 3.11 / 3.12。

## 6. 不做的事

- 不做密钥分发（只认 `OPENJM_KEY_FILE` 或显式传入）；
- 不做上传、不做 PDF 解析、不做压缩；
- 不实现阅读侧（那在 `openjm-mobile`），本仓的解密只用于校验与测试。

## 7. 使用方：AstrBot 插件

[`astrbot_plugin_openjm`](https://github.com/qichen-sbgh/astrbot_plugin_openjm) 是第一个把本 SDK 用在自动化流水线里的仓：
群里有人发 JM 号 → 下载 → 合成 PDF → 调 `JMCrypto.encrypt_file(..., mask_name=True)` → 只把 `.jm` 发回群。

它的集成方式刻意做得很薄：

| 项 | 做法 | 原因 |
| --- | --- | --- |
| SDK 引入 | `requirements.txt` 里 `openjm @ git+...@sdk-v0.1.0` | 依赖而不是复制代码：协议实现只能有一份，复制必漂移 |
| 版本 | pin 到 tag `sdk-v0.1.0` | `@main` 是浮动的，上游改接口会把插件带崩 |
| 密钥 | 插件内置了与 App 同一把（`key_id=1`） | 对称加密两端必须一致；而这把钥匙本就随公开 APK 一起公开，见下 |

**关于内置密钥的取舍**：`.jm` 是对称加密，插件加密、App 解密必须同一把根密钥，而 App 里的那把在打包时焊死。
它的"秘密性"本来就有限——正式包 `openjm-0.1.0.apk` 是公开发布物，钥匙就在 `assets/keys.json` 里，`unzip` 一行命令即可取出。
项目在 [`decisions.md`](decisions.md) 里写明安全边界是「躲群文件扫描与哈希指纹」，不对抗逆向，所以把同一把钥匙放进插件源码，
换来的是"装上就能用"；`decisions.md` 待定项里"密钥注入方式"一栏由此补上了实际做法。
要提升强度只能换钥匙并重新打包 App，代价是老文件与旧版 App 的兼容。
