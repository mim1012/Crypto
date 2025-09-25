#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
암호화폐 거래소 API 연결 테스트 스크립트
바이낸스와 바이비트 API의 연결 상태, 응답 시간, 데이터 품질을 종합적으로 테스트합니다.
"""

import requests
import hmac
import hashlib
import time
import json
import websocket
import threading
from datetime import datetime
import ssl
import os

class QuickConnectionTest:
    """빠른 연결 테스트 (API 키 불필요)"""
    
    @staticmethod
    def test_basic_connectivity():
        """기본 연결성 테스트"""
        print("⚡ 빠른 API 연결 테스트")
        print("=" * 50)
        
        results = {}
        
        # 바이낸스 테스트
        print("\n🟡 바이낸스 연결 테스트...")
        try:
            start_time = time.time()
            response = requests.get("https://fapi.binance.com/fapi/v1/ping", timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                results['binance'] = {
                    'status': '🟢 연결됨',
                    'response_time': f"{round((end_time - start_time) * 1000, 2)}ms"
                }
            else:
                results['binance'] = {
                    'status': '🔴 연결 실패',
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            results['binance'] = {
                'status': '🔴 연결 실패',
                'error': str(e)
            }
        
        print(f"  상태: {results['binance']['status']}")
        if 'response_time' in results['binance']:
            print(f"  응답시간: {results['binance']['response_time']}")
        if 'error' in results['binance']:
            print(f"  오류: {results['binance']['error']}")
        
        # 바이비트 테스트
        print("\n🟠 바이비트 연결 테스트...")
        try:
            start_time = time.time()
            response = requests.get("https://api.bybit.com/v5/market/time", timeout=10)
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                if data.get('retCode') == 0:
                    results['bybit'] = {
                        'status': '🟢 연결됨',
                        'response_time': f"{round((end_time - start_time) * 1000, 2)}ms"
                    }
                else:
                    results['bybit'] = {
                        'status': '🔴 연결 실패',
                        'error': data.get('retMsg', 'Unknown error')
                    }
            else:
                results['bybit'] = {
                    'status': '🔴 연결 실패',
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            results['bybit'] = {
                'status': '🔴 연결 실패',
                'error': str(e)
            }
        
        print(f"  상태: {results['bybit']['status']}")
        if 'response_time' in results['bybit']:
            print(f"  응답시간: {results['bybit']['response_time']}")
        if 'error' in results['bybit']:
            print(f"  오류: {results['bybit']['error']}")
        
        return results
    
    @staticmethod
    def test_market_data():
        """시장 데이터 조회 테스트"""
        print("\n📊 시장 데이터 테스트")
        print("=" * 50)
        
        symbol = "BTCUSDT"
        results = {}
        
        # 바이낸스 현재가
        print(f"\n🟡 바이낸스 {symbol} 현재가 조회...")
        try:
            start_time = time.time()
            response = requests.get(
                f"https://fapi.binance.com/fapi/v1/ticker/price",
                params={'symbol': symbol},
                timeout=10
            )
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                results['binance_price'] = {
                    'status': '✅ 성공',
                    'price': f"${float(data['price']):,.2f}",
                    'response_time': f"{round((end_time - start_time) * 1000, 2)}ms"
                }
            else:
                results['binance_price'] = {
                    'status': '❌ 실패',
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            results['binance_price'] = {
                'status': '❌ 실패',
                'error': str(e)
            }
        
        print(f"  상태: {results['binance_price']['status']}")
        if 'price' in results['binance_price']:
            print(f"  현재가: {results['binance_price']['price']}")
            print(f"  응답시간: {results['binance_price']['response_time']}")
        if 'error' in results['binance_price']:
            print(f"  오류: {results['binance_price']['error']}")
        
        # 바이비트 현재가
        print(f"\n🟠 바이비트 {symbol} 현재가 조회...")
        try:
            start_time = time.time()
            response = requests.get(
                f"https://api.bybit.com/v5/market/tickers",
                params={'category': 'linear', 'symbol': symbol},
                timeout=10
            )
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                if data.get('retCode') == 0 and data['result']['list']:
                    ticker = data['result']['list'][0]
                    results['bybit_price'] = {
                        'status': '✅ 성공',
                        'price': f"${float(ticker['lastPrice']):,.2f}",
                        'mark_price': f"${float(ticker['markPrice']):,.2f}",
                        'response_time': f"{round((end_time - start_time) * 1000, 2)}ms"
                    }
                else:
                    results['bybit_price'] = {
                        'status': '❌ 실패',
                        'error': data.get('retMsg', 'No data')
                    }
            else:
                results['bybit_price'] = {
                    'status': '❌ 실패',
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            results['bybit_price'] = {
                'status': '❌ 실패',
                'error': str(e)
            }
        
        print(f"  상태: {results['bybit_price']['status']}")
        if 'price' in results['bybit_price']:
            print(f"  현재가: {results['bybit_price']['price']}")
            print(f"  마크가격: {results['bybit_price']['mark_price']}")
            print(f"  응답시간: {results['bybit_price']['response_time']}")
        if 'error' in results['bybit_price']:
            print(f"  오류: {results['bybit_price']['error']}")
        
        return results

class AuthenticatedAPITest:
    """인증이 필요한 API 테스트"""
    
    def __init__(self, binance_api_key=None, binance_secret=None, 
                 bybit_api_key=None, bybit_secret=None):
        self.binance_api_key = binance_api_key
        self.binance_secret = binance_secret
        self.bybit_api_key = bybit_api_key
        self.bybit_secret = bybit_secret
    
    def test_binance_auth(self):
        """바이낸스 인증 테스트"""
        if not self.binance_api_key or not self.binance_secret:
            return {
                'status': '⏭️ 건너뜀',
                'reason': 'API 키가 제공되지 않음'
            }
        
        try:
            timestamp = int(time.time() * 1000)
            query_string = f"timestamp={timestamp}"
            signature = hmac.new(
                self.binance_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {'X-MBX-APIKEY': self.binance_api_key}
            params = {'timestamp': timestamp, 'signature': signature}
            
            start_time = time.time()
            response = requests.get(
                "https://fapi.binance.com/fapi/v2/account",
                params=params,
                headers=headers,
                timeout=10
            )
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'status': '✅ 인증 성공',
                    'balance': f"${float(data.get('totalWalletBalance', 0)):,.2f}",
                    'response_time': f"{round((end_time - start_time) * 1000, 2)}ms"
                }
            else:
                return {
                    'status': '❌ 인증 실패',
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                'status': '❌ 인증 실패',
                'error': str(e)
            }
    
    def test_bybit_auth(self):
        """바이비트 인증 테스트"""
        if not self.bybit_api_key or not self.bybit_secret:
            return {
                'status': '⏭️ 건너뜀',
                'reason': 'API 키가 제공되지 않음'
            }
        
        try:
            timestamp = str(int(time.time() * 1000))
            params = {"accountType": "UNIFIED"}
            params_str = json.dumps(params, separators=(',', ':'))
            
            param_str = timestamp + self.bybit_api_key + "5000" + params_str
            signature = hmac.new(
                self.bybit_secret.encode('utf-8'),
                param_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'X-BAPI-API-KEY': self.bybit_api_key,
                'X-BAPI-TIMESTAMP': timestamp,
                'X-BAPI-SIGN': signature,
                'X-BAPI-RECV-WINDOW': '5000',
                'Content-Type': 'application/json'
            }
            
            start_time = time.time()
            response = requests.get(
                "https://api.bybit.com/v5/account/wallet-balance",
                params=params,
                headers=headers,
                timeout=10
            )
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                if data.get('retCode') == 0:
                    wallet_list = data['result']['list']
                    total_equity = wallet_list[0].get('totalEquity', '0') if wallet_list else '0'
                    return {
                        'status': '✅ 인증 성공',
                        'equity': f"${float(total_equity):,.2f}",
                        'response_time': f"{round((end_time - start_time) * 1000, 2)}ms"
                    }
                else:
                    return {
                        'status': '❌ 인증 실패',
                        'error': data.get('retMsg', 'Unknown error')
                    }
            else:
                return {
                    'status': '❌ 인증 실패',
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                'status': '❌ 인증 실패',
                'error': str(e)
            }
    
    def run_auth_tests(self):
        """인증 테스트 실행"""
        print("\n🔐 API 인증 테스트")
        print("=" * 50)
        
        # 바이낸스 인증 테스트
        print("\n🟡 바이낸스 계정 정보 조회...")
        binance_result = self.test_binance_auth()
        print(f"  상태: {binance_result['status']}")
        if 'balance' in binance_result:
            print(f"  지갑 잔고: {binance_result['balance']}")
            print(f"  응답시간: {binance_result['response_time']}")
        if 'reason' in binance_result:
            print(f"  사유: {binance_result['reason']}")
        if 'error' in binance_result:
            print(f"  오류: {binance_result['error']}")
        
        # 바이비트 인증 테스트
        print("\n🟠 바이비트 계정 정보 조회...")
        bybit_result = self.test_bybit_auth()
        print(f"  상태: {bybit_result['status']}")
        if 'equity' in bybit_result:
            print(f"  총 자산: {bybit_result['equity']}")
            print(f"  응답시간: {bybit_result['response_time']}")
        if 'reason' in bybit_result:
            print(f"  사유: {bybit_result['reason']}")
        if 'error' in bybit_result:
            print(f"  오류: {bybit_result['error']}")
        
        return {
            'binance': binance_result,
            'bybit': bybit_result
        }

def main():
    """메인 테스트 실행 함수"""
    print("🚀 암호화폐 거래소 API 연결 테스트")
    print("=" * 60)
    print(f"📅 테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 기본 연결 테스트
    basic_test = QuickConnectionTest()
    connectivity_results = basic_test.test_basic_connectivity()
    market_data_results = basic_test.test_market_data()
    
    # 2. 인증 테스트 (환경 변수에서 API 키 로드)
    binance_api_key = os.getenv('BINANCE_API_KEY')
    binance_secret = os.getenv('BINANCE_SECRET_KEY')
    bybit_api_key = os.getenv('BYBIT_API_KEY')
    bybit_secret = os.getenv('BYBIT_SECRET_KEY')
    
    auth_test = AuthenticatedAPITest(
        binance_api_key=binance_api_key,
        binance_secret=binance_secret,
        bybit_api_key=bybit_api_key,
        bybit_secret=bybit_secret
    )
    auth_results = auth_test.run_auth_tests()
    
    # 3. 결과 요약
    print("\n📊 테스트 결과 요약")
    print("=" * 60)
    
    # 연결 상태 요약
    binance_connected = "🟢" if "🟢" in connectivity_results['binance']['status'] else "🔴"
    bybit_connected = "🟢" if "🟢" in connectivity_results['bybit']['status'] else "🔴"
    
    print(f"\n📡 기본 연결:")
    print(f"  🟡 바이낸스: {binance_connected}")
    print(f"  🟠 바이비트: {bybit_connected}")
    
    # 시장 데이터 상태
    binance_market = "✅" if "✅" in market_data_results['binance_price']['status'] else "❌"
    bybit_market = "✅" if "✅" in market_data_results['bybit_price']['status'] else "❌"
    
    print(f"\n💹 시장 데이터:")
    print(f"  🟡 바이낸스: {binance_market}")
    print(f"  🟠 바이비트: {bybit_market}")
    
    # 인증 상태
    binance_auth = "✅" if "✅" in auth_results['binance']['status'] else "❌" if "❌" in auth_results['binance']['status'] else "⏭️"
    bybit_auth = "✅" if "✅" in auth_results['bybit']['status'] else "❌" if "❌" in auth_results['bybit']['status'] else "⏭️"
    
    print(f"\n🔐 인증 테스트:")
    print(f"  🟡 바이낸스: {binance_auth}")
    print(f"  🟠 바이비트: {bybit_auth}")
    
    # 전체 상태 판정
    all_basic_connected = binance_connected == "🟢" and bybit_connected == "🟢"
    all_market_working = binance_market == "✅" and bybit_market == "✅"
    
    print(f"\n🎯 전체 상태:")
    if all_basic_connected and all_market_working:
        print("  ✅ 모든 기본 기능이 정상 작동합니다!")
        print("  🚀 자동매매 시스템 구현 준비 완료!")
    elif all_basic_connected:
        print("  ⚠️  기본 연결은 정상이지만 일부 기능에 문제가 있습니다.")
    else:
        print("  ❌ 연결에 문제가 있습니다. 네트워크나 API 상태를 확인해주세요.")
    
    # API 키 안내
    if not any([binance_api_key, binance_secret, bybit_api_key, bybit_secret]):
        print(f"\n💡 인증 테스트를 위해 환경 변수를 설정해주세요:")
        print(f"  export BINANCE_API_KEY='your_api_key'")
        print(f"  export BINANCE_SECRET_KEY='your_secret_key'")
        print(f"  export BYBIT_API_KEY='your_api_key'")
        print(f"  export BYBIT_SECRET_KEY='your_secret_key'")
    
    print(f"\n✨ 테스트 완료!")
    
    return {
        'connectivity': connectivity_results,
        'market_data': market_data_results,
        'authentication': auth_results,
        'timestamp': datetime.now().isoformat()
    }

if __name__ == "__main__":
    try:
        results = main()
        
        # 결과를 JSON 파일로 저장
        with open('api_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 상세 결과가 'api_test_results.json' 파일로 저장되었습니다.")
        
    except KeyboardInterrupt:
        print(f"\n\n⏹️  사용자에 의해 테스트가 중단되었습니다.")
    except Exception as e:
        print(f"\n\n❌ 테스트 실행 중 오류가 발생했습니다: {e}")
