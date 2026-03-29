"""WRDS Compustat 테이블/필드 레지스트리."""

# ── 테이블 경로 ───────────────────────────────────────────────────────────────
FUNDA_TABLE   = "comp.funda"            # 연간 재무제표
COMPANY_TABLE = "comp.company"          # 기업 헤더 (gsector, tic 포함)
FUNDQ_TABLE   = "comp.fundq"            # 분기 재무제표
SECD_TABLE    = "comp.g_secd"           # 일별 증권 데이터
CRSP_DSF      = "crsp.dsf"             # CRSP 일별 주식 파일
LINK_TABLE    = "crsp.ccmxpf_lnkhist"  # PERMNO ↔ GVKEY 연결 테이블

# ── 공통 식별자 필드 (comp.funda) ─────────────────────────────────────────────
KEY_FIELDS = ["f.gvkey", "f.datadate", "f.fyear", "f.indfmt", "f.consol", "f.popsrc", "f.datafmt", "f.tic"]

# ── 섹터 필드 (comp.company JOIN) — tic은 comp.funda에 있어서 KEY_FIELDS에 포함 ──
COMPANY_FIELDS = ["c.gsector"]   # GICS 섹터코드

# ── 재무 지표 필드 (comp.funda) ───────────────────────────────────────────────
FINANCIAL_FIELDS = [
    "f.prcc_f",   # 회계연도 말 주가
    "f.csho",     # 발행 주식 수 (백만 주)
    "f.ceq",      # 주주자본 (장부가)
    "f.ni",       # 순이익
    "f.epsfx",    # 희석 EPS
    "f.oancf",    # 영업활동 현금흐름
    "f.capx",     # 자본적 지출
    "f.mkvalt",   # 시가총액
    "f.dltt",     # 장기 부채
    "f.dlc",      # 단기 부채
    "f.sale",     # 매출액
]

# ── 파생 지표 계산 정의 ───────────────────────────────────────────────────────
# 구조: "지표명": ("분자 표현식", "분모 표현식")
# 실제 계산: numerator / denominator
# _lag4 = 4분기 전 값 (YoY 비교용)
#
DERIVED_FIELDS: dict[str, tuple[str, str]] = {

    # PBR (주가순자산비율) — 낮을수록 저평가
    # 계산: 주가 / 주당순자산 = prcc_f / (ceq / csho)
    # 해석: 시장이 장부가치의 몇 배로 기업을 평가하는가
    "pbr": (
        "prcc_f",        # 분자: 회계연도 말 주가
        "ceq / csho",    # 분모: 주주자본 ÷ 발행주식수 = 주당순자산(BPS)
    ),

    # ROE (자기자본이익률) — 높을수록 자본 효율적
    # 계산: 순이익 / 주주자본
    # 해석: 주주가 투자한 자본 1원으로 얼마의 이익을 냈는가
    "roe": (
        "ni",            # 분자: 순이익 (Net Income)
        "ceq",           # 분모: 주주자본 (Common Equity)
    ),

    # EPS 변화율 YoY (주당순이익 성장률) — 높을수록 이익 성장
    # 계산: (현재 EPS - 4분기 전 EPS) / |4분기 전 EPS|
    # 해석: 1년 전 대비 주당순이익이 얼마나 증가/감소했는가
    "eps_change_rate": (
        "epsfx - epsfx_lag4",   # 분자: 현재 희석 EPS - 4분기 전 희석 EPS
        "abs(epsfx_lag4)",       # 분모: 4분기 전 EPS 절댓값 (부호 무관 비율 계산)
    ),

    # FCF Yield (잉여현금흐름 수익률) — 높을수록 현금 창출력 우수
    # 계산: (영업현금흐름 - 자본지출) / 시가총액
    # 해석: 시가총액 대비 실제로 창출되는 잉여현금의 비율
    "fcf_yield": (
        "oancf - capx",  # 분자: 영업현금흐름 - 자본지출 = 잉여현금흐름(FCF)
        "mkvalt",        # 분모: 시가총액 (Market Value of Total Assets)
    ),

    # D/E Ratio (부채비율) — 낮을수록 재무 안정적
    # 계산: (장기부채 + 단기부채) / 주주자본
    # 해석: 자기자본 1원당 몇 원의 부채를 사용하고 있는가
    "de_ratio": (
        "dltt + dlc",    # 분자: 장기부채(Long-term Debt) + 단기부채(Debt in Current Liabilities)
        "ceq",           # 분모: 주주자본 (Common Equity)
    ),

    # 매출 성장률 YoY — 높을수록 탑라인 성장
    # 계산: (현재 매출 - 4분기 전 매출) / 4분기 전 매출
    # 해석: 1년 전 대비 매출액이 얼마나 증가/감소했는가
    "revenue_growth": (
        "sale - sale_lag4",  # 분자: 현재 매출 - 4분기 전 매출
        "sale_lag4",         # 분모: 4분기 전 매출 (기준값)
    ),

    # Earnings Yield (이익 수익률) — 높을수록 저평가 (PER의 역수)
    # 계산: 희석 EPS / 주가 = 1 / PER
    # 해석: 주가 1원당 얼마의 이익이 귀속되는가. PER 15 → Earnings Yield 6.7%
    "earnings_yield": (
        "epsfx",         # 분자: 희석 EPS (Diluted EPS)
        "prcc_f",        # 분모: 회계연도 말 주가
    ),
}

# ── 필터 조건 (Compustat 표준 필터) ──────────────────────────────────────────
STANDARD_FILTERS = {
    "indfmt":  "INDL",
    "consol":  "C",
    "popsrc":  "D",
    "datafmt": "STD",
}
