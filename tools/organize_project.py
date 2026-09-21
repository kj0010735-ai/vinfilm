#!/usr/bin/env python3
"""프리미어 프로 프로젝트 폴더 정리기 — 분류 엔진 + 명령줄 (VINFILM STUDIO)

폴더 안에 흩어진 파일을 카테고리 폴더(01_FOOTAGE ~ 08_CACHE 등)로 분류해서 옮긴다.
카테고리/규칙은 설정 파일(~/Library/Application Support/VINFILM Project Organizer/config.json)에
저장되며, 앱(organizer_app.py)의 '분류 설정' 탭에서 편집한다. 명령줄도 같은 설정을 쓴다.

  python3 organize_project.py <폴더>            # 미리보기 후 y 입력하면 실행
  python3 organize_project.py <폴더> --yes      # 확인 없이 바로 실행
  python3 organize_project.py <폴더> --copy     # 이동 대신 복사 (원본 유지)
  python3 organize_project.py <폴더> --undo     # 마지막 정리를 되돌림

표준 라이브러리만 사용 — 설치할 것 없음.
"""
import argparse
import copy
import json
import re
import shutil
import sys
from pathlib import Path

SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "VINFILM Project Organizer"
CONFIG_PATH = SUPPORT_DIR / "config.json"
LOG_NAME = "_organize_log.json"

VIDEO = [".mp4", ".mov", ".mxf", ".m4v", ".avi", ".mkv", ".mts", ".m2ts", ".webm", ".r3d", ".braw"]

DEFAULT_CONFIG = {
    "categories": [
        {"folder": "01_FOOTAGE", "extensions": VIDEO, "keywords": [], "dirs": [], "matchProjectName": False},
        {"folder": "02_AUDIO", "extensions": [".wav", ".aif", ".aiff", ".m4a", ".flac", ".aac"],
         "keywords": [], "dirs": [], "matchProjectName": False},
        {"folder": "03_MUSIC", "extensions": [".mp3"], "keywords": [], "dirs": [], "matchProjectName": False},
        {"folder": "04_PROJECT", "extensions": [".prproj", ".prin", ".aep", ".psb", ".drp"],
         "keywords": [], "dirs": ["Masks"], "matchProjectName": False},
        {"folder": "05_EXPORT", "extensions": VIDEO, "keywords": ["final", "export", "최종", "렌더"],
         "dirs": [], "matchProjectName": True},
        {"folder": "06_PROXY", "extensions": VIDEO, "keywords": ["proxy"], "dirs": [], "matchProjectName": False},
        {"folder": "07_GRAPHICS",
         "extensions": [".png", ".jpg", ".jpeg", ".psd", ".ai", ".svg", ".gif", ".tif", ".tiff", ".webp", ".heic", ".pdf", ".eps"],
         "keywords": [], "dirs": [], "matchProjectName": False},
        {"folder": "08_CACHE", "extensions": [], "keywords": [], "dirs": ["Previews", "Auto-Save", "Media Cache"],
         "matchProjectName": False},
    ],
    "fallback": "",
}


def _clean_list(values, is_ext=False):
    out = []
    for v in values or []:
        v = str(v).strip()
        if not v:
            continue
        if is_ext:
            v = v.lower()
            if not v.startswith("."):
                v = "." + v
        else:
            v = v.lower()
        if v not in out:
            out.append(v)
    return out


def _clean_folder(name):
    return re.sub(r"[/:\\\0]", "-", str(name)).strip().strip(".")


def normalize(cfg):
    """UI/파일에서 온 설정을 검증해서 정규형으로 만든다."""
    cats, seen = [], set()
    for c in (cfg or {}).get("categories", []):
        folder = _clean_folder(c.get("folder", ""))
        if not folder or folder in seen:
            continue
        seen.add(folder)
        cats.append({
            "folder": folder,
            "extensions": _clean_list(c.get("extensions"), is_ext=True),
            "keywords": _clean_list(c.get("keywords")),
            "dirs": _clean_list(c.get("dirs")),
            "matchProjectName": bool(c.get("matchProjectName")),
        })
    fallback = _clean_folder((cfg or {}).get("fallback", ""))
    if fallback in seen:
        fallback = ""
    return {"categories": cats, "fallback": fallback}


