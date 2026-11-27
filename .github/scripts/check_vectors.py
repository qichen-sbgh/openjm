#!/usr/bin/env python3
"""校验 testvectors 清单自洽性（不依赖 openjm-sdk、不做解密）。

覆盖三件事：
1. manifest 本身字段合法、引用的文件都存在；
2. valid 向量的长度恒等式 `28 + meta_len + size + pad + 32 == 文件长度` 成立；
3. 明文 sha256 与 manifest 记录一致，防止有人换了 plain/ 却没重跑生成脚本。
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "testvectors"
HEADER = struct.Struct(">4sBBBB16sI")
HEADER_SIZE, MAC_SIZE = 28, 32
ERRORS = {"JMFormatError", "JMAuthError"}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> int:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("protocol") != "JM01":
        fail("manifest.protocol 必须是 JM01")
    if manifest.get("test_key_id") != 254:
        fail("测试向量必须使用 key_id=254")

    keys = json.loads((ROOT / manifest["keys_file"]).read_text(encoding="utf-8"))
    if list(keys) != ["254"] or len(bytes.fromhex(keys["254"])) != 32:
        fail("keys.test.json 必须只含 32 字节的 key_id=254")

    checked = 0
    for entry in manifest["vectors"]:
        path = ROOT / entry["file"]
        if not path.is_file():
            fail(f"{entry['id']}: 缺少文件 {entry['file']}")
        total = path.stat().st_size
        if entry["kind"] != "invalid" and total < HEADER_SIZE + MAC_SIZE:
            fail(f"{entry['id']}: valid 向量小于最小长度")

        if entry["kind"] == "invalid":
            if entry.get("error") not in ERRORS:
                fail(f"{entry['id']}: error 必须是 {ERRORS}")
            checked += 1
            continue

        magic, version, alg, flags, key_id, _nonce, meta_len = HEADER.unpack(path.read_bytes()[:HEADER_SIZE])
        if magic != b"JM01" or version != 1 or alg != 1:
            fail(f"{entry['id']}: 头部 magic/version/alg 不合法")
        if not 1 <= meta_len <= 65536:
            fail(f"{entry['id']}: meta_len 越界")

        expect = entry["expect"]
        claimed = HEADER_SIZE + meta_len + expect["size"] + expect["pad"] + MAC_SIZE
        if claimed != total:
            fail(f"{entry['id']}: 长度恒等式不成立（声明 {claimed}，实际 {total}）")

        plain = ROOT / "plain" / expect["name"]
        if not plain.is_file():
            fail(f"{entry['id']}: 缺少明文 plain/{expect['name']}")
        if hashlib.sha256(plain.read_bytes()).hexdigest() != expect["sha256"]:
            fail(f"{entry['id']}: 明文 sha256 与清单不符")

        if key_id not in (0, 254):
            fail(f"{entry['id']}: key_id 应为 254（或口令模式的 0），实际 {key_id}")
        if bool(flags & 0x01) != bool(entry.get("password")):
            fail(f"{entry['id']}: flags 的口令位与 manifest.password 不一致")
        checked += 1

    print(f"OK: {checked} 个向量通过结构校验")
    return 0


if __name__ == "__main__":
    sys.exit(main())
