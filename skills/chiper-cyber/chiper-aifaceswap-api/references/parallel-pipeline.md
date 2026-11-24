# Parallel face-swap pipeline — recipe & code shape

Session context: web UI (FastAPI) splitting a ≤60s video into N×5s clips, swapping each, zipping.
The sequential loop (`for clip in clips: generate; poll; download`) was the bottleneck: ~45s/clip.

## Why parallelism is safe here

- Quota is tracked **server-side per fingerprint** (`code:637` = 3 free videos/day/fp).
- Each browser device has its own fingerprint + cookie jar → its own quota bucket.
- Each task gets its own `task_id`, so polling is independent per device.
- => run N clips at once on N isolated contexts; no contention.

## Two pools

### UploadPool (dodges per-IP CF 429)
```python
class UploadPool:
    def __init__(self, n=4, proxies=None):
        self.n = n
        self.ups = [Uploader(proxy=(proxies[i] if proxies and i < len(proxies) else None))
                    for i in range(n)]
        for u in self.ups:
            try: u.boot()
            except Exception: pass

    def upload_all(self, paths, typ="video", workers=None):
        results = [None] * len(paths)
        def _one(idx):
            results[idx] = self.ups[idx % self.n].upload(paths[idx], typ)
        with ThreadPoolExecutor(max_workers=workers or self.n) as ex:
            list(ex.map(_one, range(len(paths))))
        return results
```
- `Uploader` auto-uses Tor (`socks5h://127.0.0.1:9050`) if a local SOCKS port answers; env
  `CHIPER_UPLOAD_PROXY` overrides. Needs PySocks (`requests[socks]`) in the venv.
- Keep the per-uploader `MIN_GAP` throttle — parallelism + Tor multi-circuit is the real lever.

### GenPool (multi-browser generate)
```python
class GenPool:
    def __init__(self, size=4, prefix="facegen_ui"):
        self.size, self.prefix = size, prefix
        self.gens, self._lock = [], threading.Lock()

    def start(self):                        # one browser device per worker
        with ThreadPoolExecutor(max_workers=self.size) as ex:
            self.gens = list(ex.map(lambda i: self._mk(i), range(self.size)))

    def _mk(self, i):
        g = Generator(f"{self.prefix}_{i}"); g.start(); return g

    def run(self, tasks, on_done=None):
        def _work(task):
            i = task["idx"]
            for attempt in range(3):
                try:
                    g = self.gens[(i + attempt) % self.size]
                    tid, result = g.gen_clip(task["source_video"], task["face_image"],
                                             0, task["end"], timeout=300)
                    g.download(result, task["outfile"])
                    if on_done: on_done(i, True, {"task": tid, "file": task["outfile"]})
                    return
                except Exception as e:
                    err = str(e); time.sleep(2)
            if on_done: on_done(i, False, {"error": err})
        with ThreadPoolExecutor(max_workers=self.size) as ex:
            list(ex.map(_work, tasks))
```
- One `Generator` per worker = one `agent-browser --session facegen_ui_<i>` = own fingerprint.
- A CDP websocket is single-threaded → a device must never be shared by two threads at once.
  Wave mapping (`i % size`) gives each in-flight task its own device.
- Each `gen_clip` still sets a unique `MYUtils.userFP` before submit (belt-and-braces on top of
  device isolation).

## Wiring in the job runner
```python
POOL_SIZE = int(os.environ.get("FACESWAP_WORKERS", "4"))
...
upool = engine.UploadPool(n=min(POOL_SIZE, len(clips) or 1))
clip_cdn = upool.upload_all(clips, "video")
tasks = [{"idx": i, "source_video": c, "face_image": face_cdn, "end": seg,
          "outfile": os.path.join(out_dir, f"faceswap_{i:03d}.mp4")}
         for i, c in enumerate(clip_cdn)]
get_pool().run(tasks, on_done=lambda i, ok, p: st["results"].append(...) if ok
                                               else st["failed"].append(...))
st["results"].sort(key=lambda r: r["idx"])   # keep clip order for the zip
```

## Measured results (this env)
| Clips | Mode | Wall time |
|---|---|---|
| 7 (32s video) | sequential | ~480s |
| 7 | 4 workers | **226s**  (2.1x) |

Projection: 6 workers ≈ 3 min, 8 ≈ 2.5 min for 12 clips. Each browser ≈ 150-200MB RAM — size
`FACESWAP_WORKERS` to available memory.

## systemd
```
Environment=CHIPER_UPLOAD_PROXY=socks5h://127.0.0.1:9050
Environment=FACESWAP_WORKERS=4
ExecStart=<venv>/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8091
```
`Restart=always`, `After=network.target tor.service`, `Wants=tor.service`.

## Env caveat
`FACESWAP_WORKERS` is read at import time (`POOL_SIZE = int(os.environ.get(...))`), so changing it
requires a service restart — the pool is a module global, not hot-reloadable.
