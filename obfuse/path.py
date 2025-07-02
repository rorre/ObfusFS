from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
import struct
from typing import Literal
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import random
import string

MAGIC = "OBFUSFS".encode()
PathLike = os.PathLike[str] | str


def random_obfuscated_name(length: int = 16) -> str:
    characters = string.ascii_letters + string.digits
    return "".join(random.choice(characters) for _ in range(length))


def pack_string(s: str):
    return struct.pack(f">L{len(s)}s", len(s), s.encode())


def unpack_string(data: bytes, offset: int = 0) -> tuple[str, int]:
    length = struct.unpack_from(">L", data, offset)[0]
    return struct.unpack_from(f">{length}s", data, 4 + offset)[0].decode(), struct.calcsize(f">L{length}s")


@dataclass
class File:
    name: str
    obfuscated_name: str
    parent: "Directory | None" = None

    def _as_struct(self, type: Literal["F", "D"]):
        return struct.pack(">c", type.encode()) + pack_string(self.name) + pack_string(self.obfuscated_name)

    def as_struct(self):
        return self._as_struct("F")

    @staticmethod
    def from_struct(data: bytes) -> "tuple[File, bytes]":
        type = struct.unpack_from(">c", data)[0]
        data = data[1:]
        name, offset = unpack_string(data)
        obfuscated_name, offset2 = unpack_string(data, offset)

        rest_of_data = data[offset + offset2 :]
        if type not in (b"F", b"D"):
            raise ValueError("Invalid struct")
        if type == b"F":
            return File(name, obfuscated_name), rest_of_data

        dir = Directory(name, obfuscated_name, None, {})
        rest_of_data = dir._load_dir_info(rest_of_data)
        return dir, rest_of_data

    @property
    def fullpath(self):
        if not self.parent:
            return self.name
        return os.path.join(self.parent.fullpath, self.name)

    @property
    def true_path(self):
        if isinstance(self, Directory):
            return "/"
        return "/" + self.obfuscated_name


@dataclass
class Directory(File):
    children: dict[str, File] = field(default_factory=dict)
    uid: int = 0
    gid: int = 0
    mode: int = 0o755
    atime: int = 0
    mtime: int = 0
    ctime: int = 0

    def as_struct(self):
        file_endoded = super()._as_struct(type="D")
        dir_info = struct.pack(
            ">IIILLLL",
            self.uid,
            self.gid,
            self.mode,
            self.atime,
            self.mtime,
            self.ctime,
            len(self.children),
        )
        all_children = b"".join(map(lambda x: x.as_struct(), self.children.values()))
        return file_endoded + dir_info + all_children

    def _load_dir_info(self, data: bytes):
        self.uid, self.gid, self.mode, self.atime, self.mtime, self.ctime, total_children = struct.unpack_from(
            ">IIILLLL", data
        )
        data = data[struct.calcsize(">IIILLLL") :]

        for _ in range(total_children):
            f, data = File.from_struct(data)
            f.parent = self
            self.children[f.name] = f

        return data


class PathManager:
    def __init__(self, db_location: PathLike, password: str | bytes):
        if isinstance(password, str):
            password = password.encode()

        self._password = pad(password, block_size=16)
        self._db_location = db_location

    def load(self):
        with open(self._db_location, "rb") as f:
            magic = f.read(len(MAGIC))
            if magic != MAGIC:
                raise ValueError("Invalid file format")
            nonce = f.read(16)
            tag = f.read(16)
            ciphertext = f.read()

        cipher = AES.new(self._password, AES.MODE_GCM, nonce=nonce)
        cipher.update(MAGIC)

        data = cipher.decrypt_and_verify(ciphertext, tag)
        root, _ = File.from_struct(data)
        if not isinstance(root, Directory):
            raise ValueError("Root is not a directory")

        if root.name != "/":
            raise ValueError("Unexpected root")
        self._root = root

    def save(self):
        data = self._root.as_struct()

        cipher = AES.new(self._password, AES.MODE_GCM)
        cipher.update(MAGIC)

        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(data)
        with open(self._db_location, "wb") as f:
            f.write(MAGIC)
            f.write(nonce)
            f.write(tag)
            f.write(ciphertext)

    def load_or_create(self):
        try:
            self.load()
        except FileNotFoundError:
            self._root = Directory("/", "/")
            self.save()

    def get_path(self, path: PathLike):
        parts = Path(path).parts
        p = self._root
        for part in parts[1:]:  # First is always /
            if not isinstance(p, Directory):
                raise FileNotFoundError("Could not find", path)

            new_p = p.children.get(part, None)
            if not new_p:
                raise FileNotFoundError("Could not find", path)

            p = new_p

        return p

    def get_path_or_create(self, path: PathLike):
        try:
            return self.get_path(path)
        except FileNotFoundError:
            return self.create_file(path)

    def get_directory(self, path: PathLike):
        p = self.get_path(path)
        if not isinstance(p, Directory):
            raise NotADirectoryError(f"{path} is not a directory")
        return p

    def get_file(self, path: PathLike):
        p = self.get_path(path)
        if not isinstance(p, File):
            raise FileNotFoundError(f"{path} is not a file")
        return p

    def create_file(self, path: PathLike):
        p = Path(path)
        if len(p.parts) < 2:
            raise ValueError("Invalid path")

        parent_path = p.parent
        parent_dir = self.get_directory(parent_path)

        if p.name in parent_dir.children:
            raise FileExistsError(f"File {path} already exists")

        new_file = File(p.name, random_obfuscated_name(64), parent_dir)
        parent_dir.children[p.name] = new_file
        self.save()
        return new_file

    def unlink(self, path: PathLike):
        file = self.get_file(path)
        if not file.parent:
            raise ValueError("Cannot unlink root file")

        del file.parent.children[file.name]
        self.save()

    def rmdir(self, path: PathLike):
        dir = self.get_directory(path)
        if not dir.parent:
            raise ValueError("Cannot remove root directory")

        if dir.children:
            raise OSError("Directory not empty")
        del dir.parent.children[dir.name]
        self.save()

    def mkdir(self, path: PathLike, uid: int, gid: int, mode: int = 0o755):
        p = Path(path)
        if len(p.parts) < 2:
            raise ValueError("Invalid path")

        parent_path = p.parent
        parent_dir = self.get_directory(parent_path)

        if p.name in parent_dir.children:
            raise FileExistsError(f"Directory {path} already exists")

        new_dir = Directory(p.name, p.name, parent_dir)
        new_dir.atime = new_dir.mtime = new_dir.ctime = int(datetime.now().timestamp())
        new_dir.uid = uid
        new_dir.gid = gid
        new_dir.mode = mode
        parent_dir.children[p.name] = new_dir
        self.save()
