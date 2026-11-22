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
