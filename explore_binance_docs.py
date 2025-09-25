#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Binance Derivatives 문서 탐색
Playwright를 사용한 자동 탐색
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time

def explore_binance_derivatives():
    with sync_playwright() as p:
        # Headless 모드로 브라우저 실행
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()

        print("=" * 70)
        print("Binance Derivatives 문서 탐색 시작")
        print("=" * 70)

        try:
            # 메인 페이지 접속
            print("\n1. 메인 페이지 접속...")
            page.goto("https://developers.binance.com/docs/derivatives", timeout=30000)
            time.sleep(2)

            # 페이지 제목 확인
            title = page.title()
            print(f"   페이지 제목: {title}")

            # Testnet 관련 링크 찾기
            print("\n2. Testnet 관련 링크 검색...")

            # 텍스트로 링크 찾기
            testnet_links = []

            # "testnet" 텍스트가 포함된 모든 링크 찾기
            links = page.locator("a").all()
            for link in links[:50]:  # 처음 50개만 확인
                try:
                    text = link.text_content()
                    href = link.get_attribute("href")
                    if text and href:
                        text_lower = text.lower()
                        if "testnet" in text_lower or "test" in text_lower:
                            testnet_links.append({
                                "text": text.strip(),
                                "href": href
                            })
                            print(f"   - 발견: {text.strip()}")
                            print(f"     링크: {href}")
                except:
                    continue

            # 메뉴 항목 확인
            print("\n3. 사이드바 메뉴 항목 검색...")

            # 사이드바 메뉴 찾기
            sidebar_items = page.locator("nav a, aside a, [role='navigation'] a").all()
            menu_items = []

            for item in sidebar_items[:30]:
                try:
                    text = item.text_content()
                    href = item.get_attribute("href")
                    if text and href:
                        menu_items.append({
                            "text": text.strip(),
                            "href": href
                        })
                        if "test" in text.lower() or "environment" in text.lower():
                            print(f"   - 메뉴: {text.strip()}")
                            print(f"     링크: {href}")
                except:
                    continue

            # "Getting Started" 섹션 찾기
            print("\n4. Getting Started 섹션 탐색...")
            getting_started = page.locator("text=/.*Getting Started.*/i").all()
            for gs in getting_started[:5]:
                try:
                    parent = gs.locator("..")
                    links = parent.locator("a").all()
                    for link in links[:5]:
                        text = link.text_content()
                        href = link.get_attribute("href")
                        if text and href:
                            print(f"   - {text.strip()}: {href}")
                except:
                    continue

            # Environment 또는 Setup 관련 페이지 찾기
            print("\n5. Environment/Setup 페이지 검색...")

            # 직접 URL 시도
            testnet_urls = [
                "/docs/derivatives/testnet",
                "/docs/derivatives/guide/testnet",
                "/docs/derivatives/getting-started/testnet",
                "/docs/derivatives/environment",
                "/docs/derivatives/setup"
            ]

            base_url = "https://developers.binance.com"
            for url_path in testnet_urls:
                full_url = base_url + url_path
                print(f"\n   시도: {full_url}")
                try:
                    response = page.goto(full_url, timeout=5000)
                    if response and response.status == 200:
                        print(f"   ✅ 페이지 발견: {full_url}")
                        page_title = page.title()
                        print(f"   제목: {page_title}")

                        # 페이지 내용 일부 추출
                        content = page.locator("main, article, .content").first.text_content()
                        if content and "testnet" in content.lower():
                            print("   Testnet 정보 포함!")
                            # Testnet URL 찾기
                            if "testnet.binancefuture.com" in content:
                                print("   ✅ Futures Testnet URL 발견: https://testnet.binancefuture.com")
                            if "testnet.binance.vision" in content:
                                print("   ✅ Spot Testnet URL 발견: https://testnet.binance.vision")
                except:
                    print(f"   ❌ 404 또는 접근 불가")

            # 스크린샷 저장 (디버깅용)
            print("\n6. 현재 페이지 스크린샷 저장...")
            page.screenshot(path="binance_docs_page.png")
            print("   스크린샷 저장: binance_docs_page.png")

        except Exception as e:
            print(f"\n오류 발생: {e}")

        finally:
            browser.close()

        print("\n" + "=" * 70)
        print("탐색 완료")
        print("=" * 70)

if __name__ == "__main__":
    explore_binance_derivatives()

    print("\n" + "=" * 70)
    print("💡 Binance Futures Testnet 정보 (공식)")
    print("=" * 70)
    print("\n알려진 Testnet URL:")
    print("- Futures Testnet: https://testnet.binancefuture.com")
    print("- Spot Testnet: https://testnet.binance.vision")
    print("\n가입 방법:")
    print("1. https://testnet.binancefuture.com 직접 접속")
    print("2. 'Register' 클릭")
    print("3. 이메일/비밀번호 입력 (가짜 이메일 가능)")
    print("4. API Management에서 API 키 생성")
    print("\n참고: Testnet은 메인 Binance 사이트와 완전히 별도 시스템입니다!")
    print("=" * 70)