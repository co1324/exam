# 다단 편집 수험서 자동 검수 프로그램 사용 설명서

이 문서는 "다단 편집 수험서 자동 검수 프로그램"을 처음 접하는 사용자도 쉽게 따라 할 수 있도록 **준비 단계부터 실행, 결과 확인까지** 전 과정을 한글로 상세히 안내합니다. 아래 순서를 꼭 차례대로 따라 하세요.

---

## 1. 프로그램 개요

이 프로그램은 두 부분으로 나뉘어 동작합니다.

1. **법령 지식 베이스 구축(준비 단계)**: 최신 법령 PDF를 잘게 나눠 벡터 DB로 저장합니다.
2. **수험서 페이지별 검수(실행 단계)**: 수험서 PDF를 페이지 단위로 이미지화하고, 단 구분 및 OCR을 거쳐 텍스트를 추출한 뒤, 법령 지식과 비교하여 검수 리포트를 생성합니다.

> ⚠️ 법령 PDF와 수험서 PDF가 모두 준비되어 있어야 전체 과정을 수행할 수 있습니다.

---

## 2. 사전 준비물

### 2-1. 운영체제 요구 사항
- Windows, macOS, Linux 어디서든 실행 가능합니다.
- **Poppler**(PDF → 이미지 변환 도구)와 **Tesseract OCR 엔진**은 시스템에 직접 설치해야 합니다.

### 2-2. 파이썬 환경 준비
1. [Python 3.10 이상](https://www.python.org/downloads/)이 설치되어 있는지 확인합니다.
2. (권장) 가상 환경을 생성합니다.
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows의 경우 .venv\Scripts\activate
   ```

### 2-3. 필수 파이썬 패키지 설치
아래 명령을 순서대로 실행해 필요한 라이브러리를 설치합니다.
```bash
pip install --upgrade pip
pip install pillow pdf2image pdfminer.six PyPDF2 pytesseract numpy opencv-python
```

> 💡 `pdf2image`를 사용할 때는 **Poppler**가 시스템 경로에 설치되어 있어야 하며, `pytesseract`는 **Tesseract OCR 엔진**이 사전에 설치되어 있어야 합니다.

---

## 3. 입력 파일 준비
1. **법령 PDF(`latest_safety_laws.pdf` 등)**: 검수 기준이 되는 최신 법령 문서입니다.
2. **수험서 PDF(`sample_exam_book.pdf` 등)**: 실제로 검수를 수행할 수험서입니다.
3. 위 두 파일의 경로를 정확히 기록해 두세요. 프로그램 실행 시 필요합니다.

---

## 4. 프로그램 실행 전 체크리스트
아래 항목을 차례대로 확인합니다.

1. ✅ Python 가상 환경이 활성화되어 있는가?
2. ✅ 필수 라이브러리가 모두 설치되었는가?
3. ✅ Poppler와 Tesseract OCR 엔진이 설치되어 있는가?
4. ✅ 법령 PDF와 수험서 PDF 파일 경로를 알고 있는가?
5. ✅ 결과 보고서를 저장할 폴더를 미리 결정했는가? (예: `output/`)

모두 준비되었다면 다음 단계로 이동합니다.

---

## 5. 실행 방법 (Step by Step)

1. **출력 디렉터리 생성(선택 사항)**
   ```bash
   mkdir -p output
   ```
   이미 폴더가 있다면 생략 가능합니다.

2. **프로그램 실행**
   ```bash
   python main.py <법령_PDF_경로> <수험서_PDF_경로> --output output
   ```

   예시:
   ```bash
   python main.py data/latest_safety_laws.pdf data/sample_exam_book.pdf --output output
   ```

3. **선택적 인자 설명**
   | 옵션 | 기본값 | 설명 |
   | --- | --- | --- |
   | `--dpi` | `300` | PDF를 이미지로 렌더링할 해상도 |
   | `--top-k` | `5` | 페이지 검수 시 참조할 법령 청크 개수 |
   | `--chunk-size` | `1200` | 법령 텍스트를 분할할 때 사용할 청크 크기(문자 단위) |
   | `--chunk-overlap` | `200` | 인접 청크 사이의 중복 문자 수 |
   | `--language` | `kor+eng` | OCR 엔진 언어 설정 (`kor`, `eng`, `kor+eng` 등) |
   | `--stopwords` | 없음 | 추가로 제거할 불용어 목록(띄어쓰기로 구분) |

4. **지식 베이스 캐시 활용**
   - `--output` 하위의 `cache/knowledge_base.json` 파일이 자동으로 생성됩니다.
   - 같은 법령 PDF로 다시 실행하면 캐시를 그대로 재사용하므로 속도가 빨라집니다.

---

## 6. 실행 중 동작 흐름 이해하기

1. **법령 텍스트 추출** → **청크 분할** → **TF-IDF 벡터화** → **지식 베이스 저장**
2. **수험서 페이지 렌더링** → **단(Column) 감지** → **단별 OCR** → **텍스트 재조합**
3. **페이지 텍스트를 지식 베이스와 비교** → **관련 법규 검색** → **검수 리포트 생성**
4. 결과 파일 출력: `output/inspection_report.md`, `output/inspection_report.json`

각 단계에서 오류가 발생하면 로그 메시지로 안내되니 터미널 출력을 주의 깊게 확인하세요.

---

## 7. 결과 확인 방법

1. `output/inspection_report.md` 파일을 열면 페이지별 검수 내용을 Markdown 형식으로 확인할 수 있습니다.
2. `output/inspection_report.json` 파일은 동일한 정보를 JSON 배열로 제공하므로, 다른 시스템과 연동할 때 사용하기 좋습니다.
3. `--keep-debug-images` 옵션을 `SystemConfig`에서 `True`로 설정하면, 각 페이지 이미지를 `output/page_XXXX.png` 형태로 보관하여 OCR 품질을 직접 확인할 수 있습니다.

---

## 8. 문제 해결 가이드

| 증상 | 원인 | 해결 방법 |
| --- | --- | --- |
| `Pillow is required` 오류 | Pillow 미설치 | `pip install pillow` 실행 |
| `pdf2image is required` 오류 | pdf2image 또는 Poppler 미설치 | `pip install pdf2image` 후 Poppler 설치 및 PATH 추가 |
| `pytesseract is required` 오류 | pytesseract 또는 Tesseract 미설치 | `pip install pytesseract` 후 Tesseract OCR 설치 |
| OCR 결과가 비어 있음 | 이미지 품질 낮음 | `--dpi` 값을 높이거나 Poppler 설치 상태 확인 |
| 보고서 내용이 빈약함 | 법령 PDF 내용 부족 또는 불용어 설정 과도 | 더 풍부한 법령 문서 사용 또는 `--stopwords` 목록 조정 |

---

## 9. 다음 단계
- 보고서를 팀과 공유하거나, Markdown 파일을 문서화 도구(예: Notion, Confluence)에 바로 업로드할 수 있습니다.
- JSON 결과는 추가 자동화(예: 규정 위반 자동 알림) 등에 활용할 수 있습니다.

---

## 10. 요약
1. Python 및 필수 라이브러리를 설치한다.
2. 법령 PDF와 수험서 PDF를 준비한다.
3. `python main.py <법령> <수험서> --output <폴더>` 명령으로 실행한다.
4. `output/inspection_report.*` 파일에서 결과를 확인한다.

문제가 해결되지 않거나 기능 확장이 필요하면 소스 코드를 참고해 `SystemConfig`와 각 모듈(`exam_checker/`)을 커스터마이징하세요.
