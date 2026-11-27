# `.jm` 加密文档分发与移动端阅读系统——技术设计文档（v1.0 定稿）

---

## 一、 项目背景与需求要点记录

### 1.1 核心业务场景
*   **发送方**：在 QQ 群发送 PDF 文档前，通过加密算法封装为特定后缀名 `.jm` 的文件。发送端不需要图形界面，只需封装为 **SDK（优先支持 Python SDK）**，便于集成到批处理脚本、服务端或 QQ 机器人流水线。
*   **接收方**：在移动端（Android / iOS）通过 QQ 直接点击 `.jm` 文件，唤起专属阅读 App 完成校验、解密并阅读。

### 1.2 核心诉求与优先级
本系统的重点**不是高强度密码学对抗**，而是以下工程目标的综合平衡：
1.  **防 QQ 检测风控**：规避 QQ 群文件哈希拦截（秒传/黑名单）、明文文件名敏感词过滤、文件头/内嵌内容（明文文本与 JPEG 图片）深度扫描，以及固定文件体积指纹识别。
2.  **跨端唤起兼容性**：最大程度兼容 Android 各国产定制 ROM 与 iOS 从 QQ 直接打开 `.jm` 文件的场景，并处理 QQ 改名（如 `.jm.1`）、MIME 丢失和系统分区存储限制。
3.  **文件完整性保障**：准确识别 QQ 群下载中断、截断或传输损坏，避免把残缺数据送入 PDF 渲染引擎引发崩溃。
4.  **性能与内存效率**：全链路流式处理，保持极低内存峰值与百毫秒级解密速度，同时在协议层保留超大 PDF 零落盘按需解密（Seek）的扩展能力。
5.  **开发与维护成本**：优先采用主流跨平台技术栈与三端系统原生加密库，减少第三方重型依赖与双端重复造轮子。
6.  **通用性与扩展性**：`.jm` 作为通用加密容器，预留版本号、算法位、口令开关及原始扩展名字段，后续可无缝扩展至 EPUB、图片集、音视频等格式。
7.  **阅读体验与留存**：**不需要阅后清理**；App 需具备本地书架、阅读历史记录、重复导入去重、封面展示以及精准的阅读进度记忆，方便用户日常使用。

---

## 二、 方案评估与最终定稿选型

### 2.1 核心加密方案对比与结论

| 评估维度 | 方案 A：仅头部/局部混淆 | 方案 B：加密 ZIP 改后缀 `.jm` | 方案 C：全量滚动 XOR | 方案 D：自定义头 + 标准流式加密（最终选定） |
| :--- | :--- | :--- | :--- | :--- |
| **防 QQ 风控** | 差（内嵌图片与文本流易被深度扫描） | 中（保留 `PK` 文件头及目录特征） | 良（消除静态特征与固定哈希） | **优**（全量高熵密文 + 随机 Nonce + 随机填充） |
| **完整性保障** | 差（易致渲染崩溃） | 优（自带 CRC32） | 中（需自研校验） | **优**（Encrypt-then-MAC 尾部 HMAC-SHA256） |
| **性能与内存** | 极快 | 中（PDF 二次压缩耗电且无收益） | 极快 | **极快**（现代手机硬件加速 AES，50MB 约 30–80ms） |
| **开发成本** | 极低 | 低 | 低 | **低**（Python/Android/iOS 均内置原生支持） |
| **通用与扩展** | 差（绑定 PDF） | 优 | 良 | **优**（Meta 记录原扩展名，天然支持随机偏移 Seek） |

### 2.2 最终冻结的技术配置总览

