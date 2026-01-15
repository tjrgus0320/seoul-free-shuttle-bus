"""
에이전트 3: NLP 정류장 추출기
- OCR 텍스트에서 정류장명 추출
- 노선 정보 구조화
- 불필요한 텍스트 필터링
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import STOP_PATTERNS, SEOUL_DISTRICTS, PROCESSED_DIR

logger = logging.getLogger(__name__)


class StopExtractor:
    """정류장 및 노선 정보 추출기"""

    def __init__(self):
        self.stop_keywords = STOP_PATTERNS["keywords"]
        self.exclude_keywords = STOP_PATTERNS["exclude"]
        self.districts = SEOUL_DISTRICTS

        # 정류장 패턴 정규식
        self.stop_pattern = re.compile(
            r"([가-힣]{2,15}(?:역|정류장|사거리|삼거리|오거리|주민센터|구청|시장|공원|학교|병원|아파트|마을|입구|앞|건너편?)\s*\d*번?\s*(?:출구)?)"
        )

        # 시간 패턴
        self.time_pattern = re.compile(
            r"(\d{1,2})\s*[:시]\s*(\d{2})?\s*[~\-]\s*(\d{1,2})\s*[:시]\s*(\d{2})?"
        )

        # 배차간격 패턴
        self.interval_pattern = re.compile(
            r"(\d+)\s*[~\-]?\s*(\d+)?\s*분\s*(?:간격|배차)?"
        )

        # 노선명 패턴
        self.route_name_pattern = re.compile(
            r"([가-힣]+\s*(?:셔틀|순환|노선|버스)?\s*\d*\s*(?:호선|번)?)"
        )

    def clean_text(self, text: str) -> str:
        """텍스트 정제"""
        # 여러 공백을 하나로
        text = re.sub(r"\s+", " ", text)
        # 특수문자 정리
        text = re.sub(r"[^\w\s가-힣\d:~\-→↔]", " ", text)
        return text.strip()

    def extract_stops(self, text: str) -> List[str]:
        """텍스트에서 정류장명 추출"""
        stops = []
        cleaned = self.clean_text(text)

        # 정규식 매칭
        matches = self.stop_pattern.findall(cleaned)
        for match in matches:
            stop_name = match.strip()
            if self.is_valid_stop(stop_name):
                stops.append(stop_name)

        # 키워드 기반 추출 (정규식 놓친 것)
        lines = text.split("\n")
        for line in lines:
            line = self.clean_text(line)

            # 제외 키워드 필터링
            if any(ex in line for ex in self.exclude_keywords):
                continue

            # 정류장 키워드 포함 여부
            for keyword in self.stop_keywords:
                if keyword in line:
                    # 해당 부분 추출
                    parts = re.split(r"[,\s→↔\-]", line)
                    for part in parts:
                        part = part.strip()
                        if keyword in part and self.is_valid_stop(part):
                            if part not in stops:
                                stops.append(part)

        return self.deduplicate_stops(stops)

    def is_valid_stop(self, stop_name: str) -> bool:
        """유효한 정류장명인지 확인"""
        if not stop_name or len(stop_name) < 2:
            return False

        # 제외 키워드 포함 여부
        if any(ex in stop_name for ex in self.exclude_keywords):
            return False

        # 숫자만 있는 경우
        if stop_name.isdigit():
            return False

        # 너무 짧거나 긴 경우
        if len(stop_name) < 3 or len(stop_name) > 30:
            return False

        # 정류장 키워드 포함 여부
        has_keyword = any(kw in stop_name for kw in self.stop_keywords)

        return has_keyword

    def deduplicate_stops(self, stops: List[str]) -> List[str]:
        """중복 정류장 제거 (유사 이름 포함)"""
        unique = []
        seen_normalized = set()

        for stop in stops:
            # 정규화 (공백, 숫자 제거)
            normalized = re.sub(r"[\s\d]", "", stop)

            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                unique.append(stop)

        return unique

    def extract_time_info(self, text: str) -> Optional[str]:
        """운행 시간 추출"""
        match = self.time_pattern.search(text)
        if match:
            start_h = match.group(1).zfill(2)
            start_m = match.group(2) or "00"
            end_h = match.group(3).zfill(2)
            end_m = match.group(4) or "00"
            return f"{start_h}:{start_m}~{end_h}:{end_m}"
        return None

    def extract_interval(self, text: str) -> Optional[str]:
        """배차 간격 추출"""
        match = self.interval_pattern.search(text)
        if match:
            min_interval = match.group(1)
            max_interval = match.group(2)
            if max_interval:
                return f"{min_interval}~{max_interval}분"
            return f"{min_interval}분"
        return None

    def extract_route_name(self, text: str, district: str) -> str:
        """노선명 추출"""
        match = self.route_name_pattern.search(text)
        if match:
            return match.group(1).strip()
        return f"{district} 셔틀"

    def identify_district(self, text: str) -> Optional[str]:
        """텍스트에서 자치구 식별"""
        for district in self.districts.keys():
            if district in text:
                return district

            # 키워드로 매칭
            for keyword in self.districts[district]["keywords"]:
                if keyword in text:
                    return district

        return None

    def parse_route_block(self, text: str, district: str = None) -> Dict:
        """텍스트 블록에서 노선 정보 추출"""
        if not district:
            district = self.identify_district(text) or "미확인"

        return {
            "district": district,
            "name": self.extract_route_name(text, district),
            "hours": self.extract_time_info(text),
            "interval": self.extract_interval(text),
            "stops": self.extract_stops(text),
            "raw_text": text[:500]  # 원본 텍스트 일부 보관
        }

    def process_ocr_results(self, ocr_results: Dict) -> List[Dict]:
        """OCR 결과 처리"""
        routes = []

        for result in ocr_results.get("results", []):
            if not result.get("success"):
                continue

            full_text = result.get("full_text", "")

            # 자치구별로 분리
            district_blocks = self.split_by_district(full_text)

            for district, block_text in district_blocks.items():
                route = self.parse_route_block(block_text, district)
                if route["stops"]:  # 정류장이 있는 경우만
                    route["source_file"] = result.get("filename")
                    routes.append(route)

        return routes

    def split_by_district(self, text: str) -> Dict[str, str]:
        """텍스트를 자치구별로 분리"""
        blocks = {}
        current_district = None
        current_lines = []

        for line in text.split("\n"):
            # 새 자치구 발견
            for district in self.districts.keys():
                if district in line:
                    # 이전 블록 저장
                    if current_district and current_lines:
                        blocks[current_district] = "\n".join(current_lines)

                    current_district = district
                    current_lines = [line]
                    break
            else:
                # 현재 블록에 추가
                if current_district:
                    current_lines.append(line)

        # 마지막 블록 저장
        if current_district and current_lines:
            blocks[current_district] = "\n".join(current_lines)

        return blocks

    def process_crawl_results(self, crawl_results: Dict) -> List[Dict]:
        """크롤링 결과 처리"""
        routes = []

        # 메인 결과
        for result in crawl_results.get("main_results", []):
            for route_data in result.get("routes", []):
                route = self.parse_route_block(
                    route_data.get("raw_text", ""),
                    route_data.get("district")
                )
                if route["stops"]:
                    route["source_url"] = route_data.get("source")
                    routes.append(route)

        # 자치구 결과
        for result in crawl_results.get("district_results", []):
            for route_data in result.get("routes", []):
                route = self.parse_route_block(
                    route_data.get("raw_text", ""),
                    route_data.get("district")
                )
                if route["stops"]:
                    route["source_url"] = result.get("url")
                    routes.append(route)

        return routes

    def run(self) -> Dict:
        """전체 NLP 추출 실행"""
        logger.info("=" * 50)
        logger.info("에이전트 3: NLP 정류장 추출기 시작")
        logger.info("=" * 50)

        all_routes = []

        # OCR 결과 처리
        ocr_path = PROCESSED_DIR / "ocr_results.json"
        if ocr_path.exists():
            logger.info("OCR 결과 처리 중...")
            with open(ocr_path, encoding="utf-8") as f:
                ocr_data = json.load(f)
            routes = self.process_ocr_results(ocr_data)
            all_routes.extend(routes)
            logger.info(f"  OCR에서 {len(routes)}개 노선 추출")

        # 크롤링 결과 처리
        crawl_path = PROCESSED_DIR.parent / "data" / "raw" / "crawl_results.json"
        if crawl_path.exists():
            logger.info("크롤링 결과 처리 중...")
            with open(crawl_path, encoding="utf-8") as f:
                crawl_data = json.load(f)
            routes = self.process_crawl_results(crawl_data)
            all_routes.extend(routes)
            logger.info(f"  크롤링에서 {len(routes)}개 노선 추출")

        # 자치구별 그룹화
        by_district = defaultdict(list)
        for route in all_routes:
            by_district[route["district"]].append(route)

        # 결과 저장
        output = {
            "total_routes": len(all_routes),
            "districts": dict(by_district),
            "summary": {
                "district_count": len(by_district),
                "total_stops": sum(len(r["stops"]) for r in all_routes)
            }
        }

        output_path = PROCESSED_DIR / "extracted_routes.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"\nNLP 추출 완료! 결과: {output_path}")
        logger.info(f"  총 노선: {output['total_routes']}개")
        logger.info(f"  자치구: {output['summary']['district_count']}개")
        logger.info(f"  정류장: {output['summary']['total_stops']}개")

        return output


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    extractor = StopExtractor()
    results = extractor.run()
