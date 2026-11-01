import os
import threading
import time
import uuid

import imageio_ffmpeg
import yt_dlp

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

jobs = {}
lock = threading.Lock()
resolve_cache = {}
RESOLVE_TTL = 1200


def resolve(url, kind="audio"):
    key = (url, kind)
    with lock:
        hit = resolve_cache.get(key)
        if hit and time.time() - hit[1] < RESOLVE_TTL:
            return hit[0]
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    if kind == "video":
        opts["format"] = "best[ext=mp4][height<=720]/best[height<=720]/best"
    else:
        opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    result = {
        "url": info["url"],
        "title": info.get("title") or "",
        "duration": info.get("duration"),
        "ext": info.get("ext"),
    }
    with lock:
        resolve_cache[key] = (result, time.time())
    return result


def search(query, limit=20):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "default_search": f"ytsearch{limit}",
        "extract_flat": "in_playlist",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)
    results = []
    for e in info.get("entries") or []:
        if not e:
            continue
        results.append(
            {
                "id": e.get("id"),
                "title": e.get("title") or "?",
                "url": e.get("url") or e.get("webpage_url"),
                "duration": e.get("duration"),
                "uploader": e.get("uploader") or e.get("channel") or "",
            }
        )
    return results


def start_download(url, fmt, shared_dir):
    if fmt not in ("mp3", "video"):
        raise ValueError("gecersiz format")
    job_id = uuid.uuid4().hex[:12]
    job = {
        "id": job_id,
        "url": url,
        "format": fmt,
        "status": "basliyor",
        "title": "",
        "progress": 0,
        "speed": None,
        "eta": None,
        "file": None,
        "error": None,
        "started": time.time(),
    }
    with lock:
        jobs[job_id] = job
    threading.Thread(target=_run, args=(job, url, fmt, shared_dir), daemon=True).start()
    return job


def get_jobs():
    with lock:
        return sorted(jobs.values(), key=lambda j: j["started"], reverse=True)


def _run(job, url, fmt, shared_dir):
    def hook(d):
        if d["status"] == "downloading":
            job["status"] = "indiriliyor"
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            if total:
                job["progress"] = int(done * 100 / total)
            job["speed"] = d.get("speed")
            job["eta"] = d.get("eta")
        elif d["status"] == "finished":
            job["status"] = "donusturuluyor" if fmt == "mp3" else "isleniyor"
            job["progress"] = 100

    opts = {
        "outtmpl": os.path.join(shared_dir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "progress_hooks": [hook],
        "ffmpeg_location": FFMPEG,
        "retries": 3,
    }
    if fmt == "mp3":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    else:
        opts["format"] = (
            "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/"
            "best[ext=mp4]/best"
        )
        opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            job["title"] = info.get("title") or url
            base = os.path.splitext(ydl.prepare_filename(info))[0]
            job["file"] = base + (".mp3" if fmt == "mp3" else ".mp4")
        job["status"] = "tamamlandi"
        job["progress"] = 100
    except Exception as exc:
        job["status"] = "hata"
        job["error"] = str(exc)