| 决策项 | 最终冻结方案 | 选型理由 |
| :--- | :--- | :--- |
| **加密与校验** | `AES-128-CTR` 全量流式加密 + 尾部 32B `HMAC-SHA256` | 全量密文防扫描、硬件加速、天然支持 Seek；HMAC 一次校验同时防截断、损坏、篡改与口令错误 |
| **密钥与权限模式** | **1C 混合模式**：默认内置根密钥无感直开（`key_id` 版本化）+ `Flags` 预留 `PBKDF2-HMAC-SHA256` 单文件口令 | 日常分发零输入摩擦；高敏文档发送方可按需传参启用口令，协议一步到位无需升级 |
| **防 QQ 风控策略** | **3C 组合**：随机 16B Nonce + 外层脱敏命名 + 加密 Meta 存真实文件名/`doc_id` + 尾部 0–4KB 随机填充 | 彻底消除同一份 PDF 的哈希指纹、明文文件名特征与固定字节体积特征 |
| **发送端形态** | **Python SDK**（仅依赖 `cryptography`，64KB 流式 I/O） | 内存恒定极低，便于自动化发包；同步内置校验与解密接口用于跨端测试向量对齐 |
| **移动端技术栈** | **KMP + Compose Multiplatform (CMP)** | 协议解析、加密派生、本地数据库与书架/弹窗 UI 全共享；Android 原生接管 QQ Intent 零桥接 |
| **PDF 渲染组件** | **2A 组合**：Android 嵌入 **PDFium 社区封装**（`AndroidView`）；iOS 嵌入原生 **`PDFKit`**（`UIKitView`） | 避开 Android 厂商 ROM 字体与原生 `PdfRenderer` 缩放模糊问题；iOS 端零额外体积且锐利 |
| **本地存储策略** | **5A + 策略 I**：导入校验通过即流式解密存入私有沙盒，丢弃 `.jm` 副本；禁止导出明文 | 节省 50% 手机空间，二次打开秒开；本地书架通过 `doc_id` 去重并续接历史阅读进度 |
| **持久化与基线** | **Room KMP**（SQLite）；Android 8.0+（API 26）/ iOS 15.0+ | 对齐 CMP 官方稳定基线，避开老旧系统加密与存储权限坑 |
| **首版分发方式** | **6A**：极简加密阅读器，群内直发（Android APK / iOS TestFlight 或自签） | 跳过初期应用商店空壳审核风险，最快跑通业务闭环 |

### 2.3 端到端数据流架构

```text
[发送端 Python SDK]
  原始 PDF ──▶ 计算 SHA-256 前16B (doc_id) ──▶ 生成随机 Nonce 与 0~4KB Padding
           ──▶ HKDF-SHA256 派生 enc_key / iv / mac_key
           ──▶ 64KB 流式 AES-128-CTR 加密 (Meta + Payload + Padding)
           ──▶ 写入尾部 32B HMAC-SHA256 ──▶ 输出脱敏文件 doc_YYYYMMDD_xxxxxxxx.jm
                                                      │
                                                [QQ 群文件传输]
                                                      │
[移动端 KMP App]
  QQ 唤起 / SAF 选择器 ──▶ 读取前28B校验魔数 "JM01" 与 Flags（如为口令模式弹窗输密）
                       ──▶ 单遍 64KB 流式读取：同步算 HMAC + 解密写入私有目录 .tmp
                       ──▶ EOF 常量时间比对 HMAC + 校验 Meta 声明长度
                       ──▶ 校验通过：原子重命名为 files/books/{doc_id}.pdf，释放源流（不留 .jm）
                       ──▶ 异步生成首页封面缩略图 ──▶ 写入/去重更新 Room KMP 书架表
                       ──▶ 打开原生 PDF 阅读器，500ms 防抖保存页码与滚动比例
```

---

## 三、 `.jm` v1 二进制文件协议规范

所有多字节无符号整数统一采用 **大端序（Big-Endian）**。

### 3.1 物理布局

```text
+-------------------------------------------------------------------+
| Fixed Header (28 Bytes, 明文)                                      |
|   [0..3]   magic     : 4B  ASCII "JM01" (0x4A 0x4D 0x30 0x31)     |
|   [4]      version   : 1B  0x01                                   |
|   [5]      alg       : 1B  0x01 (AES-128-CTR + HMAC-SHA256)       |
|   [6]      flags     : 1B  bit0=0 无感模式; bit0=1 口令模式; 其余0   |
|   [7]      key_id    : 1B  内置根密钥版本(1..255); 口令模式填 0x00  |
|   [8..23]  nonce     : 16B CSPRNG 随机值                           |
|   [24..27] meta_len  : 4B  uint32, EncryptedMeta 长度(1..65536)   |
+-------------------------------------------------------------------+
| Encrypted Stream (AES-128-CTR 连续密钥流，大端序 128-bit 计数器)     |
|   EncryptedMeta      : meta_len 字节 (无空格紧凑 UTF-8 JSON 密文)   |
|   EncryptedPayload   : size 字节 (原始文件明文对应的密文)            |
|   EncryptedPadding   : pad 字节 (0..4096 字节随机填充对应的密文)     |
+-------------------------------------------------------------------+
| Trailer (32 Bytes)                                                |
|   hmac               : 32B HMAC-SHA256(mac_key, Header || Stream) |
+-------------------------------------------------------------------+
```

