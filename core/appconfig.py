"""
중앙 설정 접근 모듈 (appconfig)
===============================
config.ini 의 API 키 · 모델 ID 를 한 곳에서 읽어, 모듈마다 제각각이던
[api]/[claude] 이중 키 관리와 모델 ID 불일치를 제거한다.

기존 코드 호환:
- 키는 [claude] → [api] 순으로 탐색 (기존 폴백 규칙 유지)
- 모델은 [claude] model → DEFAULT_MODEL

사용:
    from core.appconfig import get_api_key, get_model, get_cfg
"""

import configparser
from pathlib import Path

# ── 단일 기본 모델 ID (config 미설정 시) ─────────────────────────────────
#  실제 사용할 Anthropic 모델 ID. config.ini 의 [claude] model 로 재정의 가능.
DEFAULT_MODEL = "claude-sonnet-4-6"

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.ini"

# 플레이스홀더로 취급할 값 (실제 키 아님)
_PLACEHOLDERS = ("", "여기에", "sk-ant-...", "YOUR_ANTHROPIC_API_KEY_HERE")


def get_cfg() -> configparser.ConfigParser:
    """config.ini 를 읽어 ConfigParser 반환 (없으면 빈 파서)."""
    cfg = configparser.ConfigParser()
    try:
        cfg.read(str(_CONFIG_PATH), encoding="utf-8")
    except Exception:
        pass
    return cfg


def _is_real(val: str) -> bool:
    v = (val or "").strip()
    return bool(v) and not any(p and p in v for p in _PLACEHOLDERS if p) and v not in _PLACEHOLDERS


def get_api_key(cfg: configparser.ConfigParser = None) -> str:
    """
    Anthropic API 키 반환. [claude] api_key 우선, 없으면 [api] api_key.
    플레이스홀더/빈값이면 "" 반환.
    """
    cfg = cfg or get_cfg()
    for section in ("claude", "api"):
        k = cfg.get(section, "api_key", fallback="").strip()
        if _is_real(k):
            return k
    return ""


def get_model(cfg: configparser.ConfigParser = None) -> str:
    """사용할 모델 ID 반환. [claude] model → DEFAULT_MODEL."""
    cfg = cfg or get_cfg()
    m = cfg.get("claude", "model", fallback="").strip()
    return m if m else DEFAULT_MODEL


def has_api_key(cfg: configparser.ConfigParser = None) -> bool:
    return bool(get_api_key(cfg))
