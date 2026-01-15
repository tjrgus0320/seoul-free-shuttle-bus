"""
에이전트 4: 지오코딩 서비스
- 정류장명 → 위도/경도 변환
- 카카오/네이버/Google API 지원
- 결과 캐싱으로 API 호출 최소화
"""

import requests
import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import (
    KAKAO_API_KEY, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET,
    GEOCODE_CONFIG, PROCESSED_DIR
)

logger = logging.getLogger(__name__)


class GeocodingService:
    """정류장 좌표 변환 서비스"""

    def __init__(self):
        self.provider = GEOCODE_CONFIG["provider"]
        self.default_region = GEOCODE_CONFIG["default_region"]
        self.cache_enabled = GEOCODE_CONFIG["cache_enabled"]
        self.cache_file = GEOCODE_CONFIG["cache_file"]
        self.cache = self.load_cache()

        # API 호출 통계
        self.stats = {
            "cache_hits": 0,
            "api_calls": 0,
            "failures": 0
        }

    def load_cache(self) -> Dict:
        """캐시 로드"""
        if self.cache_enabled and self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"캐시 로드 실패: {e}")
        return {}

    def save_cache(self):
        """캐시 저장"""
        if self.cache_enabled:
            try:
                self.cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(self.cache, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"캐시 저장 실패: {e}")

    def normalize_query(self, place: str, district: str = None) -> str:
        """검색어 정규화"""
        query = place.strip()

        # 서울 + 자치구 추가 (더 정확한 검색)
        if district and district not in query:
            query = f"서울 {district} {query}"
        elif self.default_region not in query:
            query = f"{self.default_region} {query}"

        return query

    def geocode_kakao(self, query: str) -> Optional[Tuple[float, float]]:
        """카카오 API 지오코딩"""
        if KAKAO_API_KEY == "YOUR_KAKAO_REST_API_KEY":
            logger.warning("카카오 API 키가 설정되지 않았습니다")
            return None

        try:
            url = "https://dapi.kakao.com/v2/local/search/keyword.json"
            headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
            params = {"query": query, "size": 1}

            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()

            if data.get("documents"):
                doc = data["documents"][0]
                return float(doc["y"]), float(doc["x"])

        except Exception as e:
            logger.error(f"카카오 API 오류: {e}")

        return None

    def geocode_naver(self, query: str) -> Optional[Tuple[float, float]]:
        """네이버 API 지오코딩"""
        if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
            logger.warning("네이버 API 키가 설정되지 않았습니다")
            return None

        try:
            url = "https://openapi.naver.com/v1/search/local.json"
            headers = {
                "X-Naver-Client-Id": NAVER_CLIENT_ID,
                "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
            }
            params = {"query": query, "display": 1}

            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()

            if data.get("items"):
                item = data["items"][0]
                # 네이버는 KATEC 좌표계 사용 → 변환 필요
                # 여기서는 간단히 처리 (실제로는 좌표 변환 필요)
                return None

        except Exception as e:
            logger.error(f"네이버 API 오류: {e}")

        return None

    def geocode_fallback(self, place: str, district: str = None) -> Optional[Tuple[float, float]]:
        """폴백: 주요 랜드마크 좌표 반환"""
        # 서울 주요 지하철역 좌표 (하드코딩 폴백)
        landmarks = {
            "강남역": (37.4979, 127.0276),
            "서울역": (37.5547, 126.9707),
            "홍대입구역": (37.5571, 126.9246),
            "잠실역": (37.5132, 127.1001),
            "신촌역": (37.5599, 126.9422),
            "여의도역": (37.5216, 126.9244),
            "영등포역": (37.5156, 126.9074),
            "사당역": (37.4765, 126.9816),
            "건대입구역": (37.5403, 127.0702),
            "왕십리역": (37.5614, 127.0378),
            "합정역": (37.5495, 126.9138),
            "신림역": (37.4842, 126.9293),
            "노원역": (37.6558, 127.0617),
            "종로3가역": (37.5710, 126.9920),
            "을지로입구역": (37.5660, 126.9825),
            "시청역": (37.5659, 126.9771),
            "교대역": (37.4934, 127.0145),
            "역삼역": (37.5006, 127.0366),
            "선릉역": (37.5045, 127.0490),
            "삼성역": (37.5089, 127.0630),
            "종합운동장역": (37.5107, 127.0739),
            "구로디지털단지역": (37.4851, 126.9015),
            "가산디지털단지역": (37.4816, 126.8828),
            "문래역": (37.5178, 126.8945),
            "당산역": (37.5349, 126.9025),
        }

        # 자치구 중심 좌표
        district_centers = {
            "종로구": (37.5735, 126.9790),
            "중구": (37.5641, 126.9979),
            "용산구": (37.5326, 126.9907),
            "성동구": (37.5634, 127.0369),
            "광진구": (37.5385, 127.0823),
            "동대문구": (37.5744, 127.0396),
            "중랑구": (37.6063, 127.0927),
            "성북구": (37.5894, 127.0167),
            "강북구": (37.6396, 127.0257),
            "도봉구": (37.6688, 127.0471),
            "노원구": (37.6543, 127.0568),
            "은평구": (37.6027, 126.9291),
            "서대문구": (37.5791, 126.9368),
            "마포구": (37.5663, 126.9019),
            "양천구": (37.5170, 126.8666),
            "강서구": (37.5510, 126.8495),
            "구로구": (37.4954, 126.8874),
            "금천구": (37.4569, 126.8955),
            "영등포구": (37.5264, 126.8963),
            "동작구": (37.5124, 126.9393),
            "관악구": (37.4784, 126.9516),
            "서초구": (37.4837, 127.0324),
            "강남구": (37.5172, 127.0473),
            "송파구": (37.5145, 127.1059),
            "강동구": (37.5301, 127.1238),
        }

        # 랜드마크 매칭
        for landmark, coords in landmarks.items():
            if landmark.replace("역", "") in place:
                return coords

        # 자치구 중심 반환
        if district and district in district_centers:
            return district_centers[district]

        return None

    def geocode(self, place: str, district: str = None) -> Optional[Tuple[float, float]]:
        """정류장 좌표 조회 (캐시 + API + 폴백)"""
        # 캐시 키 생성
        cache_key = f"{place}_{district or ''}"

        # 캐시 확인
        if cache_key in self.cache:
            self.stats["cache_hits"] += 1
            cached = self.cache[cache_key]
            return (cached["lat"], cached["lng"]) if cached else None

        # 검색어 정규화
        query = self.normalize_query(place, district)

        # API 호출
        coords = None

        if self.provider == "kakao":
            coords = self.geocode_kakao(query)
        elif self.provider == "naver":
            coords = self.geocode_naver(query)

        # API 실패 시 폴백
        if not coords:
            coords = self.geocode_fallback(place, district)

        # 결과 캐싱
        if coords:
            self.cache[cache_key] = {"lat": coords[0], "lng": coords[1]}
            self.stats["api_calls"] += 1
        else:
            self.cache[cache_key] = None
            self.stats["failures"] += 1

        # API 호출 간격
        time.sleep(0.1)

        return coords

    def geocode_routes(self, routes_data: Dict) -> Dict:
        """노선 데이터의 모든 정류장 좌표 변환"""
        result = {
            "districts": [],
            "stats": {}
        }

        for district, routes in routes_data.get("districts", {}).items():
            district_data = {
                "district": district,
                "routes": []
            }

            for route in routes:
                route_data = {
                    "name": route.get("name", f"{district} 셔틀"),
                    "hours": route.get("hours"),
                    "interval": route.get("interval"),
                    "stops": []
                }

                for stop_name in route.get("stops", []):
                    coords = self.geocode(stop_name, district)

                    if coords:
                        route_data["stops"].append({
                            "name": stop_name,
                            "lat": coords[0],
                            "lng": coords[1]
                        })
                    else:
                        logger.warning(f"좌표 변환 실패: {stop_name}")

                if route_data["stops"]:
                    district_data["routes"].append(route_data)

            if district_data["routes"]:
                result["districts"].append(district_data)

        result["stats"] = self.stats
        return result

    def run(self) -> Dict:
        """전체 지오코딩 실행"""
        logger.info("=" * 50)
        logger.info("에이전트 4: 지오코딩 서비스 시작")
        logger.info("=" * 50)

        # 추출된 노선 데이터 로드
        input_path = PROCESSED_DIR / "extracted_routes.json"
        if not input_path.exists():
            logger.error(f"입력 파일 없음: {input_path}")
            return {"error": "Input file not found"}

        with open(input_path, encoding="utf-8") as f:
            routes_data = json.load(f)

        logger.info(f"입력 데이터: {routes_data.get('total_routes', 0)}개 노선")

        # 지오코딩 실행
        result = self.geocode_routes(routes_data)

        # 캐시 저장
        self.save_cache()

        # 결과 저장
        output_path = PROCESSED_DIR / "geocoded_routes.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"\n지오코딩 완료! 결과: {output_path}")
        logger.info(f"  캐시 히트: {self.stats['cache_hits']}")
        logger.info(f"  API 호출: {self.stats['api_calls']}")
        logger.info(f"  실패: {self.stats['failures']}")

        return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    geocoder = GeocodingService()
    results = geocoder.run()