### 3.2 密钥派生规范（RFC 5869 HKDF-SHA256）

为确保 Python、Android（`javax.crypto`）与 iOS（`CommonCrypto`）无需引入第三方密码学库即可逐字节对齐，严格执行以下派生流程：

1.  **计算初始密钥材料 `IKM`（32 字节）**：
    *   无感模式（`flags & 0x01 == 0`）：`IKM = ROOT_KEYS[key_id]`（32 字节内置根密钥）。
    *   口令模式（`flags & 0x01 == 1`）：`IKM = PBKDF2-HMAC-SHA256(password=UTF8(pwd), salt=nonce, iterations=100000, dklen=32)`。
2.  **HKDF-Extract**：
    *   `PRK = HMAC-SHA256(key=nonce, msg=IKM)`（32 字节）。
3.  **HKDF-Expand（固定上下文 `info = b"JM01-KEYS"`）**：
    *   `T1 = HMAC-SHA256(key=PRK, msg=b"JM01-KEYS" + 0x01)`（32 字节）
    *   `T2 = HMAC-SHA256(key=PRK, msg=T1 + b"JM01-KEYS" + 0x02)`（32 字节）
4.  **切分子密钥**：
    *   `enc_key = T1[0..15]`（16 字节，AES-128 加密密钥）
    *   `iv = T1[16..31]`（16 字节，AES-128-CTR 初始大端序计数器）
    *   `mac_key = T2[0..31]`（32 字节，HMAC-SHA256 认证密钥）

### 3.3 `Meta` JSON 元数据结构

```json
{
  "doc_id": "9f86d081884c7d659a2feaa0c55ad015",
  "name": "深入理解计算机系统.pdf",
  "ext": "pdf",
  "size": 15482910,
  "pad": 1732,
  "ts": 1764229000
}
```

| 字段 | 类型 | 说明 |
| :--- | :--- | :--- |
| `doc_id` | String | 原始明文 `SHA-256` 前 16 字节小写十六进制（32 字符），用于书架去重与阅读进度续接 |
| `name` | String | 原始文件名（含扩展名），消费端需取纯文件名防路径穿越 |
| `ext` | String | 小写原始文件扩展名（如 `pdf`），用于后续多格式扩展路由 |
| `size` | Int64 | 原始明文精确字节长度，解密时按此截断以剥离随机填充 |
| `pad` | Int32 | 尾部随机填充字节数（0 至 4096） |
| `ts` | Int64 | 封装时的 Unix 秒级时间戳 |

### 3.4 完整性与边界校验规则
*   **最小长度拦截**：文件总长小于 60 字节直接报错。
*   **Encrypt-then-MAC**：必须对完整 `Header || EncryptedStream` 计算 HMAC 并以常量时间比对尾部 32 字节；未通过前严禁将临时解密文件转正。
*   **总长一致性断言**：解密 Meta 后必须满足 `28 + meta_len + size + pad + 32 == 文件总字节数`。

---

## 四、 发送端 Python SDK 设计与参考实现

### 4.1 设计要点
*   **依赖极简**：仅需 `pip install cryptography`，其余全部基于 Python 标准库。
*   **原子落盘**：加密写入隐藏 `.tmp` 文件，完毕后通过 `os.replace` 原子切换，防止中途中断残留损坏文件。
*   **异常体系**：区分 `JMFormatError`（格式/魔数/长度非法）、`JMPasswordRequiredError`（缺口令）、`JMAuthError`（HMAC 失败：下载不完整、损坏或口令错误）。

### 4.2 完整参考代码（`jm_sdk.py`）

