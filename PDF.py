import json
import os
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

# === 폰트 등록 ===
KOREAN_FONT = "HYSMyeongJo-Medium"
pdfmetrics.registerFont(UnicodeCIDFont(KOREAN_FONT))

if not os.path.exists("conlang_PUA.ttf"):
    raise FileNotFoundError("❌ conlang_PUA.ttf이 없습니다. 폰트 파일을 확인하세요.")
pdfmetrics.registerFont(TTFont("HuiuclFont", "conlang_PUA.ttf"))

def is_pua(ch):
    return 0xE000 <= ord(ch) <= 0xF8FF

def generate_pdf_from_json(json_file, output_pdf):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    c = canvas.Canvas(output_pdf, pagesize=A4)
    width, height = A4

    # === 기존의 효율적인 레이아웃 설정 유지 ===
    MARGIN = 30
    COL_GAP = 20
    COL_WIDTH = (width - (MARGIN * 2) - COL_GAP) / 2
    FONT_SIZE_BODY = 8
    FONT_SIZE_TITLE = 10
    LINE_SPACING = 1.2

    curr_x = MARGIN
    curr_y = height - MARGIN
    column_index = 0

    def check_page_break(y, required=15):
        nonlocal curr_y, curr_x, column_index
        if y < MARGIN + required:
            if column_index == 0:
                column_index = 1
                curr_x = MARGIN + COL_WIDTH + COL_GAP
                curr_y = height - MARGIN
            else:
                c.showPage()
                column_index = 0
                curr_x = MARGIN
                curr_y = height - MARGIN
            return curr_y
        return y

    # 개선된 텍스트 드로잉: 긴 문장을 COL_WIDTH에 맞춰 자동으로 줄바꿈
    def draw_wrapped_text(text, x, y, size):
        nonlocal curr_y
        y = check_page_break(y)
        cx = x
        
        # 단어 단위가 아닌 글자 단위로 처리하여 PUA 폰트 혼용 및 정확한 줄바꿈 보장
        i = 0
        while i < len(text):
            ch = text[i]
            # 글자마다 폰트 체크 (PUA면 전용폰트, 아니면 한국어폰트)
            font_name = "HuiuclFont" if is_pua(ch) else KOREAN_FONT
            c.setFont(font_name, size)
            
            w = pdfmetrics.stringWidth(ch, font_name, size)
            
            # 현재 열의 너비를 벗어나면 줄바꿈
            if cx + w > x + COL_WIDTH:
                y -= size * LINE_SPACING
                y = check_page_break(y)
                cx = x + 10 # 줄바꿈 시 들여쓰기 효과
            
            c.drawString(cx, y, ch)
            cx += w
            i += 1
            
        curr_y = y - (size * LINE_SPACING)
        return curr_y

    # 상단 타이틀
    c.setFont(KOREAN_FONT, 14)
    c.drawCentredString(width / 2, height - 20, "Huiucl Dictionary")
    curr_y -= 10

    def process_section(content, indent=0):
        nonlocal curr_y
        if not isinstance(content, dict): return

        for key, value in content.items():
            curr_y = check_page_break(curr_y, 25)
            prefix = "• " if indent > 0 else "■ "
            line_start = "  " * indent + prefix + key

            if isinstance(value, dict):
                # 데이터가 복잡한 경우(뜻, 예시, 파생형 등) 하나로 합쳐서 출력
                has_meaning = "뜻" in value or any(isinstance(v, str) for v in value.values())
                if has_meaning:
                    parts = []
                    for sub_key, sub_val in value.items():
                        if isinstance(sub_val, dict): # 파생형 뭉치 처리
                            for inner_k, inner_v in sub_val.items():
                                parts.append(f"{inner_k}: {inner_v}")
                        else:
                            parts.append(f"{sub_key}: {sub_val}")
                    full_line = line_start + ": " + ", ".join(parts)
                    curr_y = draw_wrapped_text(full_line, curr_x, curr_y, 
                                              FONT_SIZE_BODY if indent > 0 else FONT_SIZE_TITLE)
                else:
                    # 하위 카테고리 제목만 출력 후 재귀 호출
                    curr_y = draw_wrapped_text(line_start, curr_x, curr_y,
                                              FONT_SIZE_BODY if indent > 0 else FONT_SIZE_TITLE)
                    process_section(value, indent + 1)
            else:
                # 단순 문자열 데이터
                full_line = line_start + ": " + str(value)
                curr_y = draw_wrapped_text(full_line, curr_x, curr_y,
                                          FONT_SIZE_BODY if indent > 0 else FONT_SIZE_TITLE)
            curr_y -= 3 # 항목 간 미세 간격

    # 전체 데이터 순회 시작
    for section, content in data.items():
        curr_y = check_page_break(curr_y, 30)
        c.setLineWidth(0.5)
        c.line(curr_x, curr_y + 2, curr_x + COL_WIDTH, curr_y + 2) # 섹션 구분선
        curr_y = draw_wrapped_text(f"■ {section}", curr_x, curr_y, FONT_SIZE_TITLE)
        process_section(content, indent=1)
        curr_y -= 10

    c.save()
    print(f"✅ 개선 완료: {output_pdf}")

if __name__ == "__main__":
    # 유저님의 JSON 파일명에 맞춰 실행
    json_file = "conlang_pua.json"
    generate_pdf_from_json(json_file, "Huiucl_Improved.pdf")