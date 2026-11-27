#!/usr/bin/env python3
"""生成 openjm 跨端测试向量。

用法（在 openjm 仓库根目录）::

    pip install -e ../openjm-sdk
    python testvectors/make_vectors.py

产物全部提交进仓库：`plain/` 是原始明文，`valid/` 是应当解密成功的向量，
`invalid/` 是必须被拒绝的向量，`manifest.json` 是给三端单测读的清单。

注意：nonce 与填充都是随机的，所以**每次重跑都会改写 .jm 与 manifest**。
只有在协议变更或补向量时才重跑，重跑后三端都要重新对齐一次。
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from openjm import HEADER_SIZE, JMCrypto

ROOT = Path(__file__).resolve().parent
PLAIN = ROOT / "plain"
VALID = ROOT / "valid"
INVALID = ROOT / "invalid"

TEST_KEY_ID = 254
TEST_KEY = hashlib.sha256(b"openjm-test-vector-key-v1").digest()
TEST_PASSWORD = "correct horse battery staple"


def build_pdf(title: str, filler_bytes: int = 0) -> bytes:
    """手搓一份结构合法、能被真实阅读器打开的单页 PDF。

    filler 以 PDF 注释行形式塞在 xref 之前，用来把体积撑到跨 64KB 分块。
    """
    content = f"BT /F1 24 Tf 72 760 Td ({title}) Tj ET\n".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: List[int] = []
    for index, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + body + b"\nendobj\n"

    if filler_bytes:
        out += b"% " + (b"openjm filler " * (filler_bytes // 14 + 1))[:filler_bytes] + b"\n"

    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode()
    return bytes(out)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expect_of(crypto: JMCrypto, jm: Path, password: str | None = None) -> Dict[str, Any]:
    meta = crypto.verify_file(jm, password=password)
    return {
        "doc_id": meta["doc_id"],
        "name": meta["name"],
        "ext": meta["ext"],
        "size": meta["size"],
        "pad": meta["pad"],
        "sha256": sha256_file(PLAIN / meta["name"]),
    }


def main() -> int:
    for directory in (PLAIN, VALID, INVALID):
        directory.mkdir(parents=True, exist_ok=True)
        for stale in directory.glob("*"):
            if stale.is_file():
                stale.unlink()

    hello = PLAIN / "hello-openjm.pdf"
    hello.write_bytes(build_pdf("openjm test vector v1"))
    large = PLAIN / "large-192kb.pdf"
    large.write_bytes(build_pdf("openjm large streaming vector", filler_bytes=190_000))

    (ROOT / "keys.test.json").write_text(
        json.dumps({str(TEST_KEY_ID): TEST_KEY.hex()}, indent=2) + "\n", encoding="utf-8"
    )
    crypto = JMCrypto({TEST_KEY_ID: TEST_KEY}, default_key_id=TEST_KEY_ID)

    vectors: List[Dict[str, Any]] = []

    def add_valid(
        vector_id: str,
        jm: Path,
        source: Path,
        note: str,
        password: str | None = None,
        wrong_password: str | None = None,
        **extra: Any,
    ) -> None:
        relative = jm.relative_to(ROOT).as_posix()
        entry: Dict[str, Any] = {
            "id": vector_id,
            "kind": "valid",
            "file": relative,
            "source": source.relative_to(ROOT).as_posix(),
            "note": note,
            "expect": expect_of(crypto, jm, password),
        }
        if password:
            entry["password"] = password
        if wrong_password:
            entry["wrong_password"] = wrong_password
        entry.update(extra)
        vectors.append(entry)

    # v01 无感模式、零填充：最小可用样本
    v01 = VALID / "v01-plain-no-pad.jm"
    crypto.encrypt_file(hello, v01, pad_range=(0, 0))
    add_valid("v01-plain-no-pad", v01, hello, "无感模式，pad=0，最小合法样本")

    # v02 同一份 PDF 再封装一次：doc_id 相同但密文完全不同，验证抗指纹
    v02 = VALID / "v02-same-source-new-nonce.jm"
    crypto.encrypt_file(hello, v02, pad_range=(0, 0))
    add_valid("v02-same-source-new-nonce", v02, hello, "与 v01 同一明文，nonce 不同，密文必须不同")

    # v03 口令模式（PBKDF2 路径）
    v03 = VALID / "v03-password.jm"
    crypto.encrypt_file(hello, v03, password=TEST_PASSWORD, pad_range=(0, 0))
    add_valid(
        "v03-password",
        v03,
        hello,
        "口令模式，key_id 恒为 0，走 PBKDF2-HMAC-SHA256 10 万次",
        password=TEST_PASSWORD,
        wrong_password="wrong horse battery staple",
    )

    # v04 满额填充：pad=4096 边界
    v04 = VALID / "v04-pad-max.jm"
    crypto.encrypt_file(hello, v04, pad_range=(4096, 4096))
    add_valid("v04-pad-max", v04, hello, "pad=4096 上限，验证尾部填充剥离")

    # v05 跨 64KB 分块的大文件
    v05 = VALID / "v05-large-multichunk.jm"
    crypto.encrypt_file(large, v05, pad_range=(1234, 1234))
    add_valid("v05-large-multichunk", v05, large, "约 192KB，跨多个 64KB 分块，pad=1234")

    # ---------------------------------------------------------------- 反例
    def add_invalid(vector_id: str, jm: Path, error: str, note: str, password: str | None = None) -> None:
        entry: Dict[str, Any] = {
            "id": vector_id,
            "kind": "invalid",
            "file": jm.relative_to(ROOT).as_posix(),
            "error": error,
            "note": note,
        }
        if password:
            entry["password"] = password
        vectors.append(entry)

    original = v01.read_bytes()

    v90 = INVALID / "v90-truncated.jm"
    v90.write_bytes(original[:-1])
    add_invalid("v90-truncated", v90, "JMAuthError", "砍掉尾部 1 字节，模拟 QQ 下载中断")

    v91 = INVALID / "v91-tampered-payload.jm"
    tampered = bytearray(original)
    tampered[HEADER_SIZE + 64] ^= 0x01
    v91.write_bytes(bytes(tampered))
    add_invalid("v91-tampered-payload", v91, "JMAuthError", "载荷区翻 1 bit")

    v92 = INVALID / "v92-bad-magic.jm"
    bad_magic = bytearray(original)
    bad_magic[0:4] = b"JK01"
    v92.write_bytes(bytes(bad_magic))
    add_invalid("v92-bad-magic", v92, "JMFormatError", "魔数改成 JK01")

    v93 = INVALID / "v93-too-short.jm"
    v93.write_bytes(b"JM01" + b"\x00" * 36)
    add_invalid("v93-too-short", v93, "JMFormatError", "40 字节，小于 60 字节下限")

    v94 = INVALID / "v94-unknown-key-id.jm"
    JMCrypto({7: hashlib.sha256(b"not-in-test-store").digest()}, default_key_id=7).encrypt_file(
        hello, v94, pad_range=(0, 0)
    )
    add_invalid("v94-unknown-key-id", v94, "JMFormatError", "key_id=7，测试密钥库里没有")

    v95 = INVALID / "v95-zero-meta-len.jm"
    zero_meta = bytearray(original)
    zero_meta[24:28] = (0).to_bytes(4, "big")
    v95.write_bytes(bytes(zero_meta))
    add_invalid("v95-zero-meta-len", v95, "JMFormatError", "meta_len 置 0")

    manifest = {
        "protocol": "JM01",
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "generator": "testvectors/make_vectors.py",
        "test_key_id": TEST_KEY_ID,
        "keys_file": "keys.test.json",
        "note": "keys.test.json 里的密钥由 sha256(b'openjm-test-vector-key-v1') 派生，仅用于向量，禁止用于真实文档。",
        "vectors": vectors,
    }
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    total = sum(len(p.read_bytes()) for p in list(VALID.iterdir()) + list(INVALID.iterdir()))
    print(f"生成完成：{len(vectors)} 个向量，密文合计 {total} 字节")
    for entry in vectors:
        print(f"  [{entry['kind']:7}] {entry['id']:26} {entry['file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
