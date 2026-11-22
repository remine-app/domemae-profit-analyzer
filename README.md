# Domemae Profit Analyzer

도매매 공급상품을 **읽기 전용 Open API**로 조회하는 초기 사업성 검증 프로젝트입니다.

## 구현
- getItemList v4.1 상품 검색, CSV/JSON 내보내기
- GitHub Actions 수동 수집, 다운로드 가능한 아티팩트
- Python 표준 라이브러리, 오프라인 단위 테스트
- 현재 **실제 매출·수익률 검증 전**

> 이전에 채팅에 노출된 API 키는 반드시 폐기하고 새로운 키로 교체하세요.

## GitHub Actions 실행 방법
1. 도매매에서 새 API 키를 발급받습니다.
2. GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret
3. 이름: `DOMEMAE_API_KEY`, 값: 새 API 키. 키를 파일이나 채팅에 붙이지 않습니다.
4. PR을 검토한 뒤 main에 병합합니다.
5. Actions → Collect Domemae sample → Run workflow → 검색어 및 수집 수량(처음에는 30개) 입력.
6. 성공한 실행의 Artifacts에서 `domemae-data`를 내려받고 CSV와 JSON을 확인합니다.

## 로컬 실행
Python 3.9+에서 `DOMEMAE_API_KEY` 환경변수 설정 후:
```bash
python collect.py --keyword "케이블 정리" --limit 30
python -m unittest discover -s tests -v
```
파일은 `output/`에 저장되고 Git에서 제외됩니다. API 키가 로그나 출력파일에 포함되지 않도록 주의하세요.

## 주의
- 이 코드는 **실서버 인증/API 응답 테스트 전**입니다. 조회 실패 시 로그를 기반으로 응답 구조를 확인해야 합니다.
- API 데이터는 공급 측 데이터입니다. 상품 상세 옵션별 공급가·배송비, 경쟁 판매가격, 판매수수료, 반품비, 배송 책임 등을 결합해야 사업성을 판단할 수 있습니다.
- 상품 등록/주문처리 자동화는 아직 구현하지 않았습니다.
- 데이터를 공개 저장소에 업로드하지 마세요.