```python
"""
JM v1 加密容器 Python SDK
协议版本: JM01 (AES-128-CTR + HMAC-SHA256 + HKDF-SHA256)
依赖: pip install cryptography
"""

from __future__ import annotations

import dataclasses
import datetime
import hashlib
import hmac
import json
import os
import secrets
import struct
import time
from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, Tuple, Union

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC = b"JM01"
VERSION = 0x01
ALG_AES128_CTR_HMAC_SHA256 = 0x01
FLAG_PASSWORD = 0x01

HEADER_STRUCT = struct.Struct(">4sBBBB16sI")
HEADER_SIZE = HEADER_STRUCT.size  # 28 bytes
MAC_SIZE = 32
MIN_FILE_SIZE = HEADER_SIZE + MAC_SIZE  # 60 bytes

HKDF_INFO = b"JM01-KEYS"
PBKDF2_ITERATIONS = 100_000
MAX_META_LEN = 64 * 1024
MAX_PAD_LEN = 4096
DEFAULT_CHUNK_SIZE = 64 * 1024


class JMError(Exception):
    """JM SDK 基础异常。"""


class JMFormatError(JMError):
    """文件魔数、版本、结构或长度不合法。"""


class JMPasswordRequiredError(JMError):
    """文件为口令加密模式，但未提供口令。"""


class JMAuthError(JMError):
    """HMAC 校验失败（文件下载不完整、已损坏、密钥版本错误或口令错误）。"""


@dataclasses.dataclass(frozen=True)
class HeaderInfo:
    version: int
    alg: int
    flags: int
    key_id: int
    nonce: bytes
    meta_len: int

    @property
    def is_password_protected(self) -> bool:
        return bool(self.flags & FLAG_PASSWORD)


@dataclasses.dataclass(frozen=True)
class EncryptResult:
    output_path: Path
    doc_id: str
    original_name: str
    original_size: int
    encrypted_size: int
    pad_len: int
    password_protected: bool


@dataclasses.dataclass(frozen=True)
class DecryptResult:
    output_path: Path
    meta: Dict[str, Any]


def _derive_keys(
    nonce: bytes,
    flags: int,
    key_id: int,
    root_keys: Dict[int, bytes],
    password: Optional[str],
) -> Tuple[bytes, bytes, bytes]:
    """根据协议规范派生 (enc_key[16], iv[16], mac_key[32])。"""
    if flags & FLAG_PASSWORD:
        if not password:
            raise JMPasswordRequiredError("此 .jm 文件需要口令才能解密")
        ikm = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            nonce,
            PBKDF2_ITERATIONS,
            dklen=32,
        )
    else:
        ikm = root_keys.get(key_id)
        if ikm is None:
            raise JMFormatError(f"未知的 key_id: {key_id}")
        if len(ikm) != 32:
            raise ValueError("根密钥长度必须为 32 字节")

    prk = hmac.new(nonce, ikm, hashlib.sha256).digest()
    t1 = hmac.new(prk, HKDF_INFO + b"\x01", hashlib.sha256).digest()
    t2 = hmac.new(prk, t1 + HKDF_INFO + b"\x02", hashlib.sha256).digest()

    return t1[:16], t1[16:32], t2[:32]


def _compute_doc_id_and_size(stream: BinaryIO, chunk_size: int = DEFAULT_CHUNK_SIZE) -> Tuple[str, int]:
    """流式计算原文件 SHA-256 前 16 字节（32 位 hex）与总字节数。"""
    sha = hashlib.sha256()
    total = 0
    while True:
        chunk = stream.read(chunk_size)
        if not chunk:
            break
        sha.update(chunk)
        total += len(chunk)
    return sha.digest()[:16].hex(), total


def _generate_masked_filename(prefix: str = "doc") -> str:
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    rand_hex = secrets.token_hex(4)
    return f"{prefix}_{date_str}_{rand_hex}.jm"


class JMCrypto:
    """JM v1 加解密客户端（线程安全，可复用实例）。"""

    def __init__(self, root_keys: Dict[int, bytes], default_key_id: int = 1) -> None:
        if default_key_id not in root_keys:
            raise ValueError(f"default_key_id={default_key_id} 不在 root_keys 中")
        for kid, key in root_keys.items():
            if not (1 <= kid <= 255):
                raise ValueError("key_id 取值范围必须为 1..255")
            if len(key) != 32:
                raise ValueError(f"key_id={kid} 对应的根密钥必须为 32 字节")
        self._root_keys = dict(root_keys)
        self._default_key_id = default_key_id

    @staticmethod
    def inspect_header(jm_path: Union[str, Path]) -> HeaderInfo:
        """读取文件前 28 字节，无需解密即可判断合法性与是否需要口令。"""
        with open(jm_path, "rb") as f:
            raw = f.read(HEADER_SIZE)
        if len(raw) < HEADER_SIZE:
            raise JMFormatError("文件长度不足 28 字节")
        magic, version, alg, flags, key_id, nonce, meta_len = HEADER_STRUCT.unpack(raw)
        if magic != MAGIC:
            raise JMFormatError(f"无效的文件头魔数: {magic!r}")
        if version != VERSION:
            raise JMFormatError(f"不支持的协议版本: {version}")
        if alg != ALG_AES128_CTR_HMAC_SHA256:
            raise JMFormatError(f"不支持的加密算法标识: {alg}")
        if meta_len == 0 or meta_len > MAX_META_LEN:
            raise JMFormatError(f"非法的元数据长度: {meta_len}")
        return HeaderInfo(version, alg, flags, key_id, nonce, meta_len)

    def encrypt_file(
        self,
        src_path: Union[str, Path],
        dst_path: Optional[Union[str, Path]] = None,
        *,
        mask_name: bool = True,
        alias_prefix: str = "doc",
        password: Optional[str] = None,
        key_id: Optional[int] = None,
        pad_range: Tuple[int, int] = (0, MAX_PAD_LEN),
        extra_meta: Optional[Dict[str, Any]] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> EncryptResult:
        """流式加密本地文件为 .jm 格式。"""
        src = Path(src_path)
        if not src.is_file():
            raise FileNotFoundError(f"源文件不存在: {src}")

        pad_min, pad_max = pad_range
        if not (0 <= pad_min <= pad_max <= MAX_PAD_LEN):
            raise ValueError(f"pad_range 必须满足 0 <= min <= max <= {MAX_PAD_LEN}")

        if dst_path is None:
            out_name = _generate_masked_filename(alias_prefix) if mask_name else f"{src.stem}.jm"
            dst = src.parent / out_name
        else:
            dst = Path(dst_path)
            if dst.is_dir():
                out_name = _generate_masked_filename(alias_prefix) if mask_name else f"{src.stem}.jm"
                dst = dst / out_name

        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp_dst = dst.with_name(f".{dst.name}.{secrets.token_hex(4)}.tmp")

        try:
            with open(src, "rb") as fin:
                doc_id, file_size = _compute_doc_id_and_size(fin, chunk_size)
                fin.seek(0)

                pad_len = secrets.randbelow(pad_max - pad_min + 1) + pad_min
                ext = src.suffix.lstrip(".").lower()
                meta: Dict[str, Any] = {
                    "doc_id": doc_id,
                    "name": src.name,
                    "ext": ext,
                    "size": file_size,
                    "pad": pad_len,
                    "ts": int(time.time()),
                }
                if extra_meta:
                    meta.update(extra_meta)

                meta_bytes = json.dumps(meta, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                if len(meta_bytes) > MAX_META_LEN:
                    raise ValueError(f"Meta JSON 超过上限 {MAX_META_LEN} 字节")

                nonce = os.urandom(16)
                if password:
                    flags = FLAG_PASSWORD
                    eff_key_id = 0
                else:
                    flags = 0
                    eff_key_id = self._default_key_id if key_id is None else key_id

                enc_key, iv, mac_key = _derive_keys(nonce, flags, eff_key_id, self._root_keys, password)
                header = HEADER_STRUCT.pack(
                    MAGIC, VERSION, ALG_AES128_CTR_HMAC_SHA256, flags, eff_key_id, nonce, len(meta_bytes)
                )

                encryptor = Cipher(algorithms.AES(enc_key), modes.CTR(iv)).encryptor()
                mac = hmac.new(mac_key, digestmod=hashlib.sha256)

                with open(tmp_dst, "wb") as fout:
                    fout.write(header)
                    mac.update(header)

                    enc_meta = encryptor.update(meta_bytes)
                    fout.write(enc_meta)
                    mac.update(enc_meta)

                    while True:
                        chunk = fin.read(chunk_size)
                        if not chunk:
                            break
                        enc_chunk = encryptor.update(chunk)
                        fout.write(enc_chunk)
                        mac.update(enc_chunk)

                    if pad_len > 0:
                        enc_pad = encryptor.update(os.urandom(pad_len))
                        fout.write(enc_pad)
                        mac.update(enc_pad)

                    final_bytes = encryptor.finalize()
                    if final_bytes:
                        fout.write(final_bytes)
                        mac.update(final_bytes)

                    fout.write(mac.digest())

            os.replace(tmp_dst, dst)
            return EncryptResult(
                output_path=dst,
                doc_id=doc_id,
                original_name=src.name,
                original_size=file_size,
                encrypted_size=dst.stat().st_size,
                pad_len=pad_len,
                password_protected=bool(password),
            )
        except Exception:
            if tmp_dst.exists():
                tmp_dst.unlink(missing_ok=True)
            raise

    def verify_file(
        self,
        jm_path: Union[str, Path],
        *,
        password: Optional[str] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> Dict[str, Any]:
        """校验 .jm 完整性和认证标签，通过后返回解密后的 Meta 字典。"""
        jm = Path(jm_path)
        total_size = jm.stat().st_size
        if total_size < MIN_FILE_SIZE:
            raise JMFormatError("文件不完整（小于最小合法长度）")

        header_info = self.inspect_header(jm)
        enc_key, iv, mac_key = _derive_keys(
            header_info.nonce, header_info.flags, header_info.key_id, self._root_keys, password
        )

        payload_end = total_size - MAC_SIZE
        mac = hmac.new(mac_key, digestmod=hashlib.sha256)
        with open(jm, "rb") as fin:
            remaining = payload_end
            while remaining > 0:
                chunk = fin.read(min(chunk_size, remaining))
                if not chunk:
                    raise JMAuthError("读取文件意外提前结束")
                mac.update(chunk)
                remaining -= len(chunk)
            expected_mac = fin.read(MAC_SIZE)

            if len(expected_mac) != MAC_SIZE or not hmac.compare_digest(mac.digest(), expected_mac):
                raise JMAuthError("HMAC 校验失败：文件下载不完整、已损坏或口令错误")

            fin.seek(HEADER_SIZE)
            enc_meta = fin.read(header_info.meta_len)

        decryptor = Cipher(algorithms.AES(enc_key), modes.CTR(iv)).decryptor()
        meta_bytes = decryptor.update(enc_meta) + decryptor.finalize()
        meta = json.loads(meta_bytes.decode("utf-8"))

        expected_total = HEADER_SIZE + header_info.meta_len + int(meta["size"]) + int(meta["pad"]) + MAC_SIZE
        if expected_total != total_size:
            raise JMFormatError(f"元数据声明长度({expected_total})与实际文件大小({total_size})不符")
        return meta

    def decrypt_file(
        self,
        jm_path: Union[str, Path],
        dst_path: Union[str, Path],
        *,
        password: Optional[str] = None,
        use_original_name: bool = False,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> DecryptResult:
        """先校验完整性，再流式解密为明文文件（自动剔除随机填充）。"""
        jm = Path(jm_path)
        meta = self.verify_file(jm, password=password, chunk_size=chunk_size)
        header_info = self.inspect_header(jm)
        enc_key, iv, _ = _derive_keys(
            header_info.nonce, header_info.flags, header_info.key_id, self._root_keys, password
        )

        dst = Path(dst_path)
        if dst.is_dir() or use_original_name:
            target_dir = dst if dst.is_dir() else dst.parent
            safe_name = Path(meta["name"]).name
            dst = target_dir / safe_name

        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp_dst = dst.with_name(f".{dst.name}.{secrets.token_hex(4)}.tmp")

        try:
            decryptor = Cipher(algorithms.AES(enc_key), modes.CTR(iv)).decryptor()
            with open(jm, "rb") as fin, open(tmp_dst, "wb") as fout:
                fin.seek(HEADER_SIZE)
                _ = decryptor.update(fin.read(header_info.meta_len))

                remaining = int(meta["size"])
                while remaining > 0:
                    chunk = fin.read(min(chunk_size, remaining))
                    if not chunk:
                        raise JMFormatError("主体数据读取中断")
                    fout.write(decryptor.update(chunk))
                    remaining -= len(chunk)

                tail = decryptor.finalize()
                if tail:
                    fout.write(tail)

            os.replace(tmp_dst, dst)
            return DecryptResult(output_path=dst, meta=meta)
        except Exception:
            if tmp_dst.exists():
                tmp_dst.unlink(missing_ok=True)
            raise
```

