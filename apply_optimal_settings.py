"""
최적화된 설정 자동 적용
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings_manager import SettingsManager
import json

def apply_optimal_settings():
    """권장 설정을 config.json에 적용"""

    print("="*60)
    print("최적화된 설정 적용")
    print("="*60)

    # 설정 매니저 로드
    settings_manager = SettingsManager()

    # 현재 설정 읽기
    config_path = "config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    print("\n[변경 전 설정]")
    print(f"MA 단기/장기: {config['entry']['ma_cross']['short_period']}/{config['entry']['ma_cross']['long_period']}")
    print(f"PC 기간: {config['entry']['price_channel']['period']}")
    print(f"신뢰도 임계값: {config['entry']['ma_cross'].get('confidence_threshold', 0.01)}")
    print(f"조합 모드: {config['trading'].get('combination_mode', 'OR')}")
    print(f"포지션 크기: ${config['trading'].get('position_size', 5000)}")

    # 최적화된 설정 적용
    print("\n[권장 설정 적용 중...]")

    # 1. 진입 조건 개선
    config['entry']['ma_cross']['short_period'] = 50  # 20 -> 50
    config['entry']['ma_cross']['long_period'] = 200  # 50 -> 200
    config['entry']['ma_cross']['confidence_threshold'] = 0.5  # 0.01 -> 0.5

    config['entry']['price_channel']['period'] = 50  # 20 -> 50
    config['entry']['price_channel']['confidence_threshold'] = 0.5  # 추가

    # 2. 거래 설정 개선
    config['trading']['combination_mode'] = 'AND'  # OR -> AND
    config['trading']['position_size'] = 1000  # 5000 -> 1000
    config['trading']['max_positions'] = 1  # 최대 포지션 1개
    config['trading']['cooldown_minutes'] = 5  # 쿨다운 5분

    # 3. 리스크 관리 강화
    if 'risk' not in config:
        config['risk'] = {}

    config['risk']['max_leverage'] = 10  # 최대 레버리지 10x
    config['risk']['max_daily_trades'] = 20  # 일일 최대 거래 20회
    config['risk']['max_drawdown'] = 0.05  # 최대 손실 5%

    # 4. 청산 설정 최적화
    config['exit']['pcs_system']['enabled'] = True
    config['exit']['pcs_system']['active_steps'] = [1, 2, 3, 4, 5, 6]  # 1-6단계만

    # 5. 최소 수량 설정
    config['trading']['min_quantity'] = 0.001  # BTC 최소 수량

    # 설정 저장
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("\n[변경 후 설정]")
    print(f"MA 단기/장기: {config['entry']['ma_cross']['short_period']}/{config['entry']['ma_cross']['long_period']}")
    print(f"PC 기간: {config['entry']['price_channel']['period']}")
    print(f"신뢰도 임계값: {config['entry']['ma_cross']['confidence_threshold']}")
    print(f"조합 모드: {config['trading']['combination_mode']}")
    print(f"포지션 크기: ${config['trading']['position_size']}")
    print(f"최대 포지션: {config['trading']['max_positions']}개")
    print(f"쿨다운: {config['trading']['cooldown_minutes']}분")
    print(f"최대 레버리지: {config['risk']['max_leverage']}x")

    print("\n" + "="*60)
    print("✅ 설정 적용 완료!")
    print("="*60)
    print("\n다음 단계:")
    print("1. 실행 중인 프로세스 재시작")
    print("2. GUI에서 '설정 새로고침' 클릭")
    print("3. 거래 재시작")

    return config

if __name__ == "__main__":
    apply_optimal_settings()