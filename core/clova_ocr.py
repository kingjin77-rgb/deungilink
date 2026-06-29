"""
Clova OCR 래퍼 — NAVER Cloud Clova OCR API
PDF → 페이지별 이미지 → Clova OCR → 텍스트

인증 방식 A (권장): NAVER Cloud Platform Clova OCR Domain
  config.ini [clova]
    invoke_url = https://xxxx.apigw.ntruss.com/custom/v1/xxxx/general
    secret_key = xxxxxxxx

인증 방식 B: NAVER Open API (무료, 일 1,000건)
  config.ini [clova]
    client_id     = xxxxxxxx
    client_secret = xxxxxxxx
"""

import requests, base64, json, io, time, uuid, configparser
from pathlib import Path


class ClovaOCR:

    def __init__(self, cfg_path: str = None):
        cfg = configparser.ConfigParser()
        if cfg_path:
            cfg.read(cfg_path, encoding="utf-8")

        # 방식 A: Clova OCR Domain (NAVER Cloud)
        self.invoke_url  = cfg.get("clova", "invoke_url",  fallback="").strip()
        self.secret_key  = cfg.get("clova", "secret_key",  fallback="").strip()

        # 방식 B: NAVER Open API
        self.client_id   = cfg.get("clova", "client_id",     fallback="").strip()
        self.client_sec  = cfg.get("clova", "client_secret",  fallback="").strip()

        if not self.invoke_url and not self.client_id:
            raise ValueError(
                "Clova OCR 인증 정보 없음.\n"
                "config.ini [clova] 섹션에 invoke_url+secret_key 또는 "
                "client_id+client_secret 입력 필요."
            )

    # ── 방식 A: Domain API ────────────────────────────────────────────
    def _call_domain(self, b64: str, fmt: str) -> str:
        payload = {
            "version": "V2",
            "requestId": str(uuid.uuid4()),
            "timestamp": int(time.time() * 1000),
            "lang": "ko",
            "images": [{"format": fmt, "name": "page", "data": b64}],
            "enableTableDetect": True
        }
        r = requests.post(
            self.invoke_url,
            headers={"X-OCR-SECRET": self.secret_key,
                     "Content-Type": "application/json"},
            json=payload, timeout=30
        )
        r.raise_for_status()
        return self._parse_domain(r.json())

    def _parse_domain(self, data: dict) -> str:
        lines = []
        for img in data.get("images", []):
            for field in img.get("fields", []):
                lines.append(field.get("inferText", ""))
                if field.get("lineBreak"):
                    lines.append("\n")
        return " ".join(lines)

    # ── 방식 B: Open API ─────────────────────────────────────────────
    def _call_openapi(self, img_bytes: bytes, fmt: str) -> str:
        r = requests.post(
            "https://openapi.naver.com/v1/vision/ocr",
            headers={
                "X-Naver-Client-Id": self.client_id,
                "X-Naver-Client-Secret": self.client_sec
            },
            files={"image": (f"page.{fmt}", img_bytes, f"image/{fmt}")},
            timeout=30
        )
        r.raise_for_status()
        data = r.json()
        lines = []
        for field in data.get("images", [{}])[0].get("fields", []):
            lines.append(field.get("inferText", ""))
            if field.get("lineBreak"):
                lines.append("\n")
        return " ".join(lines)

    # ── 이미지 bytes → 텍스트 ─────────────────────────────────────────
    def ocr_bytes(self, img_bytes: bytes, fmt: str = "jpg") -> str:
        if self.invoke_url and self.secret_key:
            b64 = base64.b64encode(img_bytes).decode()
            return self._call_domain(b64, fmt)
        return self._call_openapi(img_bytes, fmt)

    # ── PDF → 전체 텍스트 ─────────────────────────────────────────────
    def ocr_pdf(self, pdf_path: str, dpi: int = 150) -> str:
        from pdf2image import convert_from_path
        imgs = convert_from_path(pdf_path, dpi=dpi)
        pages = []
        for i, img in enumerate(imgs):
            buf = io.BytesIO()
            img.convert("RGB").save(buf, "JPEG", quality=90)
            text = self.ocr_bytes(buf.getvalue(), "jpg")
            pages.append(f"=== 페이지 {i+1} ===\n{text.strip()}")
            time.sleep(0.05)  # rate limit 방지
        return "\n\n".join(pages)
