#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import sys
from urllib.parse import urljoin
from urllib.request import Request, urlopen


def fetch_picture_list(base_url):
    list_url = urljoin(base_url.rstrip("/") + "/", "list")
    req = Request(list_url, headers={"User-Agent": "photobooth-sync/1.0"})
    with urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    if not isinstance(data, dict):
        raise ValueError("List endpoint did not return a JSON object")

    pictures = data.get("pictures")
    if not isinstance(pictures, list):
        raise ValueError("List endpoint did not return a valid pictures list")

    return data.get("base", ""), pictures


def remote_file_url(base_url, remote_base, name):
    base = remote_base.strip("/")
    file_name = str(name).lstrip("/")
    if base:
        return urljoin(base_url.rstrip("/") + "/", f"{base}/{file_name}")
    return urljoin(base_url.rstrip("/") + "/", file_name)


def download_file(remote_url, destination):
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    req = Request(remote_url, headers={"User-Agent": "photobooth-sync/1.0"})
    with urlopen(req, timeout=60) as response, open(destination, "wb") as out_file:
        shutil.copyfileobj(response, out_file)


def sync(base_url, local_dir):
    os.makedirs(local_dir, exist_ok=True)
    remote_base, pictures = fetch_picture_list(base_url)

    downloaded = 0
    skipped = 0

    for item in pictures:
        if not isinstance(item, dict):
            continue

        name = item.get("url")
        if not name:
            continue

        remote_url = remote_file_url(base_url, remote_base, name)
        destination = os.path.join(local_dir, os.path.basename(name))

        try:
            remote_size = int(item.get("size", -1))
        except (TypeError, ValueError):
            remote_size = -1

        if os.path.exists(destination):
            local_size = os.path.getsize(destination)
            if remote_size >= 0 and local_size == remote_size:
                skipped += 1
                continue

        download_file(remote_url, destination)
        downloaded += 1
        print(f"downloaded {name} -> {destination}")

    print(f"done: downloaded={downloaded}, skipped={skipped}")
    return downloaded


def main():
    parser = argparse.ArgumentParser(description="Sync photobooth files from a remote list endpoint.")
    parser.add_argument("base_url", help="Base URL of the photobooth server, e.g. http://server:8082")
    parser.add_argument("local_dir", help="Local directory to store the downloaded files")
    args = parser.parse_args()

    try:
        sync(args.base_url, args.local_dir)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
