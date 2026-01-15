"""
에이전트 2: PDF OCR 파서
- PDF → 이미지 변환
- Tesseract OCR로 텍스트 추출
- 이미지 전처리로 인식률 향상
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import OCR_CONFIG, RAW_DIR, PROCESSED_DIR

logger = logging.getLogger(__name__)

# 선택적 임포트 (설치 안 된 경우 처리)
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image 미설치 - PDF 처리 불가")

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    TESSERACT_AVAILABLE = True

    # Windows Tesseract 경로 설정
    if os.path.exists(OCR_CONFIG["tesseract_path"]):
        pytesseract.pytesseract.tesseract_cmd = OCR_CONFIG["tesseract_path"]
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract 미설치 - OCR 불가")


class PDFOCRParser:
    """PDF 문서 OCR 파서"""

    def __init__(self):
        self.dpi = OCR_CONFIG["dpi"]
        self.language = OCR_CONFIG["language"]
        self.results = []

    def check_dependencies(self) -> Tuple[bool, List[str]]:
        """의존성 확인"""
        missing = []

        if not PDF2IMAGE_AVAILABLE:
            missing.append("pdf2image")
        if not TESSERACT_AVAILABLE:
            missing.append("pytesseract, Pillow")

        # Tesseract 설치 확인
        if TESSERACT_AVAILABLE:
            try:
                pytesseract.get_tesseract_version()
            except Exception:
                missing.append("Tesseract-OCR (시스템 설치 필요)")

        return len(missing) == 0, missing

    def preprocess_image(self, image: "Image.Image") -> "Image.Image":
        """이미지 전처리로 OCR 인식률 향상"""
        # 그레이스케일 변환
        if image.mode != "L":
            image = image.convert("L")

        # 대비 향상
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

        # 샤프닝
        image = image.filter(ImageFilter.SHARPEN)

        # 이진화 (흑백)
        threshold = 128
        image = image.point(lambda x: 255 if x > threshold else 0, mode="1")

        return image

    def pdf_to_images(self, pdf_path: Path) -> List["Image.Image"]:
        """PDF를 이미지로 변환"""
        if not PDF2IMAGE_AVAILABLE:
            logger.error("pdf2image가 설치되지 않았습니다")
            return []

        try:
            images = convert_from_path(
                str(pdf_path),
                dpi=self.dpi,
                fmt="png"
            )
            logger.info(f"PDF 변환 완료: {len(images)}페이지")
            return images
        except Exception as e:
            logger.error(f"PDF 변환 실패: {e}")
            return []

    def extract_text_from_image(self, image: "Image.Image") -> str:
        """이미지에서 텍스트 추출"""
        if not TESSERACT_AVAILABLE:
            logger.error("pytesseract가 설치되지 않았습니다")
            return ""

        try:
            # 이미지 전처리
            processed = self.preprocess_image(image.copy())

            # OCR 설정
            custom_config = f"--psm {OCR_CONFIG['psm']} --oem 3"

            # 텍스트 추출
            text = pytesseract.image_to_string(
                processed,
                lang=self.language,
                config=custom_config
            )

            return text.strip()
        except Exception as e:
            logger.error(f"OCR 실패: {e}")
            return ""

    def parse_pdf(self, pdf_path: Path) -> Dict:
        """PDF 파일 전체 파싱"""
        logger.info(f"PDF 파싱 시작: {pdf_path.name}")

        result = {
            "filename": pdf_path.name,
            "filepath": str(pdf_path),
            "pages": [],
            "full_text": "",
            "success": False,
            "error": None
        }

        # 의존성 확인
        ready, missing = self.check_dependencies()
        if not ready:
            result["error"] = f"누락된 의존성: {', '.join(missing)}"
            logger.error(result["error"])
            return result

        # PDF → 이미지
        images = self.pdf_to_images(pdf_path)
        if not images:
            result["error"] = "PDF 이미지 변환 실패"
            return result

        # 각 페이지 OCR
        all_text = []
        for i, image in enumerate(images):
            logger.info(f"  페이지 {i + 1}/{len(images)} OCR 중...")

            page_text = self.extract_text_from_image(image)

            result["pages"].append({
                "page_number": i + 1,
                "text": page_text,
                "char_count": len(page_text)
            })

            all_text.append(page_text)

        result["full_text"] = "\n\n--- 페이지 구분 ---\n\n".join(all_text)
        result["success"] = True
        result["total_chars"] = len(result["full_text"])

        logger.info(f"  완료! 총 {result['total_chars']}자 추출")

        return result

    def parse_image(self, image_path: Path) -> Dict:
        """이미지 파일 직접 파싱"""
        logger.info(f"이미지 파싱: {image_path.name}")

        result = {
            "filename": image_path.name,
            "filepath": str(image_path),
            "text": "",
            "success": False,
            "error": None
        }

        if not TESSERACT_AVAILABLE:
            result["error"] = "pytesseract 미설치"
            return result

        try:
            image = Image.open(image_path)
            result["text"] = self.extract_text_from_image(image)
            result["success"] = True
            result["char_count"] = len(result["text"])
        except Exception as e:
            result["error"] = str(e)

        return result

    def parse_all_pdfs(self, directory: Path = RAW_DIR) -> List[Dict]:
        """디렉토리 내 모든 PDF 파싱"""
        results = []

        pdf_files = list(directory.glob("*.pdf"))
        logger.info(f"발견된 PDF 파일: {len(pdf_files)}개")

        for pdf_path in pdf_files:
            result = self.parse_pdf(pdf_path)
            results.append(result)

            # 개별 결과 저장
            output_path = PROCESSED_DIR / f"{pdf_path.stem}_ocr.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

        return results

    def run(self) -> Dict:
        """전체 OCR 파싱 실행"""
        logger.info("=" * 50)
        logger.info("에이전트 2: PDF OCR 파서 시작")
        logger.info("=" * 50)

        # 의존성 확인
        ready, missing = self.check_dependencies()
        if not ready:
            logger.error(f"누락된 의존성: {', '.join(missing)}")
            logger.info("\n설치 방법:")
            logger.info("  pip install pdf2image pytesseract Pillow")
            logger.info("  + Tesseract-OCR 시스템 설치 필요")
            logger.info("  Windows: https://github.com/UB-Mannheim/tesseract/wiki")

            return {
                "success": False,
                "error": f"Missing dependencies: {missing}",
                "results": []
            }

        # PDF 파싱
        results = self.parse_all_pdfs()

        # 전체 결과 저장
        output = {
            "total_files": len(results),
            "successful": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "results": results
        }

        output_path = PROCESSED_DIR / "ocr_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"\nOCR 완료! 결과: {output_path}")
        logger.info(f"  성공: {output['successful']}개, 실패: {output['failed']}개")

        return output


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    parser = PDFOCRParser()
    results = parser.run()
