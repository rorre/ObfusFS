#!/usr/bin/env python

#    Copyright (C) 2001  Jeff Epler  <jepler@gmail.com>
#    Copyright (C) 2006  Csaba Henk  <csaba.henk@creo.hu>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
#

from __future__ import print_function

import os, sys
from fuse import Fuse

from obfusfs.fs import ObfusFS
from obfusfs.path import PathManager


def main():

    usage = (
        """
Obfus-FS: A FUSE that obfuscates the location of all files inside a directory

"""
        + Fuse.fusage
    )

    server = ObfusFS(usage=usage)

    server.parser.add_option(
        mountopt="data",
        metavar="PATH",
        default="/",
        help="data location for the filesystem [default: %default]",
    )
    server.parser.add_option(
        mountopt="password",
        help="password to encrypt the filesystem",
    )
    server.parse(values=server, errex=1)

    if server.data[0] != "/":
        server.data = os.path.abspath(server.data)

    try:
        if server.fuse_args.mount_expected():
            os.chdir(server.data)
    except OSError:
        print("can't enter root of underlying filesystem", file=sys.stderr)
        sys.exit(1)

    server.path_manager = PathManager(
        server.data + "/obfusfs.db",
        server.password,
    )
    server.path_manager.load_or_create()
    server.main()


if __name__ == "__main__":
    main()
