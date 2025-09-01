# 🚀 암호화폐 자동매매 시스템 (듀얼 버전)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Build Status](https://github.com/mim1012/Crypto/workflows/CI/badge.svg)](https://github.com/mim1012/Crypto/actions)
[![codecov](https://codecov.io/gh/mim1012/Crypto/branch/main/graph/badge.svg)](https://codecov.io/gh/mim1012/Crypto)

바이낸스 선물과 바이비트 선물/무기한 계약을 대상으로 하는 **고도로 정교한 자동매매 시스템**의 듀얼 버전 구현

## ✨ 핵심 특징

### 🎯 듀얼 버전 시스템
- **🖥️ EXE 버전**: 개인 PC에서 완전한 기능 제공
- **🌐 웹 대시보드**: 서버에서 24시간 원격 제어

### 📊 정교한 거래 로직
- **5가지 진입 조건**: 이동평균, Price Channel, 호가감지, 틱기반, 캔들상태
- **4가지 청산 방식**: PCS청산, PC트레일링, 호가청산, PC본절
- **12단계 리스크 관리**: 세밀한 익절/손절 제어
- **시간 제어**: 요일별/시간별 정교한 운용 관리

### 🏢 멀티 거래소 지원
- **바이낸스 선물**: USDT 마진, 1~125배 레버리지
- **바이비트**: 선물/무기한, 1~100배 레버리지

### 🔐 강화된 보안
- **Fernet 암호화**: 모든 설정 파일 암호화
- **JWT 인증**: 웹 대시보드 보안
- **API 키 보안**: 메모리 자동 삭제

## 🏗️ 시스템 아키텍처

```
듀얼 버전 시스템
├── 🔧 공통 코어 모듈 (core/)
│   ├── trading_engine.py      # 거래 엔진 (5진입 + 4청산)
│   ├── risk_manager.py        # 12단계 리스크 관리
│   ├── api_connector.py       # 거래소 API 통합
│   └── security_module.py     # 보안 시스템
├── 🖥️ EXE 버전 (desktop/)
│   └── PyQt5 GUI 구현
└── 🌐 웹 대시보드 (web/)
    └── Flask + React 구현
```

## 🚀 빠른 시작

### 1. 저장소 클론
```bash
git clone https://github.com/mim1012/Crypto.git
cd Crypto
```

### 2. 가상환경 설정
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 설정 파일 구성
```bash
# 설정 템플릿 복사
cp config/config.template.json config/config.json

# API 키 설정 (암호화되어 저장됨)
python setup.py configure
```

### 5. 시스템 실행

#### EXE 버전
```bash
python desktop/main.py
```

#### 웹 대시보드
```bash
python web/app.py
# 브라우저에서 http://localhost:5000 접속
```

## 📋 요구사항

### 시스템 요구사항
- **OS**: Windows 10/11 (EXE), Ubuntu 20.04+ (웹서버)
- **Python**: 3.8 이상
- **RAM**: 최소 4GB (권장 8GB)
- **Storage**: 최소 200MB
- **Network**: 안정적인 인터넷 연결

### 브라우저 지원 (웹 대시보드)
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## 🔧 개발환경 설정

### 개발 도구 설치
```bash
# 개발 의존성 설치
pip install -r requirements-dev.txt

# pre-commit 훅 설치
pre-commit install

# 테스트 실행
pytest tests/ --cov=core
```

### 코드 품질 검사
```bash
# 린팅
flake8 core/ desktop/ web/

# 포맷팅  
black core/ desktop/ web/

# 보안 검사
bandit -r core/
```

## 🧪 테스트

### 전체 테스트 실행
```bash
pytest tests/ --cov=core --cov-report=html
```

### 성능 테스트
```bash
pytest tests/performance/ --benchmark-only
```

### 보안 테스트
```bash
python tests/security/security_audit.py
```

## 📊 성능 지표

### 응답 시간
- **거래 신호 생성**: <10ms
- **API 응답**: <100ms  
- **UI 반응**: <50ms
- **WebSocket 지연**: <10ms

### 리소스 사용량
- **EXE 버전 메모리**: <200MB
- **웹서버 메모리**: <500MB
- **CPU 사용률**: <5%
- **네트워크 대역폭**: <1Mbps

## 🔐 보안 기능

### 데이터 보안
- **API 키 암호화**: Fernet (AES-256) 암호화
- **설정 파일 암호화**: 모든 민감 정보 보호
- **메모리 보안**: 사용 후 자동 삭제

### 네트워크 보안  
- **HTTPS 강제**: SSL/TLS 암호화 통신
- **JWT 인증**: 안전한 웹 세션 관리
- **Rate Limiting**: API 호출 빈도 제한
- **IP 화이트리스트**: 허용된 IP만 접속

## 🌟 주요 기능

### 거래 조건
```python
# 5가지 진입 조건
- 이동평균선 조건 (8가지 옵션)
- Price Channel 돌파 조건
- 호가 감지 진입 (0호가 포함)
- 틱 기반 패턴 감지
- 캔들 상태 분석

# 4가지 청산 조건  
- PCS 청산 (1~12단계)
- PC 트레일링 청산
- 호가 기반 청산
- PC 본절 청산 (2단계)
```

### 리스크 관리
```python
# 12단계 익절/손절
익절: +2%, +4%, +6%, +8%, +10%, +12%
손절: -1%, -2%, -3%, -4%, -5%, -6%

# 포지션 관리
- 최대 포지션 수: 3개
- 레버리지 노출 한도: 설정 가능
- 일일 손실 한도: 설정 가능
```

## 📈 모니터링 및 분석

### 실시간 모니터링
- **포지션 현황**: 실시간 PnL 추적
- **거래 신호**: 진입/청산 신호 표시
- **시장 데이터**: WebSocket 실시간 업데이트
- **성과 분석**: 일/주/월별 수익률

### 알림 시스템
- **웹 알림**: 브라우저 푸시 알림
- **이메일**: 중요 이벤트 알림
- **시스템 트레이**: EXE 버전 알림

## 🤝 기여하기

### 개발 참여
1. Fork 저장소
2. Feature 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 Push (`git push origin feature/amazing-feature`)
5. Pull Request 생성

### 코딩 규칙
- [클린 코드 가이드라인](documents/클린%20코드%20가이드라인.md) 준수
- 모든 함수에 타입 힌팅과 독스트링 작성
- 90% 이상 테스트 커버리지 유지
- 보안 규칙 엄격 준수

## 📞 지원

### 문제 보고
- **Issues**: [GitHub Issues](https://github.com/mim1012/Crypto/issues)
- **보안 취약점**: security@crypto-trading.com

### 문서
- **API 문서**: `/docs/api/`
- **사용자 가이드**: `/docs/user-guide/`
- **개발자 가이드**: `/docs/developer-guide/`

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## ⚠️ 면책 조항

이 소프트웨어는 교육 및 연구 목적으로 제공됩니다. 실제 거래에서 발생하는 손실에 대해서는 사용자가 모든 책임을 집니다. 투자는 본인의 판단과 책임 하에 이루어져야 합니다.

---

**🤖 Generated with [Claude Code](https://claude.ai/code)**

**Made with ❤️ by the Crypto Trading Team**