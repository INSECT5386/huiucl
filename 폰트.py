import sys
import math
import traceback
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QCheckBox
)
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QPointF
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

# ==========================================
# 설정 상수
# ==========================================
PUA_START = 0xE000
GRID_SIZE = 50
CANVAS_SIZE = 600
UNITS_PER_EM = 1024  # 폰트의 기본 단위 (Em Square)

PHONEME_LIST = ["m", "n", "s", "c", "h", "l", "t", "a", "i", "u"]

class CurveStroke:
    def __init__(self, p1, p2, cp=None):
        self.p1 = p1
        self.p2 = p2
        self.cp = cp if cp else QPointF((p1.x()+p2.x())/2, (p1.y()+p2.y())/2)

class DotStroke:
    def __init__(self, p, r=12):
        self.p = p
        self.r = r

class Canvas(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(CANVAS_SIZE, CANVAS_SIZE)
        self.curves = []
        self.dots = []
        self.selected = None
        self.target = None
        self.show_grid = True
        self.dot_mode = False
        self.setStyleSheet("background:white;border:2px solid #444;")

    def snap(self, p):
        return QPointF(
            round(p.x()/GRID_SIZE)*GRID_SIZE,
            round(p.y()/GRID_SIZE)*GRID_SIZE
        )

    def bezier(self, c, t):
        x = (1-t)**2*c.p1.x() + 2*(1-t)*t*c.cp.x() + t**2*c.p2.x()
        y = (1-t)**2*c.p1.y() + 2*(1-t)*t*c.cp.y() + t**2*c.p2.y()
        return QPointF(x, y)

    def mousePressEvent(self, e):
        pos = self.snap(e.position())
        if self.dot_mode:
            self.dots.append(DotStroke(pos))
            self.update()
            return
        for c in self.curves:
            for name, p in (("p1",c.p1),("p2",c.p2),("cp",c.cp)):
                if math.hypot(p.x()-pos.x(), p.y()-pos.y()) < 15:
                    self.selected, self.target = c, name
                    return
        c = CurveStroke(pos, pos)
        self.curves.append(c)
        self.selected, self.target = c, "p2"

    def mouseMoveEvent(self, e):
        if not self.selected: return
        pos = self.snap(e.position())
        if self.target == "p1": self.selected.p1 = pos
        elif self.target == "p2": self.selected.p2 = pos
        elif self.target == "cp": self.selected.cp = pos
        self.update()

    def mouseReleaseEvent(self, e):
        self.target = None

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.show_grid:
            p.setPen(QPen(QColor(220,220,220), 1))
            for i in range(0, CANVAS_SIZE+1, GRID_SIZE):
                p.drawLine(i, 0, i, CANVAS_SIZE)
                p.drawLine(0, i, CANVAS_SIZE, i)
        for c in self.curves:
            p.setPen(QPen(Qt.GlobalColor.black, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for i in range(40):
                p.drawLine(self.bezier(c, i/40), self.bezier(c, (i+1)/40))
            p.setPen(QPen(QColor(200,0,0), 1))
            p.drawEllipse(c.p1, 4, 4)
            p.drawEllipse(c.p2, 4, 4)
            p.setBrush(QColor(0,0,255, 100))
            p.drawEllipse(c.cp, 4, 4)
        p.setBrush(Qt.GlobalColor.black)
        for d in self.dots: p.drawEllipse(d.p, d.r, d.r)

    def clear(self):
        self.curves.clear(); self.dots.clear(); self.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.glyphs, self.idx = {}, 0
        self.setWindowTitle("PUA Font Creator: Proper Scaling Edition")
        w = QWidget()
        v = QVBoxLayout(w)
        self.info = QLabel(f"현재 문자: {PHONEME_LIST[0]}")
        v.addWidget(self.info)
        self.canvas = Canvas()
        v.addWidget(self.canvas)
        h = QHBoxLayout()
        btn_undo = QPushButton("되돌리기")
        btn_save = QPushButton("글자 확정")
        btn_undo.clicked.connect(lambda: (self.canvas.curves.pop() if self.canvas.curves else None, self.canvas.update()))
        btn_save.clicked.connect(self.save_glyph)
        h.addWidget(btn_undo); h.addWidget(btn_save)
        v.addLayout(h)
        btn_export = QPushButton("TTF 생성 (정밀 스케일링)")
        btn_export.clicked.connect(self.export)
        v.addWidget(btn_export)
        self.setCentralWidget(w)

    def save_glyph(self):
        self.glyphs[PUA_START+self.idx] = {
            "curves": [(c.p1.x(), c.p1.y(), c.cp.x(), c.cp.y(), c.p2.x(), c.p2.y()) for c in self.canvas.curves],
            "dots": [(d.p.x(), d.p.y(), d.r) for d in self.canvas.dots]
        }
        self.idx += 1
        if self.idx < len(PHONEME_LIST):
            self.info.setText(f"다음 문자: {PHONEME_LIST[self.idx]}")
            self.canvas.clear()
        else: self.info.setText("모든 문자 완료! TTF를 생성하세요.")

    def export(self):
        try:
            create_ttf("conlang_PUA.ttf", self.glyphs)
            self.info.setText("생성 성공: conlang_PUA.ttf")
        except: traceback.print_exc()

def create_ttf(path, data):
    fb = FontBuilder(UNITS_PER_EM, isTTF=True)
    glyph_order = [".notdef"] + [f"uni{c:04X}" for c in data]
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap({c: f"uni{c:04X}" for c in data})
    
    glyf = {".notdef": TTGlyphPen(None).glyph()}
    hmtx = {".notdef": (512, 0)}

    FONT_STROKE_THICK = 70 
    SIDE_BEARING = 60  # 글자 좌우에 들어갈 최소 여백

    for code, strokes in data.items():
        pen = TTGlyphPen(None)
        curves, dots = strokes["curves"], strokes["dots"]
        
        all_pts = []
        for (x1, y1, cx, cy, x2, y2) in curves: all_pts.extend([(x1, y1), (cx, cy), (x2, y2)])
        for (dx, dy, dr) in dots: all_pts.append((dx, dy))
        
        if not all_pts:
            glyf[f"uni{code:04X}"] = pen.glyph()
            hmtx[f"uni{code:04X}"] = (500, 0)
            continue

        min_x = min(p[0] for p in all_pts)
        max_x = max(p[0] for p in all_pts)
        min_y = min(p[1] for p in all_pts)
        max_y = max(p[1] for p in all_pts)
        
        draw_w = max(max_x - min_x, 1)
        draw_h = max(max_y - min_y, 1)

        # 스케일링 (높이 80% 기준)
        target_h = UNITS_PER_EM * 0.8
        scale = target_h / max(draw_w, draw_h, 100)
        
        # 실제 글자 너비 계산: (그려진 폭 * 스케일) + 좌우 여백
        glyph_width = int(draw_w * scale + (SIDE_BEARING * 2))

        def tr(x, y):
            # x좌표를 SIDE_BEARING만큼 띄워서 시작하게 함
            tx = (x - min_x) * scale + SIDE_BEARING
            # y좌표를 중앙 정렬 및 폰트 좌표계(위가 +)로 변환
            ty = (max_y - y) * scale + (UNITS_PER_EM - target_h) / 2
            return tx, ty

        # 곡선 그리기 로직 (동일)
        half_w = FONT_STROKE_THICK / 2
        for (x1, y1, cx, cy, x2, y2) in curves:
            points = [tr(px, py) for px, py in [
                ((1-t)**2*x1 + 2*(1-t)*t*cx + t**2*x2, 
                 (1-t)**2*y1 + 2*(1-t)*t*cy + t**2*y2) 
                for t in [i/50 for i in range(51)]
            ]]
            
            left_s, right_s = [], []
            for i in range(len(points)):
                if i < len(points)-1: dx, dy = points[i+1][0]-points[i][0], points[i+1][1]-points[i][1]
                else: dx, dy = points[i][0]-points[i-1][0], points[i][1]-points[i-1][1]
                L = math.hypot(dx, dy)
                if L == 0: continue
                nx, ny = -dy/L, dx/L
                left_s.append((points[i][0]+nx*half_w, points[i][1]+ny*half_w))
                right_s.append((points[i][0]-nx*half_w, points[i][1]-ny*half_w))
            
            if left_s:
                pen.moveTo(left_s[0])
                for p in left_s[1:]: pen.lineTo(p)
                last_p, prev_p = points[-1], points[-2]
                ang = math.atan2(last_p[1]-prev_p[1], last_p[0]-prev_p[0])
                for j in range(9):
                    a = ang - math.pi/2 + math.pi*j/8
                    pen.lineTo((last_p[0]+math.cos(a)*half_w, last_p[1]+math.sin(a)*half_w))
                for p in reversed(right_s): pen.lineTo(p)
                first_p, next_p = points[0], points[1]
                ang = math.atan2(next_p[1]-first_p[1], next_p[0]-first_p[0])
                for j in range(9):
                    a = ang + math.pi/2 + math.pi*j/8
                    pen.lineTo((first_p[0]+math.cos(a)*half_w, first_p[1]+math.sin(a)*half_w))
                pen.closePath()

        # 점 그리기 로직 (동일)
        for (dx, dy, dr) in dots:
            fx, fy = tr(dx, dy)
            fsr = dr * scale
            pen.moveTo((fx + fsr, fy))
            for i in range(1, 17):
                a = 2 * math.pi * i / 16
                pen.lineTo((fx + math.cos(a)*fsr, fy + math.sin(a)*fsr))
            pen.closePath()

        glyf[f"uni{code:04X}"] = pen.glyph()
        # 계산된 가변 너비를 적용 (Advance Width)
        hmtx[f"uni{code:04X}"] = (glyph_width, 0)

    fb.setupGlyf(glyf)
    fb.setupHorizontalMetrics(hmtx)
    fb.setupHorizontalHeader(ascent=900, descent=-100)
    fb.setupOS2(sTypoAscender=900, sTypoDescender=-100)
    fb.setupNameTable({"familyName": "ScalingFont", "styleName": "Regular"})
    fb.setupPost(); fb.setupMaxp(); fb.setupHead(); fb.save(path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow(); w.show()
    sys.exit(app.exec())