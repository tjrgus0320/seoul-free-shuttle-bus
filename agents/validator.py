"""
에이전트 5: JSON 정합성 검증기
- 스키마 검증
- 좌표 유효성 검사
- 데이터 품질 검증
- 최종 서비스용 JSON 생성
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import SCHEMA_VERSION, PROCESSED_DIR, SEOUL_DISTRICTS

logger = logging.getLogger(__name__)


class JSONValidator:
    """JSON 데이터 검증 및 최종 출력 생성"""

    def __init__(self):
        # 서울시 경계 좌표 (대략적)
        self.seoul_bounds = {
            "min_lat": 37.42,
            "max_lat": 37.72,
            "min_lng": 126.76,
            "max_lng": 127.18
        }

        self.validation_errors = []
        self.validation_warnings = []

    def validate_coordinates(self, lat: float, lng: float) -> Tuple[bool, str]:
        """좌표 유효성 검사"""
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            return False, "좌표가 숫자가 아님"

        if lat < self.seoul_bounds["min_lat"] or lat > self.seoul_bounds["max_lat"]:
            return False, f"위도 범위 초과: {lat}"

        if lng < self.seoul_bounds["min_lng"] or lng > self.seoul_bounds["max_lng"]:
            return False, f"경도 범위 초과: {lng}"

        return True, "OK"

    def validate_stop(self, stop: Dict, route_name: str) -> List[str]:
        """정류장 데이터 검증"""
        errors = []

        if not stop.get("name"):
            errors.append(f"[{route_name}] 정류장 이름 없음")

        lat = stop.get("lat")
        lng = stop.get("lng")

        if lat is None or lng is None:
            errors.append(f"[{route_name}] '{stop.get('name', '?')}' 좌표 없음")
        else:
            valid, msg = self.validate_coordinates(lat, lng)
            if not valid:
                errors.append(f"[{route_name}] '{stop.get('name')}' {msg}")

        return errors

    def validate_route(self, route: Dict, district: str) -> Tuple[List[str], List[str]]:
        """노선 데이터 검증"""
        errors = []
        warnings = []

        route_name = route.get("name", "이름 없음")

        # 필수 필드
        if not route.get("name"):
            errors.append(f"[{district}] 노선 이름 없음")

        # 정류장 검증
        stops = route.get("stops", [])
        if len(stops) < 2:
            warnings.append(f"[{route_name}] 정류장이 2개 미만")

        for stop in stops:
            stop_errors = self.validate_stop(stop, route_name)
            errors.extend(stop_errors)

        # 선택 필드 검증
        if not route.get("hours"):
            warnings.append(f"[{route_name}] 운행시간 정보 없음")

        if not route.get("interval"):
            warnings.append(f"[{route_name}] 배차간격 정보 없음")

        return errors, warnings

    def validate_district(self, district_data: Dict) -> Tuple[List[str], List[str]]:
        """자치구 데이터 검증"""
        errors = []
        warnings = []

        district = district_data.get("district")

        if not district:
            errors.append("자치구 이름 없음")
            return errors, warnings

        if district not in SEOUL_DISTRICTS:
            warnings.append(f"'{district}'는 서울시 자치구가 아님")

        routes = district_data.get("routes", [])
        if not routes:
            warnings.append(f"[{district}] 노선 정보 없음")

        for route in routes:
            route_errors, route_warnings = self.validate_route(route, district)
            errors.extend(route_errors)
            warnings.extend(route_warnings)

        return errors, warnings

    def validate_data(self, data: Dict) -> Dict:
        """전체 데이터 검증"""
        self.validation_errors = []
        self.validation_warnings = []

        districts = data.get("districts", [])

        if not districts:
            self.validation_errors.append("자치구 데이터 없음")
            return self.get_validation_result()

        for district_data in districts:
            errors, warnings = self.validate_district(district_data)
            self.validation_errors.extend(errors)
            self.validation_warnings.extend(warnings)

        return self.get_validation_result()

    def get_validation_result(self) -> Dict:
        """검증 결과 반환"""
        return {
            "valid": len(self.validation_errors) == 0,
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
            "error_count": len(self.validation_errors),
            "warning_count": len(self.validation_warnings)
        }

    def fix_common_issues(self, data: Dict) -> Dict:
        """일반적인 문제 자동 수정"""
        fixed_districts = []

        for district_data in data.get("districts", []):
            fixed_routes = []

            for route in district_data.get("routes", []):
                # 유효한 정류장만 유지
                valid_stops = []
                for stop in route.get("stops", []):
                    lat = stop.get("lat")
                    lng = stop.get("lng")

                    if lat and lng:
                        valid, _ = self.validate_coordinates(lat, lng)
                        if valid:
                            valid_stops.append(stop)

                if len(valid_stops) >= 2:
                    route["stops"] = valid_stops
                    fixed_routes.append(route)

            if fixed_routes:
                district_data["routes"] = fixed_routes
                fixed_districts.append(district_data)

        data["districts"] = fixed_districts
        return data

    def generate_final_json(self, data: Dict, source: str = "자동 수집") -> Dict:
        """최종 서비스용 JSON 생성"""
        final = {
            "updated_at": datetime.now().strftime("%Y-%m-%d"),
            "source": source,
            "schema_version": SCHEMA_VERSION,
            "districts": []
        }

        for district_data in data.get("districts", []):
            district_entry = {
                "district": district_data["district"],
                "routes": []
            }

            for route in district_data.get("routes", []):
                route_entry = {
                    "name": route.get("name", f"{district_data['district']} 셔틀"),
                    "hours": route.get("hours", "정보 없음"),
                    "interval": route.get("interval", "정보 없음"),
                    "stops": route.get("stops", [])
                }
                district_entry["routes"].append(route_entry)

            if district_entry["routes"]:
                final["districts"].append(district_entry)

        # 자치구 정렬 (가나다순)
        final["districts"].sort(key=lambda x: x["district"])

        return final

    def calculate_quality_score(self, data: Dict) -> Dict:
        """데이터 품질 점수 계산"""
        total_districts = len(data.get("districts", []))
        total_routes = sum(len(d.get("routes", [])) for d in data.get("districts", []))
        total_stops = sum(
            len(r.get("stops", []))
            for d in data.get("districts", [])
            for r in d.get("routes", [])
        )

        # 점수 계산
        district_coverage = min(total_districts / 25 * 100, 100)  # 25개 자치구

        has_hours = sum(
            1 for d in data.get("districts", [])
            for r in d.get("routes", [])
            if r.get("hours") and r.get("hours") != "정보 없음"
        )
        has_interval = sum(
            1 for d in data.get("districts", [])
            for r in d.get("routes", [])
            if r.get("interval") and r.get("interval") != "정보 없음"
        )

        info_completeness = 0
        if total_routes > 0:
            info_completeness = ((has_hours + has_interval) / (total_routes * 2)) * 100

        avg_stops_per_route = total_stops / total_routes if total_routes > 0 else 0

        return {
            "district_coverage": round(district_coverage, 1),
            "info_completeness": round(info_completeness, 1),
            "total_districts": total_districts,
            "total_routes": total_routes,
            "total_stops": total_stops,
            "avg_stops_per_route": round(avg_stops_per_route, 1),
            "overall_score": round((district_coverage + info_completeness) / 2, 1)
        }

    def run(self) -> Dict:
        """전체 검증 및 최종 JSON 생성"""
        logger.info("=" * 50)
        logger.info("에이전트 5: JSON 검증기 시작")
        logger.info("=" * 50)

        # 입력 데이터 로드
        input_path = PROCESSED_DIR / "geocoded_routes.json"
        if not input_path.exists():
            logger.error(f"입력 파일 없음: {input_path}")
            return {"error": "Input file not found"}

        with open(input_path, encoding="utf-8") as f:
            data = json.load(f)

        # 검증
        logger.info("데이터 검증 중...")
        validation = self.validate_data(data)

        logger.info(f"  오류: {validation['error_count']}개")
        logger.info(f"  경고: {validation['warning_count']}개")

        for error in validation["errors"][:10]:  # 최대 10개만 표시
            logger.error(f"  ❌ {error}")

        for warning in validation["warnings"][:10]:
            logger.warning(f"  ⚠️ {warning}")

        # 문제 수정
        if not validation["valid"]:
            logger.info("\n자동 수정 시도...")
            data = self.fix_common_issues(data)
            validation = self.validate_data(data)
            logger.info(f"  수정 후 오류: {validation['error_count']}개")

        # 최종 JSON 생성
        logger.info("\n최종 JSON 생성 중...")
        final_data = self.generate_final_json(data)

        # 품질 점수
        quality = self.calculate_quality_score(final_data)
        logger.info(f"\n📊 데이터 품질:")
        logger.info(f"  자치구 커버리지: {quality['district_coverage']}%")
        logger.info(f"  정보 완성도: {quality['info_completeness']}%")
        logger.info(f"  종합 점수: {quality['overall_score']}점")

        # 결과 저장
        output_path = PROCESSED_DIR.parent / "shuttle_routes.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)

        # 검증 리포트 저장
        report = {
            "validation": validation,
            "quality": quality,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        report_path = PROCESSED_DIR / "validation_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"\n✅ 완료!")
        logger.info(f"  서비스용 JSON: {output_path}")
        logger.info(f"  검증 리포트: {report_path}")

        return {
            "final_data": final_data,
            "validation": validation,
            "quality": quality
        }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    validator = JSONValidator()
    results = validator.run()
