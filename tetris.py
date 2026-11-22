import ctypes
from datetime import datetime
import json
import os
import random
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Trò chơi sử dụng msvcrt để đọc bàn phím không cần nhấn Enter trên Windows.
try:
    import msvcrt
except ImportError:
    print("Mã nguồn này yêu cầu Windows để chạy thư viện msvcrt.")
    sys.exit()

H = 20
W = 15
board = [[" " for _ in range(W)] for _ in range(H)]
last_frame_lines = []  # Bộ đệm lưu khung hình trước để vẽ vi phân chống nhấp nháy.

# File lưu lịch sử Top 10 điểm cao nhất cùng thư mục với file mã nguồn.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HIGHSCORE_FILE = os.path.join(BASE_DIR, "highscores.json")
MAX_HIGHSCORES = 10

# JD05: (Tên độ khó, tốc độ rơi giây/ô, hệ số nhân điểm)
DIFFICULTIES = [
    ("EASY", 0.8, 1),
    ("NORMAL", 0.5, 2),
    ("HARD", 0.2, 3),
]
MIN_FALL_DELAY = 0.08  # JD03: Không để tốc độ rơi tăng vô hạn.

# Thông số tối ưu cảm giác điều khiển (DAS / ARR & Lock Delay)
DAS_DELAY = 0.13            # Độ trễ trước khi bắt đầu trượt tự động khi giữ phím (giây)
ARR_INTERVAL = 0.03         # Tốc độ trượt ngang liên tục (~33 ô/giây)
SOFT_DROP_INTERVAL = 0.035  # Tốc độ rơi nhanh khi giữ phím xuống (~28 ô/giây)
LOCK_DELAY = 0.50           # Thời gian cho phép lách/xoay sau khi chạm đáy (giây)
MAX_LOCK_MOVES = 15         # Giới hạn số lần reset độ trễ khóa để tránh treo khối

# Bảng điểm cơ bản khi xóa 1, 2, 3 hoặc 4 hàng cùng lúc.
LINE_SCORES = {
    1: 100,
    2: 300,
    3: 500,
    4: 800,
}

# Virtual-Key Codes trên Windows để kiểm tra trạng thái giữ phím thời gian thực.
VK_LEFT_KEYS = (0x25, 0x41)          # Mũi tên trái, A
VK_RIGHT_KEYS = (0x27, 0x44)         # Mũi tên phải, D
VK_DOWN_KEYS = (0x28, 0x53, 0x58)    # Mũi tên xuống, S, X

try:
    _USER32 = ctypes.windll.user32
except Exception:
    _USER32 = None


def is_any_key_down(vk_codes):
    """Kiểm tra trực tiếp trạng thái phím vật lý đang được nhấn giữ."""
    if _USER32 is None:
        return False
    try:
        return any(_USER32.GetAsyncKeyState(vk) & 0x8000 for vk in vk_codes)
    except Exception:
        return False


def write_terminal(text):
    """Ghi trực tiếp buffer UTF-8 để giảm độ trễ I/O trên Console."""
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.flush()
    else:
        sys.stdout.write(text)
        sys.stdout.flush()


# ==========================================
# QUẢN LÝ LỊCH SỬ TOP 10 HIGH SCORES
# ==========================================
def load_highscores():
    """Đọc danh sách Top 10 điểm cao nhất từ file JSON."""
    if not os.path.exists(HIGHSCORE_FILE):
        return []
    try:
        with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        valid_entries = []
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("score"), int):
                valid_entries.append({
                    "score": item["score"],
                    "lines": int(item.get("lines", 0)),
                    "difficulty": str(item.get("difficulty", "NORMAL")),
                    "date": str(item.get("date", "--/--/---- --:--")),
                })
        valid_entries.sort(key=lambda x: (x["score"], x["lines"]), reverse=True)
        return valid_entries[:MAX_HIGHSCORES]
    except Exception:
        return []