---

## 五、 移动端（KMP + CMP）架构与关键实现设计

### 5.1 工程模块划分

```text
jm-reader/
├── composeApp/
│   ├── src/commonMain/kotlin/
│   │   ├── crypto/          # .jm 协议头解析、HKDF 实现、expect 流式解密引擎
│   │   ├── data/            # Room KMP (BookEntity / BookDao)、私有沙盒存储管理
│   │   ├── domain/          # 导入用例（去重、验密、封面生成触发、状态持久化）
│   │   └── ui/
│   │       ├── bookshelf/   # CMP 书架页（最近阅读排序、封面、进度条、口令弹窗、导入进度）
│   │       └── reader/      # CMP 阅读页工具栏 + expect PdfReaderCanvas
│   ├── src/androidMain/kotlin/
│   │   ├── crypto/          # actual: javax.crypto (AES/CTR/NoPadding, HmacSHA256, PBKDF2)
│   │   ├── ingest/          # QQ Intent 接管、ContentResolver 单遍流式读取、SAF 兜底
│   │   └── ui/reader/       # actual: AndroidView(PDFium) + 首帧封面缩略图生成
│   └── src/iosMain/kotlin/
│       ├── crypto/          # actual: CommonCrypto (CCCryptor CTR_BE, CCHmac, CCKeyDerivationPBKDF)
│       ├── ingest/          # SecurityScoped URL 读取与流式导入
│       └── ui/reader/       # actual: UIKitView(PDFKit) + 首帧封面缩略图生成
└── iosApp/                  # Swift 入口壳工程（Info.plist 自定义 UTI + onOpenURL 桥接）
```

