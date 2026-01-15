#!/usr/bin/env python3
"""
서울 무료 셔틀버스 데이터 파이프라인 실행 스크립트
사용법: python run_pipeline.py [--mode full|quick|update|validate]
"""

import sys
import logging
from pathlib import Path

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent))

from agents.pipeline import PipelineOrchestrator, main

if __name__ == "__main__":
    main()
