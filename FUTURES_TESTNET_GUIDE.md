# Binance Futures Testnet 가입 가이드

## 📌 Binance Futures Testnet 계정 생성 방법

### 1단계: Futures Testnet 접속
- URL: https://testnet.binancefuture.com/
- 주의: 일반 Binance나 Spot Testnet과 다른 별도 사이트입니다!

### 2단계: 계정 생성
1. 우측 상단 "Register" 클릭
2. 이메일 주소 입력 (실제 이메일 필요 없음, 아무거나 가능)
   - 예: test123@test.com
3. 비밀번호 설정
4. "Create Account" 클릭

### 3단계: 로그인
- 생성한 계정으로 바로 로그인 가능
- 이메일 인증 필요 없음

### 4단계: API 키 발급
1. 로그인 후 우측 상단 프로필 아이콘 클릭
2. "API Management" 선택
3. "Create API" 클릭
4. API 키 라벨 입력 (예: "trading_bot")
5. "Create" 클릭
6. **API Key와 Secret Key 복사 (한 번만 표시됨!)**

### 5단계: 테스트 자금 받기
- Futures Testnet은 자동으로 10,000 USDT 테스트 자금 제공
- 추가 자금이 필요하면 "Faucet" 메뉴 이용

## 🔧 config.json 설정 방법

```json
{
  "exchanges": [
    {
      "name": "binance",
      "api_key": "YOUR_FUTURES_API_KEY",
      "api_secret": "YOUR_FUTURES_SECRET_KEY",
      "testnet": true,
      "enabled": true
    }
  ]
}
```

## 📝 중요 참고사항

1. **Spot과 Futures는 완전히 다른 시스템**
   - Spot Testnet 계정 ≠ Futures Testnet 계정
   - API 키도 서로 호환되지 않음

2. **Futures Testnet 특징**
   - 레버리지 거래 가능 (최대 125x)
   - 숏 포지션 가능
   - 실제 Futures 거래와 동일한 환경

3. **API 엔드포인트**
   - Base URL: https://testnet.binancefuture.com
   - API 경로: /fapi/v1/*, /fapi/v2/*

## 🚀 빠른 시작

1. https://testnet.binancefuture.com/ 접속
2. 계정 생성 (30초)
3. API 키 발급 (1분)
4. config.json에 API 키 입력
5. 시스템 재시작

---

생성한 API 키를 알려주시면 시스템 설정을 업데이트해드리겠습니다!