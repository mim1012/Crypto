#!/usr/bin/env python3
"""조건 설정 설명"""

print("=" * 60)
print("거래 조건 설정 안내")
print("=" * 60)

print("""
현재 WARNING 메시지의 의미:
- [2/4] 진입 조건 없음 = 진입 탭에서 아무것도 활성화 안 됨
- [3/4] 청산 조건 없음 = 청산 탭에서 아무것도 활성화 안 됨

해결 방법:
1. GUI의 "진입 설정" 탭에서 최소 1개 이상 체크:
   ☑ MA 조건 사용
   ☑ PC 조건 사용
   ☑ 매수벽 조건 사용
   ☑ 캔들 조건 사용
   ☑ 틱 조건 사용

2. GUI의 "청산 설정" 탭에서 최소 1개 이상 체크:
   ☑ PCS 청산 활성화
   ☑ PCT 트레일링 활성화
   ☑ 호가창 청산 활성화
   ☑ PC 청산 활성화

활성화된 조건만 거래에 사용됩니다!
""")

# 시뮬레이션: 조건을 설정한 경우
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

engine_logger = logging.getLogger("core.trading_engine")

print("\n조건 설정 후 로그 예시:")
print("-" * 40)

engine_logger.info("거래 사이클 #1 시작")
engine_logger.info("[1/4] 시장 데이터 수집 시작...")
engine_logger.info("  - binance: 가격=$112,300.00")
engine_logger.info("[2/4] 진입 조건 평가 중... (총 2개 조건)")
engine_logger.info("  - 조건 1: MA 조건 (활성)")
engine_logger.info("  - 조건 2: PC 조건 (활성)")
engine_logger.info("  결과: 진입 신호 없음")
engine_logger.info("[3/4] 청산 조건 평가 중... (총 1개 조건)")
engine_logger.info("  - 조건 1: PCS 청산 (활성)")
engine_logger.info("  결과: 청산 신호 없음")
engine_logger.info("[4/4] 실행할 신호 없음 - 대기")
engine_logger.info("거래 사이클 #1 완료")

print("\n이제 WARNING 대신 조건 평가 로그가 나타납니다!")