def load_config():
    try:
        return normalize(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return copy.deepcopy(DEFAULT_CONFIG)


def save_config(cfg):
    cfg = normalize(cfg)
    SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    return cfg


def folder_names(cfg):
    names = [c["folder"] for c in cfg["categories"]]
    if cfg["fallback"]:
        names.append(cfg["fallback"])
    return names


def classify(path, project_stems, cfg):
    """항목 하나의 목적지 폴더 이름. 모르면 None.

    규칙: 폴더는 '폴더 이름 포함 단어'로, 파일은 ① 단어/프로젝트명 조건이 있는 카테고리
    (확장자도 함께 맞아야 함, 확장자가 비었으면 무관) → ② 확장자만 있는 카테고리 → ③ 기타 폴더 순.
    같은 단계에서는 목록 위쪽 카테고리가 우선.
    """
    cats = cfg["categories"]
    low = path.name.lower()
    if path.is_dir():
        for c in cats:
            if any(d.lower() in low for d in c["dirs"]):
                return c["folder"]
        return None

    ext, stem = path.suffix.lower(), path.stem
    for c in cats:
        if not (c["keywords"] or c["matchProjectName"]):
            continue
        if c["extensions"] and ext not in c["extensions"]:
            continue
        if any(k in low for k in c["keywords"]) or (c["matchProjectName"] and stem in project_stems):
            return c["folder"]
    for c in cats:
        if c["keywords"] or c["matchProjectName"]:
            continue
        if ext in c["extensions"]:
            return c["folder"]
    return cfg["fallback"] or None


def plan(root, cfg):
    reserved = set(folder_names(cfg))
    items = [p for p in sorted(root.iterdir()) if p.name not in (".DS_Store", LOG_NAME)]
    project_stems = {p.stem for p in items if p.suffix.lower() == ".prproj"}
    moves, skipped, conflicts = [], [], []
    for p in items:
        if p.is_dir() and p.name in reserved:
            continue
        folder = classify(p, project_stems, cfg)
        if folder is None:
            skipped.append(p)
            continue
        dest = root / folder / p.name
        (conflicts if dest.exists() else moves).append((p, dest))
    return moves, skipped, conflicts


def _read_log(root):
    try:
        return json.loads((root / LOG_NAME).read_text(encoding="utf-8")).get("runs", [])
    except (OSError, ValueError):
        return []


def has_undo(root):
    return bool(_read_log(root))


def execute(root, moves, cfg, copy_mode=False):
    """계획을 실행한다. (완료 개수, 실패 메시지 목록)"""
    for name in [c["folder"] for c in cfg["categories"]]:
        (root / name).mkdir(exist_ok=True)
    done, failed = [], []
    for src, dest in moves:
        try:
            dest.parent.mkdir(exist_ok=True)
            if copy_mode:
                shutil.copytree(src, dest) if src.is_dir() else shutil.copy2(src, dest)
            else:
                shutil.move(str(src), str(dest))
            done.append([str(src), str(dest)])
        except OSError as e:
            failed.append(f"{src.name}: {e}")
    if done and not copy_mode:  # 복사는 원본이 남아 있으니 되돌릴 기록이 필요 없다
        runs = _read_log(root) + [done]
        (root / LOG_NAME).write_text(
            json.dumps({"runs": runs}, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(done), failed


def undo(root):
    """마지막 이동을 되돌린다. 되돌린 개수를 반환."""
    runs = _read_log(root)
    if not runs:
        raise ValueError("되돌릴 기록이 없어요.")
    count = 0
    for src, dest in runs[-1]:
        s, d = Path(src), Path(dest)
        if d.exists() and not s.exists():
            shutil.move(str(d), str(s))
            count += 1
    runs = runs[:-1]
    log = root / LOG_NAME
    if runs:
        log.write_text(json.dumps({"runs": runs}, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        log.unlink(missing_ok=True)
    return count


def main():
    ap = argparse.ArgumentParser(description="프리미어 프로젝트 폴더 정리기")
    ap.add_argument("folder", help="정리할 프로젝트 폴더")
    ap.add_argument("--yes", action="store_true", help="확인 없이 바로 실행")
    ap.add_argument("--copy", action="store_true", help="이동 대신 복사")
    ap.add_argument("--undo", action="store_true", help="마지막 정리를 되돌림")
    ap.add_argument("--dry-run", action="store_true", help="계획만 출력하고 종료")
    args = ap.parse_args()

    root = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"폴더를 찾을 수 없어요: {root}")

    if args.undo:
        try:
            print(f"{undo(root)}개 항목을 원래 위치로 되돌렸어요.")
        except ValueError as e:
            sys.exit(str(e))
        return

    cfg = load_config()
    moves, skipped, conflicts = plan(root, cfg)
    if not moves:
        print("정리할 항목이 없어요.")
    else:
        print(f"\n[{root.name}] 정리 계획 — {'복사' if args.copy else '이동'} {len(moves)}개\n")
        for folder in folder_names(cfg):
            group = [s for s, d in moves if d.parent.name == folder]
            if group:
                print(f"{folder}  ({len(group)})")
                for s in group:
                    print(f"   {s.name}{'/' if s.is_dir() else ''}")
    if conflicts:
        print(f"\n이미 같은 이름이 있어서 건너뜀 ({len(conflicts)})")
        for s, _ in conflicts:
            print(f"   {s.name}")
    if skipped:
        print(f"\n분류 못 해서 그대로 둠 ({len(skipped)})")
        for s in skipped:
            print(f"   {s.name}{'/' if s.is_dir() else ''}")
    if not moves or args.dry_run:
        return

    print("\n※ 파일을 옮기면 기존 프리미어 프로젝트는 '미디어 오프라인'이 뜹니다."
          " 정리 후 프로젝트를 열어 Link Media로 한 번 연결해 주세요.")
    if not args.yes and input("\n진행할까요? (y/N) ").strip().lower() != "y":
        print("취소했어요.")
        return

    n, failed = execute(root, moves, cfg, copy_mode=args.copy)
    for f in failed:
        print("실패:", f)
    print(f"\n완료: {n}개 {'복사' if args.copy else '이동'}." + ("" if args.copy else " 되돌리려면 --undo"))


if __name__ == "__main__":
    main()
