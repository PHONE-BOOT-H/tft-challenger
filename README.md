# tft-challenger

브론즈~골드 KR 롤체 치트시트. 매일 자동 갱신, 패치 감지 시 변화 요약.

**사이트:** https://phone-boot-h.github.io/tft-challenger/

기존 메타 사이트가 안 주는 것 하나를 채운다 — **브실골 데이터로 본 덱 성적**과
**단계별 빌드업 경로**를 한 카드에 합치고, 고티어와의 차이(Δ)를 드러낸다.
덱의 68%는 티어가 오를수록 나빠지고 32%는 저티어 전용이다. 그 차이가 이 도구의 신호다.

## 실행

```bash
pip install -r requirements.txt
python -m src.fetch      # MetaTFT + ddragon 수집 → data/raw/
python -m src.build      # 검증 → 조인 → dist/index.html
pytest                   # 골든 테스트
```

GitHub Actions가 매일 위를 돌리고 `dist/`를 Pages로 배포한다.
패치가 감지되면 3일간 6시간 주기로 올린다.

## 구조

| 경로 | 역할 |
|---|---|
| `src/fetch.py` | 수집만. 가공 안 함 |
| `src/validate.py` | 셋·패치·cluster_id 게이트. 불일치면 렌더 거부 |
| `src/build.py` | 조인 + Δ 계산 + ko_KR 한글화 |
| `src/patchdiff.py` | 직전 커밋 데이터와 비교 → 패치 변화 |
| `src/notes.py` | 패치 감지 시 공식 노트 요약 |
| `src/render.py` | 단일 HTML 출력 |
| `data/daily/` | 축약 스냅샷. 커밋됨 = 메타 변천사 |
| `data/notes.yaml` | 보정 주석 (출처 링크 필수) |

## 데이터 출처

MetaTFT(집계) · Riot Data Dragon(ko_KR 이름표). 둘 다 공개·비인증.
Riot API는 쓰지 않는다 — 매치 데이터에 단계별 보드가 없고, 개인 키 승인이 3~8개월 걸린다.

설계 배경과 결정 근거: [docs/superpowers/specs/](docs/superpowers/specs/)

---
Riot Games가 승인하거나 후원한 프로젝트가 아니다.
