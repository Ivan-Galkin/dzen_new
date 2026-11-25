import subprocess
import time
import zipfile
from pathlib import Path

REMOTE = "https://github.com/Ivan-Galkin/dzen_new.git"


def snapshot(state, destination, folders):
    cache = state / "git-cache"
    if not cache.exists():
        subprocess.run(["git", "init", "--bare", str(cache)], check=True)
    command = ["git", "-C", str(cache)]
    for attempt in range(2):
        proc = subprocess.run(command + ["fetch", "--depth=1", REMOTE, "refs/heads/master"],
                              timeout=180, check=False)
        if proc.returncode == 0:
            break
        if attempt:
            raise RuntimeError("GitHub недоступен. Загрузка отменена.")
        time.sleep(3)
    rev = subprocess.check_output(command + ["rev-parse", "FETCH_HEAD"], text=True).strip()
    archive = destination / "source.zip"
    subprocess.run(command + ["archive", "--format=zip", "-o", str(archive), rev], check=True)
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            p = Path(member.filename)
            if (not p.parts or p.parts[0] not in folders or p.suffix.lower() not in (".md", ".txt")
                    or len(p.parts) > 3):
                continue
            target = (destination / p).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("Некорректный путь в архиве")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.read(member))
    return rev
