# 🚌 서울 무료 셔틀버스 노선도 자동화 시스템

서울 시내버스 파업 기간 동안 시민들을 위한 무료 셔틀버스 노선 정보를 **자동 수집**하고 **지도로 시각화**하는 공익 프로젝트입니다.

## 🎯 프로젝트 목표

- 서울시 공식 페이지 + 25개 자치구 공지에서 셔틀버스 정보 자동 수집
- PDF/이미지 노선도 OCR 처리
- 정류장 좌표 자동 변환 (지오코딩)
- JSON 표준화 및 품질 검증
- 모바일 최적화 웹 페이지 자동 반영

## 📁 프로젝트 구조

```
seoul-shuttle-bus/
├── agents/                    # 자동화 에이전트 모듈
│   ├── crawler.py            # 에이전트 1: 자치구 공지 URL 크롤러
│   ├── ocr_parser.py         # 에이전트 2: PDF OCR 파서
│   ├── nlp_extractor.py      # 에이전트 3: 정류장 NLP 추출기
│   ├── geocoder.py           # 에이전트 4: 지오코딩 서비스
│   ├── validator.py          # 에이전트 5: JSON 검증기
│   └── pipeline.py           # 에이전트 6: 파이프라인 오케스트레이터
├── data/
│   ├── raw/                  # 수집된 원본 데이터 (PDF, HTML)
│   └── processed/            # 처리된 중간 데이터
├── logs/                     # 실행 로그
├── index.html               # 메인 웹 페이지
├── index_mobile.html        # 모바일 최적화 페이지
├── shuttle_routes.json      # 서비스용 노선 데이터
├── config.py                # 설정 파일
├── run_pipeline.py          # 파이프라인 실행 스크립트
└── requirements.txt         # Python 의존성
```

## 🚀 빠른 시작

### 1. 웹 페이지 바로 실행

```bash
cd D:\seoul-shuttle-bus
python -m http.server 8000

# 브라우저에서 접속
# 데스크톱: http://localhost:8000
# 모바일 최적화: http://localhost:8000/index_mobile.html
```

### 2. 데이터 파이프라인 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 빠른 실행 (OCR 제외)
python run_pipeline.py --mode quick

# 전체 실행 (OCR 포함)
python run_pipeline.py --mode full

# 특정 스테이지만 실행
python run_pipeline.py --stages crawler nlp geocode validate
```

## 🔧 파이프라인 아키텍처

```
[서울시/구청 공지] → 에이전트 1: 크롤링
        ↓
[PDF / HTML 수집] → 에이전트 2: OCR
        ↓
[텍스트 추출] → 에이전트 3: NLP 정제
        ↓
[정류장명 리스트] → 에이전트 4: 지오코딩
        ↓
[좌표 데이터] → 에이전트 5: 검증
        ↓
[표준 JSON] → 웹 페이지 자동 반영
```

## ⚙️ 설정

### API 키 설정 (지오코딩)

```bash
# 환경변수 설정
set KAKAO_API_KEY=your_kakao_rest_api_key
```

### OCR 설정 (PDF 처리)

Tesseract OCR 설치 필요:
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Mac: brew install tesseract tesseract-lang
- Linux: sudo apt install tesseract-ocr tesseract-ocr-kor

## 📱 주요 기능

### 웹 페이지
- ✅ 자치구별 탭 네비게이션 (스크롤)
- ✅ Leaflet.js 인터랙티브 지도
- ✅ 노선별 경로 시각화
- ✅ 반응형 디자인 (모바일/데스크톱)
- ✅ 다크모드 지원
- ✅ 현재 위치 기반 자동 선택
- ✅ 슬라이드업 패널 (모바일)

### 자동화 파이프라인
- ✅ 서울시/자치구 공지 자동 크롤링
- ✅ PDF 첨부파일 자동 다운로드
- ✅ Tesseract OCR 한글 추출
- ✅ NLP 기반 정류장 추출
- ✅ 카카오 API 지오코딩
- ✅ JSON 스키마 검증

## 🌐 배포

### GitHub Pages (무료)
1. GitHub 저장소 생성
2. 파일 업로드
3. Settings > Pages > Source: main branch

### Cloudflare Pages (무료)
1. Cloudflare 계정 생성
2. Pages > Create a project
3. Git 연결 또는 직접 업로드

## 📰 언론/서울시 제보용

```
서울 시내버스 파업 기간 중 시민 불편 해소를 위해
서울시 및 자치구 공식 자료를 기반으로
무료 셔틀버스 노선을 지도 형태로 통합 제공하는
비영리 정보 페이지를 제작했습니다.

출처를 명확히 표기하며,
시민 누구나 무료로 접근 가능하도록 공개했습니다.
```

## 📄 라이선스

MIT License - 공익 목적으로 자유롭게 사용 가능합니다.

---

**"공공 데이터는 있어도, 공공 UX는 없다"**
이 프로젝트는 그 간극을 메우기 위해 만들어졌습니다.