def save_highscores(entries):
    """Lưu danh sách Top 10 điểm cao nhất xuống file JSON."""
    try:
        with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
            json.dump(entries[:MAX_HIGHSCORES], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_highest_score():
    """Trả về mức điểm cao nhất từng đạt được."""
    scores = load_highscores()
    return scores[0]["score"] if scores else 0


def record_score(score, lines, difficulty):
    """Lưu điểm mới nếu > 0 và trả về thứ hạng (1..10) nếu lọt vào Top 10."""
    if score <= 0:
        return None

    scores = load_highscores()
    new_entry = {
        "score": score,
        "lines": lines,
        "difficulty": difficulty,
        "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    scores.append(new_entry)
    scores.sort(key=lambda x: (x["score"], x["lines"]), reverse=True)
    top_scores = scores[:MAX_HIGHSCORES]
    save_highscores(top_scores)

    for idx, entry in enumerate(top_scores, start=1):
        if entry is new_entry:
            return idx
    return None


# ==========================================
# JD01: LỚP CHA VÀ CÁC LỚP KHỐI KẾ THỪA
# ==========================================
class Block:

    def __init__(self, x=5, y=1):
        self.x = x
        self.y = y
        self.shape = []

    def can_move(self, dx, dy, target_shape=None):
        matrix = target_shape if target_shape is not None else self.shape
        size = len(matrix)
        for i in range(size):
            for j in range(size):
                if matrix[i][j] != " ":
                    xt = self.x + j + dx
                    yt = self.y + i + dy
                    if xt < 1 or xt >= W - 1 or yt >= H - 1:
                        return False
                    if board[yt][xt] != " ":
                        return False
        return True

    def to_board(self):
        size = len(self.shape)
        for i in range(size):
            for j in range(size):
                if self.shape[i][j] != " ":
                    board[self.y + i][self.x + j] = self.shape[i][j]

    def del_from_board(self):
        size = len(self.shape)
        for i in range(size):
            for j in range(size):
                if self.shape[i][j] != " ":
                    board[self.y + i][self.x + j] = " "

    def rotate(self, clockwise=True):
        """Xoay khối 90 độ (kèm Wall Kick 1 ô để xoay mượt khi sát tường)."""
        size = len(self.shape)
        rotated = [[" " for _ in range(size)] for _ in range(size)]
        for i in range(size):
            for j in range(size):
                if clockwise:
                    rotated[j][size - 1 - i] = self.shape[i][j]
                else:
                    rotated[size - 1 - j][i] = self.shape[i][j]

        for dx in (0, -1, 1):
            if self.can_move(dx, 0, rotated):
                self.x += dx
                self.shape = rotated
                return True
        return False


class BlockO(Block):

    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.shape = [
            [" ", " ", " ", " "],
            [" ", "O", "O", " "],
            [" ", "O", "O", " "],
            [" ", " ", " ", " "],
        ]

    def rotate(self, clockwise=True):
        return False


class BlockI(Block):

    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.is_vertical = True
        self.shape = [
            [" ", "I", " ", " "],
            [" ", "I", " ", " "],
            [" ", "I", " ", " "],
            [" ", "I", " ", " "],
        ]

    def rotate(self, clockwise=True):
        if self.is_vertical:
            rotated = [
                [" ", " ", " ", " "],
                ["I", "I", "I", "I"],
                [" ", " ", " ", " "],
                [" ", " ", " ", " "],
            ]
        else:
            rotated = [
                [" ", "I", " ", " "],
                [" ", "I", " ", " "],
                [" ", "I", " ", " "],
                [" ", "I", " ", " "],
            ]

        # Thử xoay tại chỗ; nếu sát tường thì thử nhích trái/phải 1-2 ô (Wall Kick)
        for dx in (0, -1, 1, -2, 2):
            if self.can_move(dx, 0, rotated):
                self.x += dx
                self.shape = rotated
                self.is_vertical = not self.is_vertical
                return True
        return False


class BlockT(Block):

    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.shape = [[" ", "T", " "], ["T", "T", "T"], [" ", " ", " "]]


class BlockS(Block):

    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.shape = [[" ", "S", "S"], ["S", "S", " "], [" ", " ", " "]]


class BlockZ(Block):

    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.shape = [["Z", "Z", " "], [" ", "Z", "Z"], [" ", " ", " "]]


class BlockJ(Block):

    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.shape = [["J", " ", " "], ["J", "J", "J"], [" ", " ", " "]]


class BlockL(Block):

    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.shape = [[" ", " ", "L"], ["L", "L", "L"], [" ", " ", " "]]


class BlockBag:
    """Bộ sinh khối theo cơ chế túi 7 mảnh giúp nhịp độ ra gạch đồng đều."""

    def __init__(self):
        self._bag = []

    def next_block(self):
        if not self._bag:
            self._bag = [BlockI, BlockO, BlockT, BlockS, BlockZ, BlockJ, BlockL]
            random.shuffle(self._bag)
        return self._bag.pop()(x=5, y=1)


# ==========================================
# JD01: KHỞI TẠO BÀN CHƠI
# ==========================================
def init_board():
    for i in range(H):
        for j in range(W):
            if i == 0 or i == H - 1 or j == 0 or j == W - 1:
                board[i][j] = "#"
            else:
                board[i][j] = " "


# ==========================================
# JD04: VIỀN VÀ CÁC Ô VUÔNG VỨC
# ==========================================
CELL_BLOCK = "██"
CELL_EMPTY = "  "


def render_row(i):
    if i == 0:
        return "╔" + "══" * (W - 2) + "╗"
    if i == H - 1:
        return "╚" + "══" * (W - 2) + "╝"
    cells = "".join(
        CELL_EMPTY if board[i][j] == " " else CELL_BLOCK
        for j in range(1, W - 1)
    )
    return "║" + cells + "║"


def render_side_row(i, next_block, score, best_score):
    """Vẽ khung khối tiếp theo, điểm hiện tại và điểm cao nhất ở bên phải."""
    if i == 0:
        return "  NEXT:"
    if i == 1:
        return "  ╔════════╗"
    if 2 <= i <= 5:
        if next_block is None:
            return "  ║        ║"
        shape = next_block.shape
        size = len(shape)
        r = i - 2
        r_offset = 1 if size == 3 else 0
        cells = []
        for c in range(4):
            sr = r - r_offset
            if 0 <= sr < size and 0 <= c < size and shape[sr][c] != " ":
                cells.append(CELL_BLOCK)
            else:
                cells.append(CELL_EMPTY)
        return "  ║" + "".join(cells) + "║"
    if i == 6:
        return "  ╚════════╝"
    if i == 8:
        return "  SCORE:"
    if i == 9:
        return "  ╔════════╗"
    if i == 10:
        return f"  ║{str(score).center(8)}║"
    if i == 11:
        return "  ╚════════╝"
    if i == 13:
        return "  BEST:"
    if i == 14:
        return "  ╔════════╗"
    if i == 15:
        return f"  ║{str(best_score).center(8)}║"
    if i == 16:
        return "  ╚════════╝"
    return ""


def draw(total_lines=0, fall_delay=1.5, difficulty="NORMAL", next_block=None, score=0, best_score=0):
    """Vẽ vi phân kết hợp đồng bộ khung hình để loại bỏ hoàn toàn hiện tượng nhấp nháy."""
    display_best = max(best_score, score)
    rows = [render_row(i) + render_side_row(i, next_block, score, display_best) for i in range(H)]
    rows.append(
        f"Độ khó: {difficulty} | Hàng đã xóa: {total_lines} | Tốc độ: {fall_delay:.2f}s/ô"
    )

    chunks = []
    for idx, line in enumerate(rows):
        if idx >= len(last_frame_lines) or last_frame_lines[idx] != line:
            chunks.append(f"\033[{idx + 1};1H{line}\033[K")

    if len(last_frame_lines) > len(rows):
        chunks.append(f"\033[{len(rows) + 1};1H\033[J")

    last_frame_lines[:] = rows

    if chunks:
        # \033[?2026h ... \033[?2026l khóa bộ đệm hiển thị cho tới khi vẽ xong toàn bộ khung.
        payload = (
            "\033[?2026h"
            + "".join(chunks)
            + f"\033[{len(rows) + 1};1H"
            + "\033[?2026l"
        )
        write_terminal(payload)


# ==========================================
# JD02: XÓA HÀNG ĐẦY, DỒN CÁC HÀNG BÊN TRÊN
# ==========================================
def remove_line():
    """Xóa hàng đầy, dồn các hàng bên trên và trả về số hàng đã xóa."""
    lines_cleared = 0
    current_row = H - 2
    while current_row >= 1:
        playable_cells = board[current_row][1:W - 1]
        if " " not in playable_cells:
            lines_cleared += 1
            for target_row in range(current_row, 1, -1):
                above_row = target_row - 1
                board[target_row][1:W - 1] = board[above_row][1:W - 1]
            board[1][1:W - 1] = [" "] * (W - 2)
        else:
            current_row -= 1
    return lines_cleared


# ==========================================
# JD05: ĐỌC WASD VÀ PHÍM MŨI TÊN WINDOWS
# ==========================================
def read_key():
    """Chuẩn hóa phím chữ và phím mũi tên thành một tên thống nhất."""
    key = msvcrt.getch()

    if key in (b"\x00", b"\xe0"):
        second = msvcrt.getch()
        return {
            b"H": "up",
            b"P": "down",
            b"K": "left",
            b"M": "right",
        }.get(second, "unknown")
    if key == b" ":
        return "space"
    if key == b"\r":
        return "enter"
    if key == b"\x1b":
        return "esc"
    try:
        return key.decode("utf-8").lower()
    except UnicodeDecodeError:
        return "unknown"


def clear_screen():
    last_frame_lines.clear()
    write_terminal("\033[3J\033[2J\033[H")


# ==========================================
# TAB LỊCH SỬ TOP 10 ĐIỂM CAO NHẤT
# ==========================================
def show_highscores():
    """Hiển thị bảng xếp hạng lưu lịch sử 10 lần điểm cao nhất."""
    scores = load_highscores()
    lines = [
        "╔══════════════════════════════════════════════════════════╗",
        "║               TOP 10 LỊCH SỬ ĐIỂM CAO NHẤT               ║",
        "╠══════╦════════════╦════════╦══════════╦══════════════════╣",
        "║ HẠNG ║    ĐIỂM    ║  HÀNG  ║  ĐỘ KHÓ  ║    THỜI GIAN     ║",
        "╠══════╬════════════╬════════╬══════════╬══════════════════╣",
    ]
    for rank in range(1, MAX_HIGHSCORES + 1):
        if rank <= len(scores):
            item = scores[rank - 1]
            rank_str = f"#{rank}".center(4)
            score_str = f"{item['score']:,}".rjust(10)
            lines_str = str(item["lines"]).center(6)
            diff_str = item["difficulty"].center(8)
            date_str = item["date"].center(16)
        else:
            rank_str = f"#{rank}".center(4)
            score_str = "---".center(10)
            lines_str = "---".center(6)
            diff_str = "---".center(8)
            date_str = "--/--/---- --:--".center(16)
        lines.append(
            f"║ {rank_str} ║ {score_str} ║ {lines_str} ║ {diff_str} ║ {date_str} ║"
        )
    lines.extend([
        "╚══════╩════════════╩════════╩══════════╩══════════════════╝",
        "",
        "Nhấn phím bất kỳ để quay lại menu chính...",
    ])
    clear_screen()
    write_terminal("\n".join(lines) + "\n")
    read_key()


# ==========================================
# TAB HƯỚNG DẪN ĐIỀU KHIỂN & TÍNH ĐIỂM
# ==========================================
def show_guide():
    """Hiển thị toàn bộ hướng dẫn điều khiển và cơ chế tính điểm."""
    lines = [
        "╔══════════════════════════════════════════════════════╗",
        "║                 HƯỚNG DẪN CHƠI TETRIS                ║",
        "╠══════════════════════════════════════════════════════╣",
        "║  ĐIỀU KHIỂN TRONG GAME:                              ║",
        "║   • A / D hoặc ← / →   : Di chuyển / giữ để trượt    ║",
        "║   • W hoặc ↑           : Xoay cùng chiều kim đồng hồ ║",
        "║   • Z                  : Xoay ngược chiều kim đồng hồ║",
        "║   • S / X hoặc ↓       : Rơi nhanh (+1 điểm / ô)     ║",
        "║   • Space              : Rơi lập tức (+2 điểm / ô)   ║",
        "║   • Q hoặc Esc         : Thoát ván chơi về menu      ║",
        "╠══════════════════════════════════════════════════════╣",
        "║  CÁCH TÍNH ĐIỂM:                                     ║",
        "║   • Xóa 1 hàng (Single) : 100 điểm                   ║",
        "║   • Xóa 2 hàng (Double) : 300 điểm                   ║",
        "║   • Xóa 3 hàng (Triple) : 500 điểm                   ║",
        "║   • Xóa 4 hàng (Tetris) : 800 điểm                   ║",
        "║   • Hệ số độ khó        : EASY x1 | NORMAL x2 | HARD x3║",
        "╚══════════════════════════════════════════════════════╝",
        "",
        "Nhấn phím bất kỳ để quay lại menu chính...",
    ]
    clear_screen()
    write_terminal("\n".join(lines) + "\n")
    read_key()


# ==========================================
# JD05: MENU PLAY / DIFFICULTY / HIGH SCORES / GUIDE / EXIT
# ==========================================
def show_menu():
    """Trả về (tên độ khó, tốc độ rơi, hệ số điểm), hoặc None nếu chọn thoát."""
    difficulty_index = 1
    selected_index = 0

    while True:
        difficulty_name, fall_delay, _ = DIFFICULTIES[difficulty_index]
        best_score = get_highest_score()
        options = [
            "PLAY",
            f"DIFFICULTY: {difficulty_name}",
            "HIGH SCORES",
            "GUIDE",
            "EXIT",
        ]
        lines = [
            "╔════════════════════════════════════╗",
            "║              TETRIS                ║",
            "╚════════════════════════════════════╝",
            f"  HIGHEST SCORE: {best_score:,}",
            "",
        ]
        for index, option in enumerate(options):
            cursor = "❯" if index == selected_index else " "
            lines.append(f"  {cursor} {option}")
        lines.extend([
            "",
            "W/S hoặc ↑/↓: chọn mục | Enter: xác nhận",
            "A/D hoặc ←/→: đổi độ khó tại DIFFICULTY",
            "Phím tắt: 1: PLAY | 2: Độ khó | 3: Top 10 | 4: GUIDE | 5: EXIT",
        ])
        clear_screen()
        write_terminal("\n".join(lines) + "\n")

        key = read_key()
        if key in ("up", "w"):
            selected_index = (selected_index - 1) % len(options)
        elif key in ("down", "s"):
            selected_index = (selected_index + 1) % len(options)
        elif key in ("left", "a") and selected_index == 1:
            difficulty_index = (difficulty_index - 1) % len(DIFFICULTIES)
        elif key in ("right", "d") and selected_index == 1:
            difficulty_index = (difficulty_index + 1) % len(DIFFICULTIES)
        elif key == "1":
            return DIFFICULTIES[difficulty_index]
        elif key == "2":
            selected_index = 1
            difficulty_index = (difficulty_index + 1) % len(DIFFICULTIES)
        elif key == "3":
            selected_index = 2
            show_highscores()
        elif key == "4":
            selected_index = 3
            show_guide()
        elif key in ("5", "q", "esc"):
            return None
        elif key == "enter":
            if selected_index == 0:
                return DIFFICULTIES[difficulty_index]
            if selected_index == 1:
                difficulty_index = (difficulty_index + 1) % len(DIFFICULTIES)
            elif selected_index == 2:
                show_highscores()
            elif selected_index == 3:
                show_guide()
            else:
                return None


# ==========================================
# JD05: VÒNG LẶP GAME VÀ ĐIỀU KHIỂN
# ==========================================
def play_game(difficulty, base_fall_delay, score_multiplier):
    init_board()
    bag = BlockBag()
    current_block = bag.next_block()
    next_block = bag.next_block()
    fall_delay = base_fall_delay
    total_lines = 0
    score = 0
    best_score = get_highest_score()
    last_fall_time = time.monotonic()

    # Trạng thái giữ phím mượt (DAS / ARR)
    move_dir = None
    move_hold_start = 0.0
    last_auto_move = 0.0
    soft_drop_active = False
    last_soft_drop = 0.0

    # Trạng thái độ trễ khóa khối (Lock Delay)
    lock_start_time = None
    lock_move_count = 0

    clear_screen()
    write_terminal("\033[?25l")  # Ẩn con trỏ trong lúc chơi.

    try:
        if not current_block.can_move(0, 0):
            draw(total_lines, fall_delay, difficulty, next_block, score, best_score)
            write_terminal(f"\nGAME OVER! Điểm đạt được: {score} | Nhấn phím bất kỳ để về menu.\n")
            read_key()
            return

        current_block.to_board()
        draw(total_lines, fall_delay, difficulty, next_block, score, best_score)

        def register_lock_adjustment(now_ts):
            nonlocal lock_start_time, lock_move_count
            if not current_block.can_move(0, 1) and lock_move_count < MAX_LOCK_MOVES:
                lock_start_time = now_ts
                lock_move_count += 1

        while True:
            now = time.monotonic()
            needs_redraw = False
            hard_dropped = False
            current_block.del_from_board()

            # 1. Đọc các sự kiện bấm phím mới từ hàng đợi
            while msvcrt.kbhit():
                key = read_key()
                if key in ("a", "left"):
                    if move_dir != "left":
                        if current_block.can_move(-1, 0):
                            current_block.x -= 1
                            needs_redraw = True
                            register_lock_adjustment(now)
                        move_dir = "left"
                        move_hold_start = now
                        last_auto_move = now
                elif key in ("d", "right"):
                    if move_dir != "right":
                        if current_block.can_move(1, 0):
                            current_block.x += 1
                            needs_redraw = True
                            register_lock_adjustment(now)
                        move_dir = "right"
                        move_hold_start = now
                        last_auto_move = now
                elif key in ("s", "x", "down"):
                    if not soft_drop_active:
                        if current_block.can_move(0, 1):
                            current_block.y += 1
                            score += 1
                            last_fall_time = now
                            needs_redraw = True
                        soft_drop_active = True
                        last_soft_drop = now
                elif key == "space":
                    dropped_rows = 0
                    while current_block.can_move(0, 1):
                        current_block.y += 1
                        dropped_rows += 1
                    score += dropped_rows * 2
                    hard_dropped = True
                    needs_redraw = True
                    while msvcrt.kbhit():
                        read_key()
                    break
                elif key in ("w", "up"):
                    if current_block.rotate(clockwise=True):
                        needs_redraw = True
                        register_lock_adjustment(now)
                elif key == "z":
                    if current_block.rotate(clockwise=False):
                        needs_redraw = True
                        register_lock_adjustment(now)
                elif key in ("q", "esc"):
                    return

            # 2. Xử lý giữ phím trượt ngang mượt (DAS / ARR)
            if move_dir == "left":
                if is_any_key_down(VK_LEFT_KEYS):
                    if now - move_hold_start >= DAS_DELAY and now - last_auto_move >= ARR_INTERVAL:
                        if current_block.can_move(-1, 0):
                            current_block.x -= 1
                            needs_redraw = True
                            register_lock_adjustment(now)
                        last_auto_move = now
                else:
                    move_dir = None
            elif move_dir == "right":
                if is_any_key_down(VK_RIGHT_KEYS):
                    if now - move_hold_start >= DAS_DELAY and now - last_auto_move >= ARR_INTERVAL:
                        if current_block.can_move(1, 0):
                            current_block.x += 1
                            needs_redraw = True
                            register_lock_adjustment(now)
                        last_auto_move = now
                else:
                    move_dir = None

            # 3. Xử lý giữ phím rơi nhanh mượt (Soft Drop)
            if soft_drop_active:
                if is_any_key_down(VK_DOWN_KEYS):
                    if now - last_soft_drop >= SOFT_DROP_INTERVAL:
                        if current_block.can_move(0, 1):
                            current_block.y += 1
                            score += 1
                            last_fall_time = now
                            needs_redraw = True
                        last_soft_drop = now
                else:
                    soft_drop_active = False

            # 4. Trọng lực rơi tự động & cơ chế Lock Delay 0.5s
            if current_block.can_move(0, 1):
                lock_start_time = None
                if now - last_fall_time >= fall_delay:
                    current_block.y += 1
                    last_fall_time = now
                    needs_redraw = True
                    if not current_block.can_move(0, 1):
                        lock_start_time = now
            else:
                if lock_start_time is None:
                    lock_start_time = now

                if hard_dropped or (now - lock_start_time >= LOCK_DELAY):
                    current_block.to_board()
                    cleared = remove_line()
                    total_lines += cleared

                    if cleared > 0:
                        score += LINE_SCORES.get(cleared, cleared * 200) * score_multiplier
                        fall_delay = max(
                            MIN_FALL_DELAY,
                            fall_delay * (0.9 ** cleared),
                        )

                    current_block = next_block
                    next_block = bag.next_block()
                    lock_start_time = None
                    lock_move_count = 0
                    last_fall_time = now
                    needs_redraw = True

                    if not current_block.can_move(0, 0):
                        rank = record_score(score, total_lines, difficulty)
                        final_best = max(best_score, score)
                        draw(total_lines, fall_delay, difficulty, next_block, score, final_best)

                        if rank == 1:
                            badge = " | ★ KỶ LỤC MỚI (#1)!"
                        elif rank is not None:
                            badge = f" | ★ Lọt Top #{rank}!"
                        else:
                            badge = ""

                        write_terminal(
                            f"\nGAME OVER! Điểm: {score:,}{badge}\n"
                            "Nhấn phím bất kỳ để về menu.\n"
                        )
                        read_key()
                        return

            current_block.to_board()
            if needs_redraw:
                draw(total_lines, fall_delay, difficulty, next_block, score, best_score)
            time.sleep(0.004)  # Chu kỳ vòng lặp ~250Hz
    finally:
        write_terminal("\033[?25h")  # Hiện con trỏ khi rời màn chơi.


def main():
    random.seed()
    os.system("")

    timer_boosted = False
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
        timer_boosted = True
    except Exception:
        pass

    try:
        while True:
            selected = show_menu()
            if selected is None:
                break
            difficulty_name, base_fall_delay, score_multiplier = selected
            play_game(difficulty_name, base_fall_delay, score_multiplier)
    except KeyboardInterrupt:
        pass
    finally:
        if timer_boosted:
            try:
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass
        write_terminal("\033[?25h\n")


if __name__ == "__main__":
    main()