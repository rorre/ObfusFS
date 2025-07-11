import errno
import os
import stat
import fuse
from fuse import Fuse

from obfuse.path import Directory, File, PathManager


if not hasattr(fuse, "__version__"):
    raise RuntimeError("your fuse-py doesn't know of fuse.__version__, probably it's too old.")

fuse.fuse_python_api = (0, 2)

fuse.feature_assert("stateful_files", "has_init")


class DirectoryStat(fuse.Stat):
    def __init__(self, directory: Directory):
        self.st_mode = stat.S_IFDIR | 0o755
        self.st_ino = 0  # dont care, FUSE will take care of it
        self.st_dev = 0  # dont care, FUSE will take care of it
        self.st_nlink = 2 + len(list(filter(lambda x: isinstance(x, Directory), directory.children)))
        self.st_uid = directory.uid
        self.st_gid = directory.gid
        self.st_size = 4096
        self.st_atime = directory.atime
        self.st_mtime = directory.mtime
        self.st_ctime = directory.ctime


class ObfuseFS(Fuse):
    path_manager: PathManager

    def __init__(self, *args, **kw):
        Fuse.__init__(self, *args, **kw)
        self.data = ""
        self.password = ""

    # Directory related
    def readdir(self, path: str, offset: int):
        try:
            for e in self.path_manager.get_directory(path).children.keys():
                yield fuse.Direntry(e)
        except FileNotFoundError:
            return -errno.ENOENT

    def rmdir(self, path: str):
        try:
            self.path_manager.rmdir(path)
        except FileNotFoundError:
            return -errno.ENOENT

    def mknod(self, path: str, mode: int, dev: int):
        try:
            self.path_manager.create_file(path)
        except FileExistsError:
            return -errno.EEXIST
        except FileNotFoundError:
            return -errno.ENOENT

        p = self.path_manager.get_path(path)
        os.mknod("." + p.true_path, mode, dev)

    def mkdir(self, path: str, mode: int):
        ctx = self.GetContext()
        self.path_manager.mkdir(path, ctx["uid"], ctx["gid"], mode)

    # File related
    def getattr(self, path: str):
        try:
            p = self.path_manager.get_path(path)
        except FileNotFoundError:
            return -errno.ENOENT

        if isinstance(p, Directory):
            return DirectoryStat(p)

        true_path = self.path_manager.get_path(path).true_path
        return os.lstat("." + true_path)

    def unlink(self, path: str):
        try:
            true_path = self.path_manager.get_path(path).true_path
            os.unlink("." + true_path)
            self.path_manager.unlink(path)
        except FileNotFoundError:
            return -errno.ENOENT

    def rename(self, path: str, path1: str):
        try:
            p = self.path_manager.get_path(path)
            new_path = self.path_manager.get_path_or_create(path1)
            if isinstance(p, File):
                os.rename("." + p.true_path, "." + new_path.true_path)

            self.path_manager.unlink(path)
        except FileNotFoundError:
            return -errno.ENOENT

    def chmod(self, path: str, mode: int):
        try:
            p = self.path_manager.get_path(path)
            if isinstance(p, Directory):
                p.mode = mode
                self.path_manager.save()
            else:
                os.chmod("." + self.path_manager.get_path(path).true_path, mode)
        except FileNotFoundError:
            return -errno.ENOENT

    def chown(self, path: str, uid: int, gid: int):
        try:
            p = self.path_manager.get_path(path)
            if isinstance(p, Directory):
                p.uid = uid
                p.gid = gid
                self.path_manager.save()
            else:
                os.chown("." + self.path_manager.get_path(path).true_path, uid, gid)
        except FileNotFoundError:
            return -errno.ENOENT

    def truncate(self, path: str, len: int):
        try:
            f = open("." + self.path_manager.get_path(path).true_path, "a")
            f.truncate(len)
            f.close()
        except FileNotFoundError:
            return -errno.ENOENT

    def read(self, path: str, size: int, offset: int) -> bytes | int:
        """Reads up to "size" bytes from file specified by "path"

        Parameters
        ----------
        path : str
            The name (path) of the requested file.

        size : int
            The maximum number of bytes this function will return.
            Defaults to reading to the end of the file.

        offset : int
            The number of bytes to skip from the beginning of the
            file. Defaults to 0.
        """
        try:
            true_path = self.path_manager.get_path(path).true_path
            with open("." + true_path, "rb") as f:
                f.seek(offset)
                return f.read(size)
        except FileNotFoundError:
            return -errno.ENOENT

    def write(self, path: str, body: bytes, offset: int):
        try:
            true_path = self.path_manager.get_path_or_create(path).true_path
            with open("." + true_path, "wb") as f:
                f.seek(offset)
                return f.write(body)
        except FileNotFoundError:
            return -errno.ENOENT

    def statfs(self):
        """
        Should return an object with statvfs attributes (f_bsize, f_frsize...).
        Eg., the return value of os.statvfs() is such a thing (since py 2.2).
        If you are not reusing an existing statvfs object, start with
        fuse.StatVFS(), and define the attributes.

        To provide usable information (i.e., you want sensible df(1)
        output, you are suggested to specify the following attributes:

            - f_bsize - preferred size of file blocks, in bytes
            - f_frsize - fundamental size of file blcoks, in bytes
                [if you have no idea, use the same as blocksize]
            - f_blocks - total number of blocks in the filesystem
            - f_bfree - number of free blocks
            - f_files - total number of file inodes
            - f_ffree - nunber of free file inodes
        """

        return os.statvfs(".")

    def fsinit(self):
        os.chdir(self.data)

    def main(self, *a, **kw):
        return Fuse.main(self, *a, **kw)
