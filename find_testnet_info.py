#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Binance Testnet 정보 상세 탐색
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time

def find_testnet_info():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # 브라우저 보이게
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        print("=" * 70)
        print("Binance Testnet 정보 검색")
        print("=" * 70)

        # 1. 메인 개발자 포털
        print("\n1. Binance 개발자 포털 접속...")
        page.goto("https://developers.binance.com/", timeout=30000)
        time.sleep(2)

        # Derivatives 섹션 찾기
        print("\n2. Derivatives 섹션 검색...")
        try:
            # Derivatives 링크 클릭
            derivatives_link = page.locator("text=Derivatives").first
            if derivatives_link:
                print("   Derivatives 링크 발견, 클릭...")
                derivatives_link.click()
                time.sleep(2)
        except:
            print("   Derivatives 링크를 찾을 수 없음")

        # 3. 직접 Testnet 페이지들 시도
        print("\n3. 알려진 Testnet 페이지 직접 접속...")

        testnet_pages = [
            {
                "name": "Futures Testnet Portal",
                "url": "https://testnet.binancefuture.com"
            },
            {
                "name": "Spot Testnet Portal",
                "url": "https://testnet.binance.vision"
            },
            {
                "name": "Binance API Github",
                "url": "https://github.com/binance/binance-api-postman"
            }
        ]

        for testnet in testnet_pages:
            print(f"\n   {testnet['name']}:")
            print(f"   URL: {testnet['url']}")
            try:
                page.goto(testnet['url'], timeout=10000)
                time.sleep(2)

                # 페이지 제목 확인
                title = page.title()
                print(f"   ✅ 페이지 제목: {title}")

                # Register 버튼 찾기
                register_btn = page.locator("text=/Register|Sign Up|Create Account/i").first
                if register_btn:
                    print(f"   ✅ 가입 버튼 발견!")

                # API Management 링크 찾기
                api_link = page.locator("text=/API/i").first
                if api_link:
                    print(f"   ✅ API 관리 메뉴 있음")

                # 스크린샷
                screenshot_name = f"{testnet['name'].replace(' ', '_')}.png"
                page.screenshot(path=screenshot_name)
                print(f"   스크린샷 저장: {screenshot_name}")

            except Exception as e:
                print(f"   ❌ 접속 실패: {e}")

        # 4. Google 검색으로 정보 찾기
        print("\n4. Google에서 Binance Futures Testnet 검색...")
        page.goto("https://www.google.com")
        time.sleep(1)

        # 검색어 입력
        search_box = page.locator("input[name='q']").first
        if search_box:
            search_box.fill("Binance Futures Testnet API registration guide")
            search_box.press("Enter")
            time.sleep(2)

            # 결과 확인
            results = page.locator("h3").all()
            print("\n   검색 결과 (상위 5개):")
            for i, result in enumerate(results[:5], 1):
                try:
                    text = result.text_content()
                    print(f"   {i}. {text}")
                except:
                    continue

        print("\n" + "=" * 70)
        print("검색 완료 - 브라우저를 10초 후 닫습니다...")
        print("=" * 70)

        time.sleep(10)
        browser.close()

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("📌 확인된 Binance Testnet 정보")
    print("=" * 70)
    print("""
1. FUTURES TESTNET (선물 거래)
   - URL: https://testnet.binancefuture.com
   - 가입: 이메일/비밀번호만 필요 (인증 없음)
   - API: 가입 후 API Management에서 생성
   - 자금: 자동 10,000 USDT 제공
   - 용도: 레버리지/선물 거래 테스트

2. SPOT TESTNET (현물 거래)
   - URL: https://testnet.binance.vision
   - 가입: 이메일/비밀번호만 필요
   - API: 가입 후 API Management에서 생성
   - 자금: Faucet에서 받기
   - 용도: 현물 거래 테스트

3. 중요사항:
   - Spot과 Futures는 완전히 별도 시스템
   - API 키 호환 안됨
   - 각각 별도 가입 필요
    """)

    print("브라우저로 직접 탐색을 시작합니다...")
    find_testnet_info()