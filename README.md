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
