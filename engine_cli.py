#!/usr/bin/env python3
"""
통합 CLI — 개별/집단 등기 자동화 (신 엔진)
==========================================
Vision 구조화 추출 + 신뢰도 병합 + 세율(rates_2026) + 안정성 로깅을
묶은 실전 진입점. GUI 없이 배치 처리·검증에 사용.

사용:
  # 개별등기 1세대 (파일 또는 폴더) — 결과 JSON 출력
  python engine_cli.py individual "C:\\서류\\104동2302호" --type 분양

  # 집단등기 (세대별 하위폴더) — 엑셀 기입 + 실행로그
  python engine_cli.py group "C:\\서류\\검단웰카운티" \\
      --mapping 검단롯데캐슬넥스티엘 --out 기본명단.xlsx --append --workers 5

옵션:
  --type      분양 | 분양전환 | 대지권 (기본: 분양)
  --no-vision Vision 끄고 정규식만 사용
  --append    기존 기본명단에 이어쓰기(덮어쓰기 아님)
  --workers   병렬 워커 수 (기본 5)
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _meta(args) -> dict:
    return {
        "아파트유형": getattr(args, "type", "분양") or "분양",
    }


def cmd_individual(args) -> int:
    from core.registry_engine import process_individual
    from core.run_logger import classify_unit
    unit = process_individual(args.path, _meta(args), use_vision=not args.no_vision)
    status = classify_unit(unit)
    # 내부 필드(_) 제외하고 출력
    printable = {k: v for k, v in unit.items() if not k.startswith("_")}
    print(json.dumps(printable, ensure_ascii=False, indent=2, default=str))
    print(f"\n[분류] {status}  |  신뢰도: {unit.get('_신뢰도', 'N/A')}"
          f"  |  미비: {unit.get('미비서류') or '없음'}", file=sys.stderr)
    return 0 if status != "error" else 1


def cmd_group(args) -> int:
    from core.registry_engine import process_group
    from core.run_logger import RunLogger
    from core.mapping_manager import write_with_mapping

    def progress(done, total, name):
        print(f"  [{done}/{total}] {name}", file=sys.stderr)

    units = process_group(args.root, _meta(args), workers=args.workers,
                          use_vision=not args.no_vision, progress_cb=progress)

    # 실행 로그
    단지 = Path(args.root).name
    log = RunLogger("group", 아파트유형=_meta(args)["아파트유형"], 단지=단지)
    log.add_all(units)
    print(log.text_report(), file=sys.stderr)

    # 엑셀 기입
    if args.mapping and args.out:
        write_with_mapping(args.out if args.append and Path(args.out).exists() else _template_for(args),
                           units, args.mapping, output_path=args.out,
                           append=args.append, backup=True)
    # 로그 파일 저장
    paths = log.write("output")
    print(f"\n실행로그: {paths['txt']}", file=sys.stderr)

    s = log.summary()
    return 0 if s["error"] == 0 else 1


def _template_for(args) -> str:
    """매핑의 템플릿 경로 추론 (out 이 없을 때)."""
    from core.mapping_manager import load_mapping
    m = load_mapping(args.mapping)
    return m["_info"].get("템플릿", args.out)


def main() -> int:
    p = argparse.ArgumentParser(description="개별/집단 등기 자동화 통합 CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("individual", help="개별등기 1세대")
    pi.add_argument("path")
    pi.add_argument("--type", default="분양")
    pi.add_argument("--no-vision", action="store_true")
    pi.set_defaults(func=cmd_individual)

    pg = sub.add_parser("group", help="집단등기 (세대 폴더 n개)")
    pg.add_argument("root")
    pg.add_argument("--type", default="분양")
    pg.add_argument("--mapping", default="")
    pg.add_argument("--out", default="")
    pg.add_argument("--append", action="store_true")
    pg.add_argument("--workers", type=int, default=5)
    pg.add_argument("--no-vision", action="store_true")
    pg.set_defaults(func=cmd_group)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
