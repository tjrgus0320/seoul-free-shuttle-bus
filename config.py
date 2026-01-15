"""
서울 무료 셔틀버스 자동화 시스템 설정
"""

import os
from pathlib import Path

# 프로젝트 경로
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
LOGS_DIR = BASE_DIR / "logs"

# API 키 (환경변수에서 로드)
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY", "YOUR_KAKAO_REST_API_KEY")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# 크롤링 설정
CRAWL_CONFIG = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "timeout": 15,
    "retry_count": 3,
    "retry_delay": 2,
}

# 서울시 공식 소스
OFFICIAL_SOURCES = [
    {
        "name": "서울시 비상수송대책",
        "url": "https://news.seoul.go.kr/traffic/archives/514068",
        "type": "main"
    },
    {
        "name": "서울시 교통정보",
        "url": "https://topis.seoul.go.kr",
        "type": "reference"
    }
]

# 서울시 25개 자치구 정보
SEOUL_DISTRICTS = {
    "종로구": {"code": "110", "keywords": ["종로", "광화문", "경복궁"]},
    "중구": {"code": "100", "keywords": ["중구", "명동", "을지로"]},
    "용산구": {"code": "140", "keywords": ["용산", "이태원", "한남"]},
    "성동구": {"code": "133", "keywords": ["성동", "왕십리", "성수"]},
    "광진구": {"code": "143", "keywords": ["광진", "건대", "구의"]},
    "동대문구": {"code": "130", "keywords": ["동대문", "청량리", "회기"]},
    "중랑구": {"code": "131", "keywords": ["중랑", "망우", "면목"]},
    "성북구": {"code": "136", "keywords": ["성북", "길음", "돈암"]},
    "강북구": {"code": "305", "keywords": ["강북", "수유", "미아"]},
    "도봉구": {"code": "320", "keywords": ["도봉", "창동", "쌍문"]},
    "노원구": {"code": "350", "keywords": ["노원", "상계", "중계"]},
    "은평구": {"code": "380", "keywords": ["은평", "연신내", "불광"]},
    "서대문구": {"code": "120", "keywords": ["서대문", "신촌", "홍제"]},
    "마포구": {"code": "121", "keywords": ["마포", "홍대", "합정"]},
    "양천구": {"code": "158", "keywords": ["양천", "목동", "신정"]},
    "강서구": {"code": "157", "keywords": ["강서", "화곡", "발산"]},
    "구로구": {"code": "152", "keywords": ["구로", "신도림", "개봉"]},
    "금천구": {"code": "153", "keywords": ["금천", "가산", "독산"]},
    "영등포구": {"code": "150", "keywords": ["영등포", "여의도", "당산"]},
    "동작구": {"code": "156", "keywords": ["동작", "사당", "노량진"]},
    "관악구": {"code": "151", "keywords": ["관악", "신림", "봉천"]},
    "서초구": {"code": "137", "keywords": ["서초", "강남", "양재"]},
    "강남구": {"code": "135", "keywords": ["강남", "역삼", "삼성"]},
    "송파구": {"code": "138", "keywords": ["송파", "잠실", "가락"]},
    "강동구": {"code": "134", "keywords": ["강동", "천호", "길동"]},
}

# OCR 설정
OCR_CONFIG = {
    "tesseract_path": r"C:\Program Files\Tesseract-OCR\tesseract.exe",  # Windows
    "language": "kor+eng",
    "dpi": 300,
    "psm": 6,  # Page segmentation mode
}

# NLP 정류장 추출 패턴
STOP_PATTERNS = {
    "keywords": [
        "역", "정류장", "사거리", "삼거리", "오거리",
        "주민센터", "구청", "시장", "공원", "학교",
        "병원", "아파트", "마을", "입구", "앞", "건너"
    ],
    "exclude": [
        "운행", "시간", "배차", "간격", "분", "시",
        "노선", "안내", "문의", "연락처"
    ]
}

# 지오코딩 설정
GEOCODE_CONFIG = {
    "provider": "kakao",  # kakao, naver, google
    "default_region": "서울",
    "cache_enabled": True,
    "cache_file": PROCESSED_DIR / "geocode_cache.json"
}

# JSON 스키마 버전
SCHEMA_VERSION = "1.0.0"

# 로깅 설정
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S"
}
