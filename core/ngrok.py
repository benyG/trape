#!/usr/bin/env python
# -*- coding: utf-8 -*-
#**
#
#########
# trape #
#########
#
# trape depends of this file
# For full copyright information this visit: https://github.com/jofpin/trape
#
# Copyright 2018 by Jose Pino (@jofpin) / <jofpin@gmail.com>
#**
import os
import sys
import platform
import shutil
import zipfile
import tarfile
import subprocess
import urllib.request
import os.path as path
from multiprocessing import Process

# ngrok v3 download index (equinox CDN, same one the official installer uses).
NGROK_CDN = "https://bin.equinox.io/c/bNyj1mQVY4c"


def _binary_name():
    return "ngrok.exe" if os.name == "nt" else "ngrok"


def locate_ngrok():
    """Return a usable ngrok binary path: a local ./ngrok, then one on PATH,
    otherwise '' so the caller knows it has to be downloaded."""
    local = os.path.join(".", _binary_name())
    if path.exists(local):
        return local
    found = shutil.which("ngrok")
    if found:
        return found
    return ""


def _download_target():
    """Resolve the right ngrok v3 archive URL and its type for this platform."""
    system_name = platform.system().lower()      # linux / darwin / windows
    machine = platform.machine().lower()          # x86_64 / aarch64 / armv7l / i386 ...

    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("aarch64", "arm64"):
        arch = "arm64"
    elif machine.startswith("arm"):
        arch = "arm"
    elif machine in ("i386", "i686", "x86"):
        arch = "386"
    else:
        arch = "amd64"

    if "darwin" in system_name:
        return "%s/ngrok-v3-stable-darwin-%s.zip" % (NGROK_CDN, arch), "zip"
    elif "windows" in system_name or os.name == "nt":
        return "%s/ngrok-v3-stable-windows-%s.zip" % (NGROK_CDN, arch), "zip"
    # linux (and anything unknown) ships as a .tgz
    return "%s/ngrok-v3-stable-linux-%s.tgz" % (NGROK_CDN, arch), "tgz"


def download_ngrok():
    """Fetch and extract the ngrok v3 binary into the current directory using
    the Python standard library (no external unzip/tar required)."""
    url, kind = _download_target()
    archive = "ngrok." + kind
    print("[*] Downloading ngrok (v3)...")
    urllib.request.urlretrieve(url, archive)

    if kind == "zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(".")
    else:
        with tarfile.open(archive) as tf:
            try:
                # 'data' filter (Python 3.12+, backported to 3.11.4) guards
                # against path traversal; fall back for older interpreters.
                tf.extractall(".", filter="data")
            except TypeError:
                tf.extractall(".")

    try:
        os.remove(archive)
    except OSError:
        pass

    binary = os.path.join(".", _binary_name())
    if path.exists(binary) and os.name != "nt":
        os.chmod(binary, 0o755)
    return binary


class ngrok(object):
    def __init__(self, authtoken, port, nT, hash):
        if not authtoken:
            print("Can't use Ngrok without a valid token")
            return
        self.token = authtoken

        str_ngrok = locate_ngrok()
        if not str_ngrok:
            try:
                str_ngrok = download_ngrok()
            except Exception as e:
                print("[x] ERROR: could not download ngrok: %s" % e)
                return

        # Register the authtoken. ngrok v3 uses `config add-authtoken`; keep the
        # legacy `authtoken` command as a fallback for older binaries.
        if not _run_ngrok([str_ngrok, "config", "add-authtoken", authtoken]):
            if not _run_ngrok([str_ngrok, "authtoken", authtoken]):
                print("[x] ERROR: could not register the ngrok authtoken")
                return

        if nT > 0:
            pNg = Process(target=start_ngrok, args=(str(port), hash, 1))
            pNg.daemon = True
            pNg.start()


def _run_ngrok(cmd):
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return True
    except Exception:
        return False


def start_ngrok(port, hash, f=0):
    if f == 0:
        return
    str_ngrok = locate_ngrok()
    if not str_ngrok:
        return
    # Run headless: `--log stdout` keeps ngrok v3 out of its interactive TUI so
    # it works when spawned as a background process. Output goes to ngrok.log.
    cmd = [str_ngrok, "http", str(port), "--log", "stdout"]
    try:
        with open("ngrok.log", "a") as logf:
            subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT).wait()
    except Exception as e:
        print("[x] ERROR: ngrok failed to start: %s" % e)
