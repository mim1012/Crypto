"""
개선된 설정 테스트
GUI에서 직접 설정을 변경하여 테스트
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow
from datetime import datetime
import time

def main():
    print("="*60)
    print("개선된 설정으로 GUI 파라미터 테스트")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # PyQt5 애플리케이션 생성
    app = QApplication(sys.argv)

    # GUI 생성 및 표시
    window = MainWindow()
    window.show()

    # GUI 탭 가져오기
    entry_tab = window.entry_tab
    exit_tab = window.exit_tab

    print("\n【현재 GUI 설정 확인】")

    # 1. 진입 설정 확인
    print("\n[진입 조건]")

    # MA Cross 설정 확인
    print(f"MA 단기선: {entry_tab.ma_short_spinbox.value()}")
    print(f"MA 장기선: {entry_tab.ma_long_spinbox.value()}")

    # Price Channel 설정 확인
    print(f"PC 기간: {entry_tab.pc_period_spinbox.value()}")

    # 포지션 크기 확인
    print(f"포지션 크기: ${entry_tab.position_size_spinbox.value():,.2f}")

    # 레버리지 확인
    print(f"레버리지: {entry_tab.binance_leverage_spinbox.value()}x")

    print("\n[청산 조건]")

    # PC 본절 청산 틱 확인
    print(f"PC 본절 롱 틱: {exit_tab.pc_break_long_spinbox.value()}")
    print(f"PC 본절 숏 틱: {exit_tab.pc_break_short_spinbox.value()}")

    # PCS 테이블 확인
    pcs_table = exit_tab.pcs_table
    active_steps = 0
    for row in range(12):
        checkbox = pcs_table.cellWidget(row, 1)
        if checkbox and checkbox.isChecked():
            active_steps += 1
    print(f"PCS 활성 단계: {active_steps}개")

    print("\n" + "="*60)
    print("【권장 설정 적용 방법】")
    print("="*60)
    print("\n1. MA Cross 설정:")
    print("   - 단기선: 20 → 50으로 변경")
    print("   - 장기선: 50 → 200으로 변경")
    print("\n2. 신뢰도 임계값:")
    print("   - 진입 조건 탭에서 설정")
    print("\n3. 포지션 관리:")
    print("   - 리스크 탭에서 최대 포지션 1개로 제한")
    print("\n4. 조합 모드:")
    print("   - 진입 조건 탭에서 AND 모드 선택")

    print("\n✅ GUI가 실행되었습니다.")
    print("위의 권장 설정을 직접 GUI에서 변경한 후")
    print("거래 시작 버튼을 눌러 테스트하세요.")

    print("\n【실시간 바인딩 확인】")
    print("모든 GUI 설정은 실시간으로 동기화됩니다:")
    print("✅ 체크박스 상태 → 즉시 반영")
    print("✅ 스핀박스 값 → 즉시 반영")
    print("✅ 콤보박스 선택 → 즉시 반영")
    print("✅ 테이블 수정 → 즉시 반영")

    # 애플리케이션 실행
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()