공식 문서: [목록](https://docs.channel.io/domeggook_api/ko/articles/43780628) · [상세](https://docs.channel.io/domeggook_api/ko/articles/933abc24)


## 2단계: 특정 카테고리를 미리 고르지 않는 폭넓은 상품 발굴

- GitHub Actions → **Broad product discovery** → Run workflow
- 기본 설정: 검색어 18개 × 정렬 2종(인기·최근등록), 검색당 100개, 상세 30개, 요청 최대 75회
- 검색어는 8개 생활 분야를 넓게 탐색하기 위한 **임시 가설**입니다. 수요가 검증된 카테고리 목록이 아닙니다.
- 결과: `catalog_*.csv` (중복 제거 공급상품), `detail_candidates_*.csv` (상세 검토 후보), `summary_*.json` (수집 상태/오류)
- 분산된 카테고리에서 상세 후보를 뽑습니다. `screen_score`는 운영 난도 신호이며 수익성·인기도를 의미하지 않습니다.
- API는 상세에서 `price.supply`, `qty.inventory`, `deli.supply`, `desc.license.usable` 등을 조회합니다. 옵션별 추가금, 비정형 배송비는 반드시 수동 검토합니다.
- 현재는 **공개 경쟁 판매가격과 실제 판매량이 없어서 실마진 순위가 아닙니다.**

### 시장가격 확인 후 공헌이익 계산

동일 상품·동일 옵션 여부를 직접 검증한 뒤 `market.csv`를 준비합니다. 필수 열은 다음과 같습니다.

```csv
no,marketplace,competitor_url,market_sale_price,market_shipping_collected,platform_fee_pct,other_cost,checked_at,comparison_note
```

`other_cost`에는 광고·반품 충당 및 기타 주문당 비용을 합산합니다. 공란이면 계산하지 않습니다.
`market_shipping_collected`는 고객에게 별도로 받는 배송비이며 공급처 배송비와 구분합니다.
일치하는 상품의 근거 URL과 확인 시점이 반드시 필요합니다.

```bash
python evaluate.py --supplier output/detail_candidates_파일명.csv --market market.csv
```

이 계산은 실거래 순이익이 아닌 **입력 조건의 잠정 공헌이익**입니다. 제품 원가의 부가세 처리, 옵션 추가금, 묶음배송, 정산·세금, 실제 전환율은 별도 검토해야 합니다.

### 보안
- Secrets의 `DOMEMAE_API_KEY`를 사용합니다. 노출된 이전 키는 재발급합니다.
- API 인증키 및 상품 원본 데이터는 저장소 코드에 커밋하지 않습니다.
- GitHub Actions 아티팩트는 공개 저장소에서 접근 범위가 넓을 수 있습니다. 결과물의 개인정보·거래기밀 노출을 주의하세요.
- API 호출 정책과 서비스 약관의 트래픽 제한을 확인하고, 필요하면 요청량을 낮추세요.


## 3단계: 기존 3,114건의 공급 위험 스크리닝 (실행 가능)

**Screen latest supplier data** 워크플로를 수동으로 실행합니다.
- `source_run`: 기존 성공 실행 ID `45018028549`
- `shortlist`: 우선 조사 큐 수량 `80`
- 새 도매매 호출이나 별도 키 입력은 필요하지 않습니다. 기존 Actions 아티팩트를 내려받아 오프라인에서 분석합니다.
- 결과는 `supplier_screening.csv` (공급정보 기준 위험 분류), `market_research_queue.csv` (외부 시장 증거를 추가할 조사 대상), `screening_summary.json`입니다.

**중요한 해석 제한**
- `MARKET_CHECK`는 ‘판매 승인’이 아니라 상품 상세 조건을 얻었으며 시장 조사가 필요한 상태를 뜻합니다.
- `REVIEW`는 공급 상세/권리/인증 검토가 필요한 상태, `HOLD`는 제한 상품 여부 확인이 필요한 상태입니다.
- 상품명만으로 인증 의무, 불량률, 가품 여부, 실제 반품률을 확정하지 않습니다.
- `market_research_queue.csv`의 빈 열은 사람이 확인한 동일상품 증거 URL, 시장 판매가격, 쇼핑 관심도, 판매자 수수료, 반품 충당액을 기록하기 위한 것입니다.
- **네이버 쇼핑인사이트의 검색 클릭지수는 판매 수량이 아닙니다.** 정확한 경쟁 판매자 주문량을 만들어 넣지 마세요.
- 현 단계에서 `contribution_profit`은 공란입니다. 실제 수익/판매 실적 데이터가 없기 때문입니다.
- 외부 시장 가격 자동 수집은 아직 구현되지 않았습니다. 최신 공식 API/권한 및 이용약관 확인 후 연결해야 합니다.
- 상품 실마진은 배송비, 옵션, 배송비 수취, 구매자 쿠폰, 환불 예상 손실, VAT 처리 등을 종합한 후 검증합니다.

현재 시장 신호 출처 검토:
- [NAVER API HUB 쇼핑인사이트](https://api.ncloud-docs.com/docs/naver-api-hub-shopping-insight-keywords)
- [NAVER 쇼핑 검색 API 종료 안내](https://developers.naver.com/notice/article/32530)
- [쿠팡 판매자 API](https://developers.coupang.com/ko)


## 4단계: 네이버·쿠팡 양쪽 시장 비교

- **Screen latest supplier data**를 먼저 실행해 `market_research_queue.csv`를 생성합니다.
- **Prepare Naver and Coupang comparison**에서 위 스크리닝 실행번호를 `screening_run`에 입력합니다.
- 결과 `market_observation_template.csv`에 네이버/쿠팡 동일 모델·옵션의 URL, 가격과 배송비, 정확한 수수료, 광고/반품충당 비용, 관측일, 수요 근거를 직접 검증해 채웁니다.
- 이 표는 **공식·허용 데이터 출처가 확인되기 전에는 자동으로 가격이나 판매량을 채우지 않습니다.**
- 로컬에서 `python compare_markets.py --queue market_research_queue.csv --observations market_observation_template.csv`를 실행해 비교 파일을 만듭니다.
- `match_status=exact_verified` + `match_evidence`(같은 모델/옵션 증거), `compliance_status=verified` + 모든 비용 + 가격근거 URL + 수요 출처·기간이 있어야 잠정 공헌이익을 계산합니다.
- 네이버·쿠팡의 수수료는 **임의의 고정 비율을 적용하지 않습니다.** 실제 판매자 계정/카테고리별 정보를 직접 입력합니다. payment_fee_pct는 marketplace_fee_pct와 중복 계상하지 않아야 합니다.
- `demand_type=click_trend`는 클릭 추세일 뿐 판매량이 아닙니다. 관측 기간/출처를 보존하고, 외부 판매자의 정확한 주문 수를 추정해 확정치로 기재하지 않습니다.
- 비교 결과 `PROVISIONAL_COMPARE`도 즉시 판매를 승인한 상태가 아닙니다. 부가세·정산·반품 책임·운전자금 확인이 필요합니다.

공식 참고: [네이버 API HUB](https://guide.ncloud-docs.com/docs/apihub-use), [네이버 스마트스토어 수수료](https://help.sell.smartstore.naver.com/faq/content.help?faqId=15759), [쿠팡 입점 FAQ](https://marketplace.coupang.com/faq).

**사용자 필요 정보:** 실제 판매 예정 플랫폼(네이버/쿠팡 모두 비교), 판매자 계정이 생기면 카테고리별 적용 수수료, API HUB 계정·허용 데이터 범위, 필요 시 실제 경쟁상품 근거. API 키를 공개 저장소/채팅에 붙이지 마세요.


## 5단계: 판매자·NAVER API HUB 계정 없이 진행하는 비교 조사

기존 **Broad product discovery** 성공 실행번호(`45018028549`)를 재사용하여 **Prepare no-account market research queue**를 수동 실행합니다.

- 기본값: `discovery_run=45018028549`, `candidates=25`
- 이전 결과의 상세 조회 완료 상품 중 기본 공급조건과 위험 키워드 검토를 통과한 후보를 분야별로 분산 선별합니다.
- 각 상품에 대해 네이버와 쿠팡 **검색 페이지를 여는 URL**을 생성합니다. URL은 검색 편의용이며, 일치 상품이나 경쟁가격의 존재를 보증하지 않습니다.
- 파일: `market_research_queue.csv`, `summary.json`
- 표의 경쟁 상품 URL·동일 모델/옵션 여부·가격·배송비·수수료·관측일·수요 근거는 모두 비어 있습니다. **외부 시장 데이터 수집 완료라는 의미가 아닙니다.**
- 가격, 반품률, 주문량 등을 임의 추정하지 않습니다. 인증 및 재판매/이미지 권리는 실제 판매 전 확인해야 합니다.
- 이 프로세스는 웹사이트를 자동 스크래핑하지 않으며 판매자 계정이나 NAVER API HUB 인증키가 필요하지 않습니다.

다음 단계로 네이버 쇼핑인사이트 API HUB를 연결할 때에는 서비스 신청 여부, 무료 사용 범위, 현재 요금 및 호출 제한을 반드시 공식 콘솔에서 확인한 뒤 적용합니다. 쇼핑 클릭지수는 판매건수와 다릅니다.

`compare_markets.py`의 비교 엔진은 실제로 확인한 데이터가 양쪽 시장에 입력될 때만 작동합니다. 빈 템플릿으로는 수익성 판정을 하지 않습니다.


## 6단계: 1차 후보의 카테고리 오류 점검
- **Audit market research queue**를 수동 실행하고 `research_run=45020115701` 사용.
- 25개 공급 후보 × 네이버/쿠팡 조사 행 50개의 **상품명 기반 카테고리 일치 여부만** 간단히 점검합니다.
- `keyword_supported_not_verified`는 상품명에 해당 카테고리의 단어가 존재한다는 뜻일 뿐 정확한 분류를 검증했다는 뜻이 아닙니다.
- `possible_category_mismatch` 및 `category_not_verifiable_from_title`는 사람의 재검토 대상입니다.
- 이 단계는 법적 판매 가능성, 동일 모델/옵션 매칭, 시장 가격, 판매량, 마진을 증명하지 않습니다.
- 이미 실행한 원본 데이터의 샘플 오분류 사례: '반려동물'에 '핸드폰 미니백' 포함.


## 7단계: NAVER API HUB 무료 한도 내 쇼핑인사이트 연동

현재 사용자가 확인한 요금표(2026-11-22)는 검색어 트렌드와 쇼핑인사이트 각각 월 0~30,000건 기본 무료, 30,001~50,000건 한시적 무료, 검색 API는 최대 775,000건 무료(하루 25,000건 한도)입니다. **한시적 무료는 영구 무료 약속이 아닙니다.** 실제 계정 청구·한도·변경 공지를 콘솔에서 다시 확인해야 합니다.

### 사용자 준비
1. NAVER Cloud Platform > Application Services > NAVER API HUB 에서 서비스 이용 신청 후 Application을 등록하고 **쇼핑 인사이트**를 선택합니다.
2. 해당 Application의 Client ID/Client Secret을 확인하고 GitHub 저장소의 Settings > Secrets and variables > Actions에 다음 이름으로 **각각 Repository Secret**을 저장합니다:
   - `NAVER_API_HUB_CLIENT_ID`
   - `NAVER_API_HUB_CLIENT_SECRET`
3. **NAVER Shopping Insight (free-only manual)** 워크플로를 실행합니다. 먼저 `execute=false`로 무료 드라이런을 실행해 카테고리 코드 및 요청 바디만 확인하세요.
4. 해당 월 쇼핑인사이트 실제 호출량과 적용 요금이 무료 한도 이내인지 콘솔에서 확인한 다음 `execute=true`, `free_plan_confirmed=true`로 **한 번만 호출**합니다.

이 프로그램은 자동 반복/크론을 걸지 않았고 1회 수동 실행당 쇼핑인사이트 요청 한 번만 전송합니다. 단, **GitHub Actions만으로 NAVER 계정 전체 누적 호출량이나 미래 과금 방지를 보장할 수 없으므로** NCP 콘솔의 사용량 및 알림 설정을 병행하세요.

카테고리 코드는 네이버쇼핑 카테고리 고유 ID입니다. 도매매 자체 분류명과 혼동하면 안 됩니다.
쇼핑인사이트는 검색 클릭 **상대지수**를 제공합니다. 실제 판매량, 제품별 매출 또는 경쟁가격으로 해석하지 마세요.
쇼핑/책/전문자료의 종전 NAVER 개발자센터 검색 API는 2026-07-31 종료되었으므로 경쟁상품 가격 자동 조회 기능이 아닙니다.

공식 문서: https://api.ncloud-docs.com/docs/naver-api-hub-shopping-insight-keywords


## 8단계: 증거 기반 동일상품 매칭 엔진 (v1)

`matching_engine.py`는 **공급처 이름이나 상품명 비슷함만으로 동일 상품 또는 수익이 검증됐다고 판정하지 않습니다.**

### 공급 데이터 추가
- 기본: 도매매 `catalog_*.csv`의 상세 데이터가 확인된 가격만 표준화합니다. 목록 가격은 실원가로 승격하지 않습니다.
- 타 공급처는 해당 업체의 **정식 API 또는 허용된 CSV 파일**을 사용해야 합니다. `--supplier-csv authorized_ownerclan.csv`처럼 입력할 수 있으며, 별도 계약이나 토큰 없이 타 플랫폼 데이터에 접근하지 않습니다.
- 표준 공급 필드: `source,source_id,title,brand,model,gtin,option,quantity,supply_price,shipping_fee,min_order,stock,active,rights_verified,compliance_verified,return_policy_verified,fulfillment_sla_verified,supplier_url,seller_id,observed_at`
- 오너클랜은 정식 GraphQL 상품/변경 이력 API를 제공하지만, 이 저장소에서 아직 실서비스 연동 및 권한 테스트를 하지 않았습니다.
- **정확한 공급비용**에는 옵션 가격, 최소구매수량, 주문 부대비용이 반영돼야 합니다.

### 시장 데이터 연결
- 정상적으로 이용 허가된 시장 API, 서면 허용된 데이터 피드 또는 수동으로 확인한 공개 판매페이지의 상품정보를 `market_observation_template.csv` 스키마로 기록합니다.
- `market_title`은 탐색용이고 정확성 증거가 아닙니다.
- `market_gtin` 일치 **또는** 제조사·모델 일치와 **동일한 옵션/수량**이 있을 때만 `EXACT_CANDIDATE`라고 판정합니다. 최종 동일상품 승인에는 사람 검토가 더 필요합니다.
- 옵션이 없거나, 모델/바코드가 달라지거나, 상품명만 비슷하면 `REVIEW` / `SIMILAR` / `CONFLICT`로 제한합니다.
- 시장경쟁가, 배송비, 수수료, 광고비, 반품비, 적법성 근거가 완전하지 않으면 `verified_contribution`은 **항상 공란**입니다.
- 데이터 소스의 이용범위·저장·보존 허용 여부를 먼저 확인하세요.
- 무단 쿠팡 크롤링·차단 우회 코드는 사용하지 않습니다.

### 실행
GitHub Actions → **Offline supplier-market matching gate** → Run workflow.
기존 도매매 수집 실행 ID `45018028549`가 기본값입니다. 최초 병합 시 오프라인 감사 1회가 자동 실행됩니다.
파일: `normalized_suppliers.csv`, `market_observation_template.csv`, `match_review.csv`, `matching_summary.json`.

로컬:
```bash
python matching_engine.py --domemae-catalog input/catalog_*.csv --supplier-csv authorized_ownerclan.csv --market-observations authorized_market.csv
```

**데이터 확보 원칙:** 상품수 기준 대량 등록 금지. 상품군의 지속적 관심, 동일 상품 경쟁가격, 공급자격, 배송, 반품, 법규, 주문당 공헌이익을 검증한 후 5~10개 후보로 소액 실험.
