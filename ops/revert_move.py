import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "local_artifacts"


def usage():
    print(
        "Usage: python ops/revert_move.py <group_subpath> <target_restore_dir>"
    )
    print(
        "Example: python ops/revert_move.py page010/page_010 C:\\Users\\User\\Downloads\\restore"
    )


def main():
    if len(sys.argv) < 3:
        usage()
        return 2
    src = ROOT / sys.argv[1]
    dest = Path(sys.argv[2])
    if not src.exists():
        print("Source not found:", src)
        return 3
    dest.mkdir(parents=True, exist_ok=True)
    name = src.name
    target = dest / name
    if target.exists():
        print("Target already exists:", target)
        return 4
    print(f"Moving {src} -> {target}")
    shutil.move(str(src), str(target))
    print("Moved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
