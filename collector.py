"""
서울 무료 셔틀버스 노선 정보 수집 스크립트
- 서울시 공식 페이지 및 자치구 공지에서 셔틀버스 정보 수집
- HTML 기반 공지 자동 수집 → JSON 변환
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from typing import List, Dict, Any

# 수집 대상 URL 목록
SOURCES = [
    {
        "name": "서울시 비상수송대책",
        "url": "https://news.seoul.go.kr/traffic/archives/514068",
        "type": "official"
    },
    # 추가 소스는 여기에 등록
]

def fetch_page(url: str) -> str:
    """웹 페이지 HTML 가져오기"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = "utf-8"
        return res.text
    except Exception as e:
        print(f"❌ 페이지 로드 실패: {url} - {e}")
        return ""

def extract_district_info(soup: BeautifulSoup, source_url: str) -> List[Dict]:
    """HTML에서 자치구별 셔틀버스 정보 추출"""
    districts = []

    # 본문 영역 선택 (사이트마다 구조가 다를 수 있음)
    content_areas = soup.select("div.view-con, div.content, article, .post-content")

    if not content_areas:
        content_areas = [soup.body] if soup.body else []

    for section in content_areas:
        text = section.get_text("\n", strip=True)

        # 자치구 이름 추출 (예: 영등포구, 관악구 등)
        district_matches = re.findall(r"([가-힣]{1,3}구)", text)

        # 서울시 자치구 목록으로 필터링
        seoul_districts = [
            "종로구", "중구", "용산구", "성동구", "광진구", "동대문구", "중랑구",
            "성북구", "강북구", "도봉구", "노원구", "은평구", "서대문구", "마포구",
            "양천구", "강서구", "구로구", "금천구", "영등포구", "동작구", "관악구",
            "서초구", "강남구", "송파구", "강동구"
        ]

        found_districts = [d for d in district_matches if d in seoul_districts]
        found_districts = list(dict.fromkeys(found_districts))  # 중복 제거

        for district_name in found_districts:
            routes = []

            # 해당 구 관련 노선 정보 추출
            for line in text.split("\n"):
                if district_name in line or "운행" in line or "노선" in line or "셔틀" in line:
                    # 시간 정보 추출
                    time_match = re.search(r"(\d{1,2}:\d{2})\s*[~-]\s*(\d{1,2}:\d{2})", line)
                    # 배차간격 추출
                    interval_match = re.search(r"(\d+)\s*[~-]?\s*(\d+)?\s*분", line)

                    route_info = {
                        "raw_text": line.strip(),
                        "hours": f"{time_match.group(1)}~{time_match.group(2)}" if time_match else None,
                        "interval": f"{interval_match.group(1)}~{interval_match.group(2)}분" if interval_match and interval_match.group(2) else f"{interval_match.group(1)}분" if interval_match else None
                    }

                    if route_info["raw_text"]:
                        routes.append(route_info)

            if routes:
                districts.append({
                    "district": district_name,
                    "routes": routes,
                    "source": source_url
                })

    return districts

def collect_all_sources() -> Dict[str, Any]:
    """모든 소스에서 데이터 수집"""
    all_data = {
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sources": [],
        "districts": []
    }

    seen_districts = set()

    for source in SOURCES:
        print(f"📡 수집 중: {source['name']} ({source['url']})")

        html = fetch_page(source["url"])
        if not html:
            continue

        soup = BeautifulSoup(html, "lxml")
        districts = extract_district_info(soup, source["url"])

        all_data["sources"].append({
            "name": source["name"],
            "url": source["url"],
            "collected": True
        })

        for district in districts:
            if district["district"] not in seen_districts:
                all_data["districts"].append(district)
                seen_districts.add(district["district"])
                print(f"  ✅ {district['district']}: {len(district['routes'])}개 노선 정보")

    return all_data

def save_raw_data(data: Dict, filename: str = "shuttle_routes_raw.json"):
    """수집된 원본 데이터 저장"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n💾 저장 완료: {filename}")

def main():
    print("=" * 50)
    print("🚌 서울 무료 셔틀버스 노선 정보 수집기")
    print("=" * 50)
    print()

    # 데이터 수집
    data = collect_all_sources()

    # 원본 데이터 저장
    save_raw_data(data)

    print()
    print(f"📊 수집 결과: {len(data['districts'])}개 자치구 정보")
    print("=" * 50)
    print()
    print("💡 다음 단계:")
    print("   1. shuttle_routes_raw.json 검토")
    print("   2. 필요시 수동 보정")
    print("   3. shuttle_routes.json으로 정규화")
    print("   4. index.html에서 확인")

if __name__ == "__main__":
    main()
