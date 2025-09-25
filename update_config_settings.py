"""
config.json 설정 최적화
"""
import json

def update_config_settings():
    """설정 파일 업데이트"""

    print("="*60)
    print("설정 파일 최적화")
    print("="*60)

    # 현재 설정 읽기
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    print("\n[변경 전 설정]")
    print(f"심볼: {config['trading']['symbol']}")
    print(f"레버리지: {config['trading']['leverage']}")
    print(f"포지션 크기: ${config['trading']['position_size']}")
    print(f"조합 모드: {config['entry']['combination_mode']}")
    print(f"MA 활성화: {config['entry']['ma_enabled']}")
    print(f"MA 기간: {config['entry']['ma_period']}")

    # 설정 최적화
    print("\n[설정 변경 중...]")

    # 1. 거래 설정
    config['trading']['symbol'] = 'BTCUSDT'  # BTC로 변경
    config['trading']['leverage'] = 10  # 레버리지 10x
    config['trading']['position_size'] = 1000.0  # $1000
    config['trading']['max_positions'] = 1  # 최대 1개 포지션

    # 2. 진입 조건 설정
    config['entry']['combination_mode'] = 'AND'  # AND 모드
    config['entry']['ma_enabled'] = True  # MA 활성화
    config['entry']['ma_period'] = 50  # MA 기간 50
    config['entry']['pc_enabled'] = True  # PC 활성화
    config['entry']['pc_period'] = 50  # PC 기간 50

    # 3. MA Cross 설정 추가
    if 'ma_cross' not in config['entry']:
        config['entry']['ma_cross'] = {
            'short_period': 50,
            'long_period': 200,
            'confidence_threshold': 0.5,
            'enabled': True
        }
    else:
        config['entry']['ma_cross']['short_period'] = 50
        config['entry']['ma_cross']['long_period'] = 200
        config['entry']['ma_cross']['confidence_threshold'] = 0.5

    # 4. Price Channel 설정 추가
    if 'price_channel' not in config['entry']:
        config['entry']['price_channel'] = {
            'period': 50,
            'confidence_threshold': 0.5,
            'enabled': True
        }
    else:
        config['entry']['price_channel']['period'] = 50
        config['entry']['price_channel']['confidence_threshold'] = 0.5

    # 5. 추가 설정
    if 'cooldown_minutes' not in config['trading']:
        config['trading']['cooldown_minutes'] = 5

    if 'min_confidence' not in config['trading']:
        config['trading']['min_confidence'] = 0.5

    # 6. 청산 설정 최적화
    if 'pcs_system' not in config['exit']:
        config['exit']['pcs_system'] = {
            'enabled': True,
            'active_steps': [1, 2, 3, 4, 5, 6]
        }

    # 설정 저장
    with open('config.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("\n[변경 후 설정]")
    print(f"심볼: {config['trading']['symbol']}")
    print(f"레버리지: {config['trading']['leverage']}x")
    print(f"포지션 크기: ${config['trading']['position_size']}")
    print(f"조합 모드: {config['entry']['combination_mode']}")
    print(f"최대 포지션: {config['trading']['max_positions']}개")
    print(f"쿨다운: {config['trading'].get('cooldown_minutes', 5)}분")
    print(f"MA Cross: {config['entry']['ma_cross']['short_period']}/{config['entry']['ma_cross']['long_period']}")
    print(f"신뢰도 임계값: {config['entry']['ma_cross']['confidence_threshold']}")

    print("\n" + "="*60)
    print("✅ 설정 최적화 완료!")
    print("="*60)

if __name__ == "__main__":
    update_config_settings()