### 5.2 QQ 唤起与系统兼容性专项设计

| 平台 | 典型兼容性坑点 | 工程落地策略 |
| :--- | :--- | :--- |
| **Android** | 1. QQ 分享未知后缀常发 `application/octet-stream`，且 `content://` URI 不含 `.jm`；<br>2. QQ 偶发追加 `.1` 变为 `.jm.1`；<br>3. Android 11+ 分区存储无法取物理路径；<br>4. 部分国产 ROM 拦截三方文件关联 | 1. `AndroidManifest.xml` 同时注册 `VIEW`/`SEND`、`.jm` 路径匹配及 `application/octet-stream`；<br>2. 收到 Intent 后**统一通过 `ContentResolver.openInputStream(uri)` 读前 4 字节校验 `JM01` 魔数**（自动兼容 `.jm.1`，非 `.jm` 文件友好提示退出）；<br>3. App 首页常驻“导入本地 `.jm`”按钮（调用系统 SAF 选择器）作为国产 ROM 兜底入口 |
| **iOS** | 未知自定义后缀无法出现在 QQ“用其他应用打开”列表 | 在 `Info.plist` 注册 `UTExportedTypeDeclarations`（自定义 UTI 继承 `public.data`，绑定扩展名 `jm`）与 `CFBundleDocumentTypes`；通过 `onOpenURL` 接管并在 Security-Scoped 权限内完成流式读取 |

