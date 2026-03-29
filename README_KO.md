# Multi-Horizon Investment Decision Support System (MHIDSS)

> **Fundamental × Macro × Technical** 3개 데이터를 통합해
> **Short / Mid / Long 시계열별 Entry Score(0~100)**를 산출하고
> 다크 테마 브라우저 대쉬보드로 출력하는 투자 의사결정 지원 시스템

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [데이터 흐름도](#2-데이터-흐름도)
3. [핵심 로직 — Entry Score 계산 공식](#3-핵심-로직--entry-score-계산-공식)
4. [설계 의도](#4-설계-의도)
5. [현재 사용 중인 지표 목록](#5-현재-사용-중인-지표-목록)
6. [수정 가이드](#6-수정-가이드)
7. [빠른 시작](#7-빠른-시작)
8. [프로젝트 구조](#8-프로젝트-구조)
9. [의존성](#9-의존성)

---

## 1. 시스템 개요

```
입력: 티커 심볼 또는 회사명  +  분석 기준일
출력: Short / Mid / Long 시계열별 Entry Score + 시그널  →  브라우저 대쉬보드
```

| 시계열 | 투자 호흡 | 지배적 데이터 | 의미 |
|--------|-----------|--------------|------|
| **Short** | 1~4주 | Technical (70%) | 단기 가격 모멘텀 기반 진입 타이밍 |
| **Mid** | 1~6개월 | 균등 (35/30/35%) | 이익 사이클 + 기술적 흐름 복합 판단 |
| **Long** | 6~24개월 | Macro (50%) + Fundamental (45%) | 매크로 레짐 + 내재가치 기반 포지션 구축 |

**시그널 분류:**

| Entry Score | 시그널 |
|-------------|--------|
| ≥ 70 | `STRONG BUY` |
| ≥ 55 | `BUY` |
| ≥ 45 | `NEUTRAL` |
| ≥ 30 | `SELL` |
| < 30 | `STRONG SELL` |

> 임계값은 `.env` 파일의 `SIGNAL_THRESHOLD_*` 변수로 조정 가능.

---

## 2. 데이터 흐름도

```mermaid
flowchart TD
    subgraph INPUT["데이터 레이어  (data/)"]
        A1["FREDFetcher\nfred_fetcher.py\n금리·CPI·실업률 등 10개 시리즈"]
        A2["WRDSFetcher\nwrds_fetcher.py\nPBR·EPS·ROE 등 Compustat"]
        A3["TechnicalFetcher\ntechnical_fetcher.py\nRSI·MACD·SMA 등 8개 (ta 라이브러리)"]
        CACHE["DiskCache  (Parquet + TTL)\nFRED: 24h  /  WRDS: 168h  /  Tech: 4h"]
        A1 <-->|캐시 히트/미스| CACHE
        A2 <-->|캐시 히트/미스| CACHE
        A3 <-->|캐시 히트/미스| CACHE
    end

    subgraph NORM["정규화  (engine/normalizers/)"]
        N1["MinMaxNormalizer\n범위 고정 지표 (RSI, Bollinger %B)"]
        N2["ZScoreNormalizer\n분포형 지표 (FEDFUNDS, UNRATE)"]
        N3["PercentileRankNormalizer\n상대 순위 지표 (PBR, ROE, FCF Yield)"]
        WARN["fit() = as_of_date 이전만\n→ Look-ahead Bias 원천 차단"]
    end

    subgraph SCORE["스코어러  (engine/scorers/)"]
        S1["MacroScorer"]
        S2["FundamentalScorer\n(섹터 내 z-score)"]
        S3["TechnicalScorer"]
    end

    subgraph HORIZON["시계열  (engine/horizons/)"]
        H1["Short: 0.20·G_M + 0.10·G_F + 0.70·G_T"]
        H2["Mid:   0.35·G_M + 0.30·G_F + 0.35·G_T"]
        H3["Long:  0.50·G_M + 0.45·G_F + 0.05·G_T"]
    end

    subgraph OUTPUT["출력  (reports/ + 브라우저)"]
        F3["HTML 대쉬보드\n3×3 분석 그리드 + Entry Score 카드\n+ Score Guide → 브라우저 자동 오픈"]
        CLI["터미널 rich 테이블"]
    end

    A1 --> N2
    A2 --> N3
    A3 --> N1
    N1 & N2 & N3 --> S1 & S2 & S3
    S1 & S2 & S3 --> H1 & H2 & H3
    H1 & H2 & H3 --> F3 & CLI
```

---

## 3. 핵심 로직 — Entry Score 계산 공식

### 3-1. 전체 수식 (3단계)

```
Step 1.  각 원시 지표값 → [0, 100] 정규화
         score_i = Normalizer_i.transform(raw_value_i)

Step 2.  그룹 내 가중 평균  (지표 단위 → 그룹 단위)
         G_M = Σ w_macro[i]   × score_i    (매크로 그룹)
         G_F = Σ w_fund[j]    × score_j    (펀더멘탈 그룹)
         G_T = Σ w_tech[k]    × score_k    (기술적 그룹)

Step 3.  시계열별 교차 그룹 합산  (그룹 단위 → 최종 점수)
         EntryScore = W_macro × G_M  +  W_fund × G_F  +  W_tech × G_T
```

### 3-2. 가중치 행렬

**그룹 간 가중치** — `config/weights.py` 9~11행

| 그룹 | Short | Mid | Long |
|------|-------|-----|------|
| Macro | 0.20 | 0.35 | **0.50** |
| Fundamental | 0.10 | 0.30 | **0.45** |
| Technical | **0.70** | 0.35 | 0.05 |

**매크로 그룹 내 가중치** — `config/weights.py` 16~45행

| 지표 | Short | Mid | Long |
|------|-------|-----|------|
| YIELD_CURVE_SPREAD | 0.15 | 0.20 | 0.25 |
| FEDFUNDS | 0.15 | 0.20 | 0.20 |
| CREDIT_SPREAD | 0.20 | 0.15 | 0.15 |
| CPIAUCSL (YoY) | 0.10 | 0.15 | 0.15 |
| PCEPILFE (YoY) | 0.10 | 0.10 | 0.10 |
| UNRATE | 0.10 | 0.10 | 0.10 |
| ICSA | 0.15 | 0.05 | 0.00 |
| M2SL (YoY) | 0.05 | 0.05 | 0.05 |

**펀더멘탈 그룹 내 가중치** — `config/weights.py` 49~77행

| 지표 | Short | Mid | Long |
|------|-------|-----|------|
| eps_change_rate | 0.30 | 0.25 | 0.15 |
| roe | 0.15 | 0.20 | 0.25 |
| fcf_yield | 0.15 | 0.20 | 0.25 |
| pbr | 0.10 | 0.15 | 0.20 |
| revenue_growth | 0.15 | 0.10 | 0.10 |
| de_ratio | 0.10 | 0.05 | 0.05 |
| earnings_yield | 0.05 | 0.05 | 0.00 |

> 펀더멘탈 스코어는 **섹터 내 z-score 정규화** 방식 사용 (Barra USE4 / AQR QMJ 방법론 기반).
> 동종 GICS 섹터 기업들과만 비교 (11개 섹터 지원). 섹터별 가중치: `config/normalization.py`의 `SECTOR_FUNDAMENTAL_WEIGHTS`.

**기술적 그룹 내 가중치** — `config/weights.py` 80~111행

| 지표 | Short | Mid | Long |
|------|-------|-----|------|
| rsi_14 | 0.20 | 0.15 | 0.00 |
| macd_histogram | 0.20 | 0.20 | 0.10 |
| sma_ratio | 0.10 | 0.20 | 0.40 |
| stoch_k | 0.15 | 0.10 | 0.00 |
| bb_pct_b | 0.15 | 0.10 | 0.00 |
| obv_slope | 0.10 | 0.10 | 0.20 |
| atr_norm | 0.05 | 0.05 | 0.15 |
| roc | 0.05 | 0.10 | 0.15 |

### 3-3. 정규화 방법 3종

| 방법 | 언제 쓰나 | 공식 |
|------|-----------|------|
| **MinMax** | 범위가 알려진 지표 (RSI 0~100, Bollinger %B 0~1) | `(x − min) / (max − min) × 100` |
| **Z-Score** | 정규분포형 지표 (금리, 실업률, MACD) | `clip((z + 3) / 6 × 100, 0, 100)` |
| **Percentile** | 상대적 위치가 중요한 지표 (PBR, ROE, FCF Yield) | `rank(x) / N × 100` |

- **방향성 반전** (`invert=True`): 높을수록 나쁜 지표는 `100 − score`로 반전
- 각 지표의 방법·방향·윈도우: `config/normalization.py`

### 3-4. 합산 공식이 있는 코드 위치

| 수정하고 싶은 것 | 파일 | 라인 |
|-----------------|------|------|
| 그룹 간 비율 (Short의 Tech 70% 조정 등) | `config/weights.py` | 9~11 |
| 매크로 지표별 비중 | `config/weights.py` | 16~45 |
| 펀더멘탈 지표별 비중 | `config/weights.py` | 49~77 |
| 기술적 지표별 비중 | `config/weights.py` | 80~111 |
| 합산 공식 자체 | `engine/horizons/short_term.py` | 41 |
| 시그널 임계값 | `engine/horizons/base.py` 또는 `.env` | 21~30 |
| 정규화 방법 변경 | `config/normalization.py` | 해당 지표 행 |

---

## 4. 설계 의도

### 왜 파일을 이렇게 세분화했는가

각 파일은 **"변경되는 이유"가 하나**입니다.

```
config/weights.py              ← 투자 철학이 바뀔 때만 수정
config/normalization.py        ← 정규화 방법론이 바뀔 때만 수정
data/fetchers/wrds_fetcher.py  ← WRDS 쿼리 구조가 바뀔 때만 수정
engine/normalizers/zscore.py   ← Z-Score 알고리즘 자체를 바꿀 때만 수정
engine/horizons/short_term.py  ← Short-term 합산 로직만 바꿀 때만 수정
```

### Look-ahead Bias 차단

백테스트의 가장 흔한 오류는 미래 데이터로 현재를 정규화하는 것입니다.
`BaseNormalizer.fit()`은 반드시 `as_of_date` **이전** 데이터만 받도록 API 계약이 걸려 있습니다.

```python
# engine/scorers/macro_scorer.py
history = self._historical.loc[:as_of_date, indicator_id].dropna()
normalizer.fit(history)  # ← as_of_date 이전만
```

### 누락 지표 처리

- **0점 처리 금지** → 인위적 패널티 발생
- 대신 `INSUFFICIENT_DATA` 플래그 후 해당 지표의 가중치를 **같은 그룹 내 나머지 지표에 비례 재분배**

---

## 5. 현재 사용 중인 지표 목록

### 매크로 (FRED API) — 10개

| 지표명 | FRED ID | 정규화 | 방향 |
|--------|---------|--------|------|
| 연방기금금리 | `FEDFUNDS` | Z-Score | 높을수록 나쁨 ↓ |
| 10년 국채 수익률 | `DGS10` | Z-Score | 높을수록 나쁨 ↓ |
| 2년 국채 수익률 | `DGS2` | Z-Score | 높을수록 나쁨 ↓ |
| 장단기 금리차 (10Y−2Y) | 파생 | MinMax (−3~+4%) | 높을수록 좋음 ↑ |
| CPI YoY | `CPIAUCSL` | MinMax (0~10%) | 높을수록 나쁨 ↓ |
| 근원 PCE YoY | `PCEPILFE` | MinMax (0~8%) | 높을수록 나쁨 ↓ |
| 실업률 | `UNRATE` | Z-Score | 높을수록 나쁨 ↓ |
| 신규 실업수당 청구 | `ICSA` | Z-Score | 높을수록 나쁨 ↓ |
| M2 통화량 YoY | `M2SL` | Z-Score | 높을수록 좋음 ↑ |
| BAA−AAA 크레딧 스프레드 | 파생 | MinMax (0~5%) | 높을수록 나쁨 ↓ |

### 펀더멘탈 (WRDS Compustat) — 7개 (섹터 내 z-score)

| 지표명 | 계산식 | Compustat 필드 | 정규화 |
|--------|--------|----------------|--------|
| PBR | `prcc_f / (ceq / csho)` | `prcc_f, ceq, csho` | Percentile ↓ |
| EPS 변화율 (YoY) | `(eps_t − eps_{t-1}) / \|eps_{t-1}\|` | `epsfx` | Z-Score ↑ |
| ROE | `ni / ceq` | `ni, ceq` | Percentile ↑ |
| FCF Yield | `(oancf − capx) / mkvalt` | `oancf, capx, mkvalt` | Percentile ↑ |
| 부채비율 (D/E) | `(dltt + dlc) / ceq` | `dltt, dlc, ceq` | Percentile ↓ |
| 매출 성장률 (YoY) | `(sale_t − sale_{t-1}) / sale_{t-1}` | `sale` | Z-Score ↑ |
| Earnings Yield | `epsfx / prcc_f` | `epsfx, prcc_f` | Percentile ↑ |

> **Point-in-time**: `datadate ≤ as_of_date`인 데이터만 사용 (look-ahead bias 차단).
> **1~99% 윈저화** 적용 후 섹터 mean/std 계산.

### 기술적 지표 (yfinance + ta 라이브러리) — 8개, 3개 해상도

| 지표명 | 파라미터 | 정규화 | 특이사항 |
|--------|---------|--------|---------|
| RSI | 14일 | MinMax (0~100) | **V자형 비선형** 스코어링 |
| MACD Histogram | 12/26/9 | Z-Score | |
| SMA Ratio | 일봉: 50/200 · 주봉: 20/100 · 월봉: 10/40 | MinMax (0.85~1.15) | |
| Stochastic %K | 14/3 | MinMax (0~100) | |
| Bollinger %B | 20일/2σ | MinMax (0~1) | |
| OBV Slope | 20봉 선형 기울기 | Z-Score | |
| ATR (정규화) | ATR(14)/Close | Z-Score | 변동성 — 높으면 나쁨 ↓ |
| ROC | 10일 | Z-Score | |

> **RSI V자형**: RSI=30(과매도) → 100점, RSI=70(과매수) → 0점, RSI=50 → 50점.
> 구현: `engine/scorers/technical_scorer.py` 11~16행

---

## 6. 수정 가이드

### A. 펀더멘탈 지표 추가/변경

1. `config/wrds_fields.py` — 새 필드 추가
2. `config/normalization.py` — `FUNDAMENTAL_NORM`에 정규화 설정 등록
3. `config/weights.py` — `FUNDAMENTAL_INDICATOR_WEIGHTS`에 가중치 추가 (합산 1.0 유지)
4. `data/fetchers/wrds_fetcher.py` — `_compute_derived()`에 계산 로직 추가

### B. 그룹 간 가중치 변경

`config/weights.py` **9~11행**만 수정. **합계 반드시 1.0**.

### C. 매크로 지표 추가

1. `config/fred_series.py` — 시리즈 ID 상수 추가
2. `config/normalization.py` — `MACRO_NORM`에 정규화 설정 추가
3. `config/weights.py` — `MACRO_INDICATOR_WEIGHTS`에 비중 추가

### D. 시그널 임계값 변경

`.env` 파일 직접 수정:
```
SIGNAL_THRESHOLD_STRONG_BUY=70
SIGNAL_THRESHOLD_BUY=55
SIGNAL_THRESHOLD_NEUTRAL=45
SIGNAL_THRESHOLD_SELL=30
```

### E. 정규화 방법 변경

```python
# config/normalization.py
# 예: PBR을 Percentile → Z-Score로
FUNDAMENTAL_NORM["pbr"] = NormConfig("zscore", invert=True, window_years=5)
```

---

## 7. 빠른 시작

### 환경 설정

```bash
pip install -e ".[dev]"
cp .env.example .env
# .env에 FRED_API_KEY, WRDS_USERNAME, WRDS_PASSWORD 입력
```

### 실행

```bash
# 단일 티커 — 브라우저 자동 오픈
python main.py run AAPL

# 다중 티커 — 종목당 탭 하나씩
python main.py run AAPL MSFT NVDA GOOGL

# 회사명도 지원 (yfinance Search로 자동 변환)
python main.py run "Apple" "Microsoft" "엔비디아"

# 특정 날짜 기준
python main.py run AAPL --date 2024-01-01

# Short-term만
python main.py run AAPL --horizon short

# 브라우저 자동 오픈 비활성화
python main.py run AAPL --no-browser

# 연결 상태 확인
python main.py check-connections
```

### 테스트

```bash
pytest tests/unit/ -v
pytest tests/integration/test_fred_live.py -v
```

---

## 8. 프로젝트 구조

```
mhidss/
│
├── config/
│   ├── weights.py               ★ 가중치 행렬 (투자 철학의 핵심)
│   ├── normalization.py         ★ 지표별 정규화 전략 + 섹터별 펀더멘탈 가중치
│   ├── fred_series.py
│   ├── wrds_fields.py
│   └── settings.py
│
├── data/
│   ├── fetchers/
│   │   ├── fred_fetcher.py
│   │   ├── wrds_fetcher.py
│   │   └── technical_fetcher.py  (yfinance + ta 라이브러리)
│   ├── cache/disk_cache.py
│   └── models/
│
├── engine/
│   ├── normalizers/
│   │   ├── base.py              ★ fit/transform 계약 (look-ahead bias 차단)
│   │   ├── minmax.py, zscore.py, percentile.py
│   ├── scorers/
│   │   ├── macro_scorer.py
│   │   ├── fundamental_scorer.py  (섹터 내 z-score)
│   │   └── technical_scorer.py
│   ├── horizons/
│   │   ├── base.py               HorizonResult 데이터클래스
│   │   ├── short_term.py        ★ Short 합산 공식
│   │   ├── mid_term.py          ★ Mid 합산 공식
│   │   └── long_term.py         ★ Long 합산 공식
│   └── entry_score.py            전체 파이프라인 오케스트레이터
│
├── reports/
│   └── formatters/html_formatter.py  다크 테마 대쉬보드 (3×3 그리드 + Score Guide)
│
├── main.py                       CLI (티커·회사명 입력, 다중 종목, 브라우저 자동 오픈)
├── pyproject.toml
├── .env.example
└── README_KO.md                  ← 이 파일 (한글 전용)
```

---

## 9. 의존성

| 라이브러리 | 용도 |
|-----------|------|
| `fredapi` | FRED API 래퍼 |
| `wrds` | WRDS PostgreSQL 연결 |
| `pandas`, `numpy` | 데이터 처리 |
| `polars` | 고성능 DataFrame (내부 파이프라인) |
| `ta` | 기술적 지표 계산 (RSI, MACD, Bollinger 등) |
| `yfinance` | 가격 데이터 + 회사명→티커 변환 |
| `pydantic` | 런타임 데이터 검증 |
| `structlog` | 구조화 로깅 |
| `typer`, `rich` | CLI & 터미널 출력 |
| `jinja2` | HTML 리포트 템플릿 |
| `pyarrow` | Parquet 캐시 직렬화 |
| `python-dotenv` | 환경변수 관리 |
| `tenacity` | 지수 백오프 API 재시도 |
