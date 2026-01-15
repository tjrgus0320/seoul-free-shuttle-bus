"""
에이전트 6: 파이프라인 오케스트레이터
- 전체 데이터 파이프라인 조율
- 에이전트 순차/병렬 실행
- 에러 처리 및 복구
- 진행 상황 리포팅
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import RAW_DIR, PROCESSED_DIR, LOGS_DIR

from .crawler import DistrictCrawler
from .ocr_parser import PDFOCRParser
from .nlp_extractor import StopExtractor
from .geocoder import GeocodingService
from .validator import JSONValidator

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """데이터 파이프라인 오케스트레이터"""

    def __init__(self):
        self.stages = [
            ("crawler", "자치구 공지 크롤링", DistrictCrawler),
            ("ocr", "PDF OCR 파싱", PDFOCRParser),
            ("nlp", "정류장 NLP 추출", StopExtractor),
            ("geocode", "좌표 변환", GeocodingService),
            ("validate", "JSON 검증", JSONValidator),
        ]

        self.results = {}
        self.errors = []
        self.start_time = None

    def setup_logging(self):
        """로깅 설정"""
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        log_file = LOGS_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

        logging.getLogger().addHandler(file_handler)

        return log_file

    def ensure_directories(self):
        """필요한 디렉토리 생성"""
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

    def run_stage(self, stage_id: str, stage_name: str, agent_class) -> Dict:
        """개별 스테이지 실행"""
        logger.info(f"\n{'=' * 60}")
        logger.info(f"🚀 스테이지: {stage_name}")
        logger.info(f"{'=' * 60}")

        stage_start = time.time()

        try:
            agent = agent_class()
            result = agent.run()

            elapsed = time.time() - stage_start

            return {
                "stage_id": stage_id,
                "stage_name": stage_name,
                "success": True,
                "result": result,
                "elapsed_seconds": round(elapsed, 2),
                "error": None
            }

        except Exception as e:
            elapsed = time.time() - stage_start
            error_msg = str(e)
            logger.error(f"❌ 스테이지 실패: {error_msg}")

            return {
                "stage_id": stage_id,
                "stage_name": stage_name,
                "success": False,
                "result": None,
                "elapsed_seconds": round(elapsed, 2),
                "error": error_msg
            }

    def run_pipeline(
        self,
        stages: List[str] = None,
        skip_stages: List[str] = None,
        continue_on_error: bool = True
    ) -> Dict:
        """전체 파이프라인 실행"""
        self.start_time = time.time()
        log_file = self.setup_logging()
        self.ensure_directories()

        logger.info("=" * 70)
        logger.info("🚌 서울 무료 셔틀버스 데이터 파이프라인 시작")
        logger.info("=" * 70)
        logger.info(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"로그 파일: {log_file}")

        # 실행할 스테이지 결정
        stages_to_run = []
        for stage_id, stage_name, agent_class in self.stages:
            if stages and stage_id not in stages:
                continue
            if skip_stages and stage_id in skip_stages:
                logger.info(f"⏭️ 스킵: {stage_name}")
                continue
            stages_to_run.append((stage_id, stage_name, agent_class))

        # 스테이지 순차 실행
        completed = 0
        failed = 0

        for stage_id, stage_name, agent_class in stages_to_run:
            result = self.run_stage(stage_id, stage_name, agent_class)
            self.results[stage_id] = result

            if result["success"]:
                completed += 1
                logger.info(f"✅ 완료 ({result['elapsed_seconds']}초)")
            else:
                failed += 1
                self.errors.append({
                    "stage": stage_id,
                    "error": result["error"]
                })

                if not continue_on_error:
                    logger.error("파이프라인 중단 (continue_on_error=False)")
                    break

        # 최종 리포트
        total_elapsed = time.time() - self.start_time

        report = {
            "pipeline_status": "completed" if failed == 0 else "completed_with_errors",
            "start_time": datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_elapsed_seconds": round(total_elapsed, 2),
            "stages_completed": completed,
            "stages_failed": failed,
            "stages": self.results,
            "errors": self.errors,
            "log_file": str(log_file)
        }

        # 리포트 저장
        report_path = PROCESSED_DIR / "pipeline_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        # 최종 로그
        logger.info("\n" + "=" * 70)
        logger.info("📊 파이프라인 실행 완료")
        logger.info("=" * 70)
        logger.info(f"총 소요 시간: {round(total_elapsed, 1)}초")
        logger.info(f"성공: {completed}개, 실패: {failed}개")

        if self.errors:
            logger.warning("\n⚠️ 발생한 오류:")
            for err in self.errors:
                logger.warning(f"  - [{err['stage']}] {err['error']}")

        logger.info(f"\n리포트 저장: {report_path}")

        return report

    def run_quick(self) -> Dict:
        """빠른 실행 (OCR 스킵)"""
        return self.run_pipeline(skip_stages=["ocr"])

    def run_full(self) -> Dict:
        """전체 실행"""
        return self.run_pipeline()

    def run_update(self) -> Dict:
        """업데이트 실행 (크롤링 + NLP + 지오코딩 + 검증)"""
        return self.run_pipeline(skip_stages=["ocr"])

    def run_validate_only(self) -> Dict:
        """검증만 실행"""
        return self.run_pipeline(stages=["validate"])


def main():
    """CLI 진입점"""
    import argparse

    parser = argparse.ArgumentParser(
        description="서울 무료 셔틀버스 데이터 파이프라인"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "quick", "update", "validate"],
        default="quick",
        help="실행 모드 (기본: quick)"
    )
    parser.add_argument(
        "--stages",
        nargs="+",
        choices=["crawler", "ocr", "nlp", "geocode", "validate"],
        help="실행할 스테이지 지정"
    )
    parser.add_argument(
        "--skip",
        nargs="+",
        choices=["crawler", "ocr", "nlp", "geocode", "validate"],
        help="스킵할 스테이지"
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="오류 발생 시 중단"
    )

    args = parser.parse_args()

    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    orchestrator = PipelineOrchestrator()

    if args.stages:
        result = orchestrator.run_pipeline(
            stages=args.stages,
            continue_on_error=not args.stop_on_error
        )
    elif args.mode == "full":
        result = orchestrator.run_full()
    elif args.mode == "update":
        result = orchestrator.run_update()
    elif args.mode == "validate":
        result = orchestrator.run_validate_only()
    else:
        result = orchestrator.run_quick()

    # 종료 코드
    if result.get("stages_failed", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