### 5.3 跨端加解密与单遍流式导入避坑要点
*   **iOS `CommonCrypto` 的 CTR 字节序坑（必防）**：Python `cryptography` 与 Android `javax.crypto` 的 `AES/CTR/NoPadding` 均按大端序递增 128-bit 计数器。iOS 调用 `CCCryptorCreateWithMode` 时**必须显式传入 `kCCModeOptionCTR_BE`**，否则密文与另外两端完全不一致。
*   **Android 单遍流式导入**：`ContentResolver` 返回的流通常不支持 `seek`，导入时采用 **64KB 缓冲区 + 32 字节滑动尾部窗口**：单遍读取同时更新 `HMAC` 与 `Cipher`，明文直接流式写入 `filesDir/tmp/{uuid}.tmp`；读至 EOF 且常量时间比对尾部 32B `HMAC` 与长度均合法后，原子重命名为 `filesDir/books/{doc_id}.pdf` 并释放输入流（遵循策略 I 不留 `.jm` 副本）；失败立即删除 `.tmp` 并给出明确提示（如“文件下载不完整，请在 QQ 重新下载”或“口令错误”）。
*   **口令文档策略**：口令加密文件在**首次导入时验证一次口令**，解密进入私有沙盒后存入书架即可免密续读。

### 5.4 私有沙盒与 Room KMP 书架表设计

