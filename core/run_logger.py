"""
구조적 실행 로거 (run_logger)
=============================
처리 결과를 세대별로 성공/부분/오류로 분류하고, 실행 로그(txt+json)와
요약을 남긴다. 기존의 광범위한 'except: pass' 침묵 대신, 무엇이
실패·미비였는지 실무자가 추적할 수 있게 한다.

분류:
  ok      — 핵심 필드 완비, 미비서류 없음, 신뢰도 충분
  partial — 미비서류 있음 / 핵심 필드(성명·동·호) 누락 / 낮은 신뢰도
  error   — 처리 중 예외(_오류)
"""

import json
from datetime import datetime
from pathlib import Path

# 부분 처리로 볼 신뢰도 임계값 (Vision confidence)
LOW_CONFIDENCE = 0.6


def classify_unit(unit: dict) -> str:
    """세대 처리 결과를 ok/partial/error 로 분류."""
    if not unit:
        return "error"
    if unit.get("_오류"):
        return "error"

    미비 = str(unit.get("미비서류", "") or "").strip()
    성명 = str(unit.get("성명", "") or "").strip()
    동   = str(unit.get("동", "") or "").strip()
    호   = str(unit.get("호", "") or "").strip()
    신뢰도 = unit.get("_신뢰도")

    if 미비:
        return "partial"
    if not 성명 or not (동 and 호):
        return "partial"
    if 신뢰도 is not None and 신뢰도 < LOW_CONFIDENCE:
        return "partial"
    return "ok"


class RunLogger:
    """한 번의 처리 실행에 대한 세대별 로그 누적기."""

    def __init__(self, name: str = "run", 아파트유형: str = "", 단지: str = ""):
        self.name = name
        self.아파트유형 = 아파트유형
        self.단지 = 단지
        self.started = datetime.now()
        self.entries = []  # [{세대, status, 성명, 동호수, 미비서류, 신뢰도, 오류}]

    def add(self, unit: dict) -> str:
        """세대 결과 1건 기록. 분류 status 반환."""
        status = classify_unit(unit)
        self.entries.append({
            "세대":     unit.get("_세대", "") or unit.get("동호수", ""),
            "status":   status,
            "성명":     unit.get("성명", ""),
            "동호수":   unit.get("동호수", ""),
            "미비서류": unit.get("미비서류", ""),
            "신뢰도":   unit.get("_신뢰도"),
            "오류":     unit.get("_오류", ""),
        })
        return status

    def add_all(self, units: list):
        for u in units:
            self.add(u)

    def summary(self) -> dict:
        c = {"total": len(self.entries), "ok": 0, "partial": 0, "error": 0}
        for e in self.entries:
            c[e["status"]] = c.get(e["status"], 0) + 1
        return c

    def review_needed(self) -> list:
        """검토가 필요한(partial/error) 항목만."""
        return [e for e in self.entries if e["status"] in ("partial", "error")]

    def text_report(self) -> str:
        s = self.summary()
        dur = (datetime.now() - self.started).total_seconds()
        lines = [
            "═" * 50,
            f" 등기자동화 실행 로그 — {self.name}",
            "═" * 50,
            f"단지: {self.단지}   유형: {self.아파트유형}",
            f"시작: {self.started.strftime('%Y-%m-%d %H:%M:%S')}   소요: {dur:.1f}초",
            "",
            f"전체 {s['total']}건  |  완료 {s['ok']}  |  부분/검토 {s['partial']}  |  오류 {s['error']}",
            "",
            "── 검토 필요 세대 ──",
        ]
        review = self.review_needed()
        if not review:
            lines.append("  (없음 — 전건 정상)")
        else:
            for e in review:
                tag = "⚠부분" if e["status"] == "partial" else "✗오류"
                note = e["오류"] or e["미비서류"] or "핵심필드 누락"
                conf = f" (신뢰도 {e['신뢰도']})" if e["신뢰도"] is not None else ""
                lines.append(f"  [{tag}] {e['세대']} / {e['성명']}{conf} — {note}")
        lines.append("═" * 50)
        return "\n".join(lines)

    def write(self, out_dir: str = "output") -> dict:
        """txt + json 실행 로그 저장. 저장 경로 dict 반환."""
        outp = Path(out_dir)
        outp.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        txt_path = outp / f"실행로그_{stamp}.txt"
        json_path = outp / f"실행로그_{stamp}.json"

        txt_path.write_text(self.text_report(), encoding="utf-8")
        json_path.write_text(
            json.dumps({
                "name": self.name,
                "단지": self.단지,
                "아파트유형": self.아파트유형,
                "started": self.started.isoformat(),
                "summary": self.summary(),
                "entries": self.entries,
            }, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8")

        return {"txt": str(txt_path), "json": str(json_path)}
