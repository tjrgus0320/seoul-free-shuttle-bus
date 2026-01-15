"""
에이전트 1: 자치구 공지 URL 크롤러
- 서울시 공식 페이지에서 자치구별 셔틀버스 공지 수집
- PDF/첨부파일 URL 자동 추출
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from config import CRAWL_CONFIG, OFFICIAL_SOURCES, SEOUL_DISTRICTS, RAW_DIR

logger = logging.getLogger(__name__)


class DistrictCrawler:
    """자치구 셔틀버스 공지 크롤러"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": CRAWL_CONFIG["user_agent"],
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"
        })
        self.collected_data = []
        self.keywords = ["무료", "셔틀", "파업", "비상", "수송", "노선", "운행"]

    def fetch_page(self, url: str) -> Optional[str]:
        """웹 페이지 HTML 가져오기"""
        for attempt in range(CRAWL_CONFIG["retry_count"]):
            try:
                response = self.session.get(
                    url,
                    timeout=CRAWL_CONFIG["timeout"]
                )
                response.encoding = "utf-8"

                if response.status_code == 200:
                    return response.text

                logger.warning(f"HTTP {response.status_code}: {url}")

            except requests.RequestException as e:
                logger.warning(f"요청 실패 (시도 {attempt + 1}): {e}")
                time.sleep(CRAWL_CONFIG["retry_delay"])

        return None

    def extract_district_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """자치구 관련 링크 추출"""
        links = []

        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            text = a_tag.get_text(strip=True)

            # 자치구 이름 확인
            for district in SEOUL_DISTRICTS.keys():
                if district in text:
                    full_url = urljoin(base_url, href)
                    links.append({
                        "district": district,
                        "text": text,
                        "url": full_url,
                        "type": "district_link"
                    })
                    break

        return links

    def extract_attachments(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """첨부파일 (PDF, HWP 등) URL 추출"""
        attachments = []
        file_extensions = [".pdf", ".hwp", ".hwpx", ".docx", ".xlsx"]

        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "").lower()

            for ext in file_extensions:
                if ext in href:
                    full_url = urljoin(base_url, a_tag.get("href"))
                    filename = a_tag.get_text(strip=True) or urlparse(href).path.split("/")[-1]

                    attachments.append({
                        "filename": filename,
                        "url": full_url,
                        "type": ext.replace(".", ""),
                        "source": base_url
                    })
                    break

        return attachments

    def extract_route_info(self, soup: BeautifulSoup, source_url: str) -> List[Dict]:
        """페이지 본문에서 노선 정보 추출"""
        routes = []

        # 본문 영역 선택
        content_areas = soup.select(
            "div.view-con, div.content, article, .post-content, "
            ".board-view, .bbs-view, main"
        )

        if not content_areas:
            content_areas = [soup.body] if soup.body else []

        for section in content_areas:
            text = section.get_text("\n", strip=True)

            # 자치구별 정보 추출
            for district, info in SEOUL_DISTRICTS.items():
                if district in text:
                    # 해당 구 관련 텍스트 블록 추출
                    lines = text.split("\n")
                    district_lines = []
                    in_district_section = False

                    for line in lines:
                        if district in line:
                            in_district_section = True

                        if in_district_section:
                            district_lines.append(line)

                            # 다른 구 이름이 나오면 종료
                            other_districts = [d for d in SEOUL_DISTRICTS.keys() if d != district]
                            if any(d in line for d in other_districts) and district not in line:
                                break

                    if district_lines:
                        routes.append({
                            "district": district,
                            "raw_text": "\n".join(district_lines[:50]),  # 최대 50줄
                            "source": source_url
                        })

        return routes

    def crawl_main_sources(self) -> List[Dict]:
        """공식 소스 크롤링"""
        results = []

        for source in OFFICIAL_SOURCES:
            logger.info(f"크롤링: {source['name']} ({source['url']})")

            html = self.fetch_page(source["url"])
            if not html:
                continue

            soup = BeautifulSoup(html, "lxml")

            # 자치구 링크 추출
            district_links = self.extract_district_links(soup, source["url"])
            logger.info(f"  발견된 자치구 링크: {len(district_links)}개")

            # 첨부파일 추출
            attachments = self.extract_attachments(soup, source["url"])
            logger.info(f"  발견된 첨부파일: {len(attachments)}개")

            # 본문 노선 정보 추출
            routes = self.extract_route_info(soup, source["url"])
            logger.info(f"  추출된 노선 정보: {len(routes)}개")

            results.append({
                "source": source,
                "district_links": district_links,
                "attachments": attachments,
                "routes": routes,
                "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })

            time.sleep(1)  # 예의 바른 크롤링

        return results

    def crawl_district_pages(self, district_links: List[Dict]) -> List[Dict]:
        """자치구 개별 페이지 크롤링"""
        results = []

        for link in district_links:
            logger.info(f"자치구 페이지 크롤링: {link['district']} ({link['url']})")

            html = self.fetch_page(link["url"])
            if not html:
                continue

            soup = BeautifulSoup(html, "lxml")

            # 첨부파일 추출
            attachments = self.extract_attachments(soup, link["url"])

            # 노선 정보 추출
            routes = self.extract_route_info(soup, link["url"])

            results.append({
                "district": link["district"],
                "url": link["url"],
                "attachments": attachments,
                "routes": routes,
                "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })

            time.sleep(1)

        return results

    def download_attachment(self, url: str, save_path: Path) -> bool:
        """첨부파일 다운로드"""
        try:
            response = self.session.get(url, timeout=30, stream=True)

            if response.status_code == 200:
                with open(save_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"다운로드 완료: {save_path.name}")
                return True

        except Exception as e:
            logger.error(f"다운로드 실패: {e}")

        return False

    def run(self, download_files: bool = True) -> Dict:
        """전체 크롤링 실행"""
        logger.info("=" * 50)
        logger.info("에이전트 1: 자치구 공지 URL 크롤러 시작")
        logger.info("=" * 50)

        # 메인 소스 크롤링
        main_results = self.crawl_main_sources()

        # 자치구 링크 수집
        all_district_links = []
        for result in main_results:
            all_district_links.extend(result.get("district_links", []))

        # 중복 제거
        seen_urls = set()
        unique_links = []
        for link in all_district_links:
            if link["url"] not in seen_urls:
                seen_urls.add(link["url"])
                unique_links.append(link)

        # 자치구 페이지 크롤링
        district_results = self.crawl_district_pages(unique_links)

        # 첨부파일 다운로드
        downloaded_files = []
        if download_files:
            all_attachments = []
            for result in main_results:
                all_attachments.extend(result.get("attachments", []))
            for result in district_results:
                all_attachments.extend(result.get("attachments", []))

            for attachment in all_attachments:
                if attachment["type"] == "pdf":
                    filename = f"{attachment['filename']}"
                    if not filename.endswith(".pdf"):
                        filename += ".pdf"
                    save_path = RAW_DIR / filename

                    if self.download_attachment(attachment["url"], save_path):
                        downloaded_files.append(str(save_path))

        # 결과 저장
        output = {
            "main_results": main_results,
            "district_results": district_results,
            "downloaded_files": downloaded_files,
            "summary": {
                "total_sources": len(main_results),
                "total_district_pages": len(district_results),
                "total_attachments": len(downloaded_files),
                "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }

        output_path = RAW_DIR / "crawl_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"\n크롤링 완료! 결과: {output_path}")

        return output


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    crawler = DistrictCrawler()
    results = crawler.run(download_files=True)

    print(f"\n📊 크롤링 요약:")
    print(f"  - 메인 소스: {results['summary']['total_sources']}개")
    print(f"  - 자치구 페이지: {results['summary']['total_district_pages']}개")
    print(f"  - 다운로드 파일: {results['summary']['total_attachments']}개")