私有目录规划（系统文件管理器与相册不可见，App 不提供明文导出/分享功能）：
*   文档目录：`files/books/{doc_id}.pdf`
*   封面目录：`files/covers/{doc_id}.webp`（导入成功后异步渲染 PDF 第 1 页生成缩略图）

数据表 `books` 结构：

| 字段名 | 类型 | 约束与说明 |
| :--- | :--- | :--- |
| `docId` | `String` | **主键**，源自加密 Meta 的 `doc_id` |
| `title` | `String` | 展示标题（初始取加密 Meta 原名，支持用户自定义重命名） |
| `ext` | `String` | 原始扩展名（如 `pdf`），用于路由阅读组件 |
| `localPath` | `String` | 沙盒内相对路径 |
| `coverPath` | `String?` | 首页缩略图相对路径 |
| `fileSize` | `Long` | 原始明文大小（字节） |
| `lastPage` | `Int` | 上次阅读页码（从 0 开始） |
| `totalPages` | `Int` | 文档总页数 |
| `scrollRatio` | `Float` | 纵向滚动百分比（确保横竖屏切换不跑偏） |
| `importedAt` | `Long` | 首次导入时间戳（毫秒） |
| `lastReadAt` | `Long` | 最近阅读时间戳（书架默认按此倒序） |

*   **去重与进度保留**：重复导入相同 `docId` 时，命中已有记录则保留原 `lastPage`、`totalPages` 与 `scrollRatio`，仅刷新 `lastReadAt` 与文件有效性检查，避免群内重发同一文件导致阅读进度丢失。

### 5.5 统一阅读器桥接与进度防抖

```kotlin
@Composable
expect fun PdfReaderCanvas(
    filePath: String,
    initialPage: Int,
    initialScrollRatio: Float,
    onDocumentLoaded: (totalPages: Int) -> Unit,
    onProgressChanged: (page: Int, scrollRatio: Float) -> Unit,
    modifier: Modifier = Modifier,
)
```

*   进度保存采用 **500ms 防抖（debounce）** 异步写入 Room KMP，避免高频滑动引发磁盘 I/O 卡顿；在页面退出（`onDispose`）或应用切后台时补写一次最终进度。

---

## 六、 实施路线与远期演进预留

### 6.1 MVP 研发排期建议
1.  **阶段一：协议冻结与测试向量生成** — 落地 Python SDK，生成覆盖无感模式、口令模式、边界 Padding、截断与篡改的跨端标准测试样本集（`.jm` + 原始明文）。
2.  **阶段二：KMP 共享加密核心互测** — 完成 `commonMain` 协议解析与 Android/iOS `expect/actual` 流式解密引擎，在双端单测中 100% 通过阶段一样本（重点验证 iOS `CTR_BE` 与 PBKDF2 对齐）。
3.  **阶段三：QQ 唤起真机兼容性攻关** — 优先在主流国产 Android 机型（小米/OPPO/vivo/华为）与 iOS 真机上打通 QQ 群文件点击唤起、`.jm.1` 识别、单遍导入与 SAF 兜底。
4.  **阶段四：书架与阅读闭环交付** — 集成 Room KMP、封面渲染、Android PDFium / iOS `PDFKit` 桥接与阅读进度防抖保存，产出首版群内灰度包。

### 6.2 远期演进预留（无需改动 `.jm` v1 协议）
*   **超大 PDF（150MB 以上）零落盘秒开**：利用 `AES-128-CTR` 支持任意字节偏移独立计算密钥流的特性，后续可在 App 端为 PDFium / MuPDF 接入自定义 `RandomAccessDataSource` 实现按页按需解密，历史上已发出的 `.jm` 文件无需任何改动即可无缝兼容。
*   **多格式通用扩展**：依托 `Meta.ext` 字段，后续在移动端按扩展名路由对应查看器，即可平滑扩展支持加密图片集、EPUB 电子书或音视频。
*   **应用商店上架合规**：未来若需从群内直发升级至上架 App Store 与国内应用市场，产品定位可包装为“个人隐私加密文档阅读器”，并在 App 内补齐**本地文件加密生成 `.jm` 功能**与**内置示例文档**，避免被审核判定为依赖外部未知文件的空壳应用。