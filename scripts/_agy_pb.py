"""
_agy_pb.py: Antigravity CLI 本地存储共用底层助手。
提供无损 protobuf wire 编解码、同目录原子写文件与 SQLite 在线滚动备份。
"""

import os
import sqlite3
import tempfile
from typing import List, Optional, Tuple


def read_varint(buf: bytes, idx: int) -> Optional[Tuple[int, int]]:
    val = 0
    shift = 0
    while idx < len(buf):
        b = buf[idx]
        idx += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, idx
        shift += 7
    return None


def encode_varint(val: int) -> bytes:
    out = bytearray()
    while True:
        b = val & 0x7F
        val >>= 7
        if val:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def parse_pb_fields(blob: bytes) -> Optional[List[Tuple[int, int, bytes]]]:
    """无损解析 protobuf wire 字段列表 (field_num, wire_type, raw_payload)。"""
    fields: List[Tuple[int, int, bytes]] = []
    idx = 0
    n = len(blob)
    while idx < n:
        tag_res = read_varint(blob, idx)
        if tag_res is None:
            return None
        tag, idx = tag_res
        fn, wt = tag >> 3, tag & 7
        if fn <= 0:
            return None
        if wt == 0:
            start = idx
            res = read_varint(blob, idx)
            if res is None:
                return None
            _, idx = res
            fields.append((fn, wt, blob[start:idx]))
        elif wt == 1:
            if idx + 8 > n:
                return None
            fields.append((fn, wt, blob[idx : idx + 8]))
            idx += 8
        elif wt == 2:
            len_res = read_varint(blob, idx)
            if len_res is None:
                return None
            ln, idx = len_res
            if idx + ln > n:
                return None
            fields.append((fn, wt, blob[idx : idx + ln]))
            idx += ln
        elif wt == 5:
            if idx + 4 > n:
                return None
            fields.append((fn, wt, blob[idx : idx + 4]))
            idx += 4
        else:
            return None
    return fields


def encode_pb_fields(fields: List[Tuple[int, int, bytes]]) -> bytes:
    out = bytearray()
    for fn, wt, payload in fields:
        out.extend(encode_varint((fn << 3) | wt))
        if wt == 2:
            out.extend(encode_varint(len(payload)))
        out.extend(payload)
    return bytes(out)


def upsert_len_field(
    fields: List[Tuple[int, int, bytes]], field_num: int, new_bytes: bytes
) -> List[Tuple[int, int, bytes]]:
    replaced = False
    out: List[Tuple[int, int, bytes]] = []
    for fn, wt, payload in fields:
        if fn == field_num and wt == 2:
            if not replaced:
                out.append((fn, 2, new_bytes))
                replaced = True
        else:
            out.append((fn, wt, payload))
    if not replaced:
        out.append((field_num, 2, new_bytes))
    return out


def atomic_write_bytes(path: str, data: bytes, prefix: str = ".agy_") -> None:
    target_dir = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=prefix, dir=target_dir)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def atomic_write_text(path: str, text: str, prefix: str = ".agy_") -> None:
    atomic_write_bytes(path, text.encode("utf-8"), prefix=prefix)


def create_rolling_backup(conn: sqlite3.Connection, db_path: str) -> None:
    """使用 SQLite online backup API 生成单份滚动备份，避免多版本堆积。"""
    bak_path = db_path + ".bak"
    dst = sqlite3.connect(bak_path)
    try:
        conn.backup(dst)
    finally:
        dst.close()
