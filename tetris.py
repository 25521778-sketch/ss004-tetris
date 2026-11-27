import ctypes
from ctypes import wintypes
import os
import random
import shutil
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

H = 24  # Chiều cao bàn chơi (22 hàng chơi + 2 hàng viền).
W = 15
board = [[" " for _ in range(W)] for _ in range(H)]

# JD05: Tốc độ rơi ban đầu ứng với từng độ khó (giây / ô).
DIFFICULTIES = [
    ("EASY", 0.8),
    ("NORMAL", 0.5),
    ("HARD", 0.2),
]
MIN_FALL_DELAY = 0.08  # JD03: Không để tốc độ rơi tăng vô hạn.

# Kích thước khung ngoài thống nhất cho cả Menu chính và Màn chơi.
UI_WIDTH = 66
UI_HEIGHT = H + 2  # 26 dòng (gồm viền ngoài trên/dưới + 24 dòng nội dung).
SIDE_PANEL_INNER_W = 28  # Chiều rộng nội dung bảng thông số bên phải.

# Nội dung Guide dùng chung cho menu chính và Pause Menu.
GUIDE_ITEMS = [
    "A / ←         : Di chuyển sang trái",
    "D / →         : Di chuyển sang phải",
    "W / ↑         : Xoay thuận chiều kim đồng hồ",
    "Z             : Xoay ngược chiều kim đồng hồ",
    "S / X / ↓     : Rơi nhanh",
    "SPACE         : Rơi tức thì",
    "P             : Tạm dừng / tiếp tục",
    "Q / ESC       : Về menu",
    "",
    "Nhấn phím bất kỳ để trở về.",
]

# Hệ thống điểm: Single / Double / Triple / Tetris (4 hàng).
LINE_CLEAR_POINTS = {1: 100, 2: 300, 3: 500, 4: 800}
COMBO_BONUS = 50
LINES_PER_LEVEL = 10


# ==========================================
# HỖ TRỢ ANSI, ALTERNATE SCREEN & VẼ KHÔNG CUỘN
# ==========================================
ANSI_ENABLED = False
_WIN32_HANDLE = None


class _COORD(ctypes.Structure):
    _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]


class _SMALL_RECT(ctypes.Structure):
    _fields_ = [
        ("Left", wintypes.SHORT),
        ("Top", wintypes.SHORT),
        ("Right", wintypes.SHORT),
        ("Bottom", wintypes.SHORT),
    ]


class _CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
    _fields_ = [
        ("dwSize", _COORD),
        ("dwCursorPosition", _COORD),
        ("wAttributes", wintypes.WORD),
        ("srWindow", _SMALL_RECT),
        ("dwMaximumWindowSize", _COORD),
    ]


def enable_windows_ansi():
    """Kích hoạt Virtual Terminal (ANSI) trên Windows Console bằng Win32 API."""
    global ANSI_ENABLED, _WIN32_HANDLE

    if os.name != "nt":
        ANSI_ENABLED = True
        return True

    # Hỗ trợ các terminal Unix-like trên Windows (Git Bash / mintty / WT / VS Code).
    env_ansi = bool(
        os.environ.get("WT_SESSION")
        or os.environ.get("TERM_PROGRAM")
        or os.environ.get("TERM")
    )

    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
        kernel32.GetStdHandle.restype = wintypes.HANDLE
        kernel32.GetConsoleMode.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.GetConsoleMode.restype = wintypes.BOOL
        kernel32.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.SetConsoleMode.restype = wintypes.BOOL

        STD_OUTPUT_HANDLE = wintypes.DWORD(-11)
        ENABLE_PROCESSED_OUTPUT = 0x0001
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        _WIN32_HANDLE = handle
        mode = wintypes.DWORD()
        if handle and kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            new_mode = (
                mode.value
                | ENABLE_PROCESSED_OUTPUT
                | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            )
            if kernel32.SetConsoleMode(handle, new_mode):
                ANSI_ENABLED = True
                return True
    except Exception:
        pass

    # Dự phòng: kích hoạt qua shell mặc định nếu terminal hỗ trợ.
    os.system("")
    ANSI_ENABLED = env_ansi
    return ANSI_ENABLED


def enter_screen_mode():
    """Vào Alternate Screen Buffer, tắt auto-wrap và ẩn con trỏ để chống cuộn."""
    if ANSI_ENABLED:
        # ?1049h: mở màn hình phụ (không có thanh cuộn lịch sử)
        # ?7l   : tắt tự động xuống dòng khi chạm mép phải
        # ?25l  : ẩn con trỏ nhấp nháy
        sys.stdout.write("\033[?1049h\033[?7l\033[?25l\033[2J\033[1;1H")
        sys.stdout.flush()
    else:
        os.system("cls" if os.name == "nt" else "clear")


def exit_screen_mode():
    """Khôi phục lại màn hình terminal gốc khi thoát trò chơi."""
    if ANSI_ENABLED:
        sys.stdout.write("\033[?7h\033[?25h\033[?1049l")
        sys.stdout.flush()


def get_terminal_size():
    size = shutil.get_terminal_size(fallback=(80, 28))
    return size.columns, size.lines


def _render_frame_win32(lines, term_cols, term_rows):
    """Fallback dùng Win32 API ghi đè trực tiếp lên viewport nếu không có ANSI."""
    try:
        kernel32 = ctypes.windll.kernel32
        csbi = _CONSOLE_SCREEN_BUFFER_INFO()
        if not _WIN32_HANDLE or not kernel32.GetConsoleScreenBufferInfo(
            _WIN32_HANDLE, ctypes.byref(csbi)
        ):
            raise OSError("No console buffer")

        top_y = csbi.srWindow.Top
        max_cols = max(1, term_cols - 1)
        written = wintypes.DWORD()
        for idx in range(term_rows):
            text = lines[idx][:max_cols] if idx < len(lines) else ""
            padded = text.ljust(max_cols)
            kernel32.SetConsoleCursorPosition(
                _WIN32_HANDLE, _COORD(0, top_y + idx)
            )
            kernel32.WriteConsoleW(
                _WIN32_HANDLE, padded, len(padded), ctypes.byref(written), None
            )
        return
    except Exception:
        os.system("cls" if os.name == "nt" else "clear")
        max_cols = max(1, term_cols - 1)
        sys.stdout.write(
            "\n".join(line[:max_cols] for line in lines[: max(1, term_rows - 1)])
        )
        sys.stdout.flush()


def render_frame(lines):
    """Vẽ từng dòng theo tọa độ tuyệt đối (row, 1), không dùng ký tự xuống dòng để không cuộn."""
    term_cols, term_rows = get_terminal_size()
    max_cols = max(1, term_cols - 1)  # Chừa 1 cột cuối để không kích hoạt wrap-scroll.
    frame_width = max((len(line) for line in lines), default=UI_WIDTH)
    frame_height = len(lines)

    display_lines = list(lines)
    if term_rows < frame_height or term_cols < frame_width:
        warning = (
            f"[!] Terminal quá nhỏ ({term_cols}x{term_rows}), "
            f"cần >= {frame_width}x{frame_height}. Kéo rộng thêm!"
        )
        if term_rows >= 1:
            if len(display_lines) < term_rows:
                display_lines.extend([""] * (term_rows - len(display_lines)))
            display_lines[term_rows - 1] = warning[:max_cols]

    if not ANSI_ENABLED:
        _render_frame_win32(display_lines, term_cols, term_rows)
        return

    # Ghi từng dòng bằng mã định vị tuyệt đối ESC[row;1H (không chứa ký tự xuống dòng).
    chunks = []
    for row_idx in range(1, term_rows + 1):
        text = display_lines[row_idx - 1][:max_cols] if row_idx <= len(display_lines) else ""
        chunks.append(f"\033[{row_idx};1H{text}\033[K")
    sys.stdout.write("".join(chunks))
    sys.stdout.flush()


def compose_overlay(base_lines, panel_lines):
    """Chồng bảng nổi (Pause/Guide/Game Over) vào giữa khung nền rồi vẽ 1 lần, tránh nháy."""
    merged = list(base_lines)
    base_height = len(merged)
    base_width = max((len(line) for line in merged), default=UI_WIDTH)
    panel_height = len(panel_lines)
    panel_width = max((len(line) for line in panel_lines), default=0)
    canvas_width = max(base_width, panel_width)

    start_row = max(0, (base_height - panel_height) // 2)
    start_col = max(0, (canvas_width - panel_width) // 2)

    for offset, panel_line in enumerate(panel_lines):
        target_row = start_row + offset
        if target_row >= base_height:
            merged.append(panel_line.center(canvas_width))
            continue
        bg = merged[target_row].ljust(canvas_width)
        end_col = start_col + len(panel_line)
        merged[target_row] = bg[:start_col] + panel_line + bg[end_col:]
    return merged


class GameStats:
    """Lưu điểm, số hàng đã xóa, cấp độ và chuỗi Combo hiện tại."""

    def __init__(self):
        self.score = 0
        self.total_lines = 0
        self.level = 1
        self.combo = 0
        self._clear_streak = 0

    def record_lock(self, cleared):
        """Gọi khi một khối đã chạm đáy; trả về điểm của lượt đặt khối.

        Combo 1 là lần xóa hàng thứ hai liên tiếp, không có lượt đặt
        khối nào xen giữa mà không xóa được hàng.
        """
        if cleared == 0:
            self._clear_streak = 0
            self.combo = 0
            return 0
        if cleared not in LINE_CLEAR_POINTS:
            raise ValueError("Mỗi khối chỉ có thể xóa từ 1 đến 4 hàng")

        self._clear_streak += 1
        self.combo = self._clear_streak - 1
        # Dùng Level trước lượt xóa hiện tại để nhân điểm.
        earned = (LINE_CLEAR_POINTS[cleared] + COMBO_BONUS * self.combo) * self.level
        self.score += earned
        self.total_lines += cleared
        self.level = 1 + self.total_lines // LINES_PER_LEVEL
        return earned


# ==========================================
# JD01: LỚP CHA VÀ CÁC LỚP KHỐI KẾ THỪA
# ==========================================
def matrix(*rows):
    return [list(row) for row in rows]


class Block:
    def __init__(self, x=5, y=1, shape=None):
        self.x, self.y, self.shape = x, y, shape or []

    def can_move(self, dx, dy, target_shape=None):
        shape = target_shape or self.shape
        return all(
            1 <= self.x + j + dx < W - 1
            and self.y + i + dy < H - 1
            and board[self.y + i + dy][self.x + j + dx] == " "
            for i, row in enumerate(shape) for j, cell in enumerate(row) if cell != " "
        )

    def _put(self, value):
        for i, row in enumerate(self.shape):
            for j, cell in enumerate(row):
                if cell != " ":
                    board[self.y + i][self.x + j] = value

    def to_board(self):
        for i, row in enumerate(self.shape):
            for j, cell in enumerate(row):
                if cell != " ":
                    board[self.y + i][self.x + j] = cell

    def del_from_board(self):
        self._put(" ")

    def rotate(self, clockwise=True):
        rotated = [list(row) for row in (zip(*self.shape[::-1]) if clockwise else zip(*self.shape[::-1]))]
        if not clockwise:
            rotated = [list(row) for row in zip(*self.shape)][::-1]
        if self.can_move(0, 0, rotated):
            self.shape = rotated

    def rotate_counterclockwise(self):
        self.rotate(False)


class BlockO(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y, matrix("    ", " OO ", " OO ", "    "))

    def rotate(self, clockwise=True):
        pass

    rotate_counterclockwise = rotate


class BlockI(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y, matrix(" I  ", " I  ", " I  ", " I  "))
        self.is_vertical = True

    def rotate(self, clockwise=True):
        rotated = matrix("    ", "IIII", "    ", "    ") if self.is_vertical else matrix(" I  ", " I  ", " I  ", " I  ")
        for dx in (0, -1, 1, -2, 2):
            if self.can_move(dx, 0, rotated):
                self.x += dx
                self.shape, self.is_vertical = rotated, not self.is_vertical
                break

    rotate_counterclockwise = rotate


# Các khối còn lại dùng chung cách xoay và kiểm tra va chạm của lớp Block.
class BlockT(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y, matrix(" T ", "TTT", "   "))


class BlockS(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y, matrix(" SS", "SS ", "   "))


class BlockZ(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y, matrix("ZZ ", " ZZ", "   "))


class BlockJ(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y, matrix("J  ", "JJJ", "   "))


class BlockL(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y, matrix("  L", "LLL", "   "))


def spawn_block():
    return random.choice((BlockI, BlockO, BlockT, BlockS, BlockZ, BlockJ, BlockL))(5, 1)


# ==========================================
# JD01: KHỞI TẠO BÀN CHƠI
# ==========================================
def init_board():
    for i in range(H):
        board[i] = ["#" if i in (0, H - 1) or j in (0, W - 1) else " " for j in range(W)]


# ==========================================
# JD04: KHUNG NGOÀI ĐỒNG BỘ & Ô VUÔNG VỨC
# ==========================================
CELL_BLOCK = "██"
CELL_EMPTY = "  "


def render_board_row(i):
    """Vẽ một dòng của khung bàn chơi (viền đơn để phân tách với khung ngoài viền đôi)."""
    board_inner_w = 2 * (W - 2)
    if i == 0:
        return "┌" + "─" * board_inner_w + "┐"
    if i == H - 1:
        return "└" + "─" * board_inner_w + "┘"
    cells = "".join(
        CELL_EMPTY if board[i][j] == " " else CELL_BLOCK
        for j in range(1, W - 1)
    )
    return "│" + cells + "│"


def build_stats_box(total_lines, fall_delay, difficulty, paused, score, level, combo):
    """Tạo khung thông số bên phải."""
    w = SIDE_PANEL_INNER_W
    status_badge = "*** TẠM DỪNG ***" if paused else ""
    return [
        "┌" + "─" * w + "┐",
        "│" + "TETRIS".center(w) + "│",
        "├" + "─" * w + "┤",
        "│" + f"  Độ khó     : {difficulty}".ljust(w) + "│",
        "│" + f"  Điểm       : {score}".ljust(w) + "│",
        "│" + f"  Level      : {level}".ljust(w) + "│",
        "│" + f"  Hàng đã xóa: {total_lines}".ljust(w) + "│",
        "│" + f"  Combo      : {combo}".ljust(w) + "│",
        "│" + status_badge.center(w) + "│",
        "└" + "─" * w + "┘",
    ]


def build_next_box(next_block):
    """Tạo khung Next Block và căn giữa hình khối kế tiếp."""
    w = SIDE_PANEL_INNER_W
    box = [
        "┌" + "─" * w + "┐",
        "│" + "NEXT BLOCK".center(w) + "│",
        "├" + "─" * w + "┤",
    ]
    shape = next_block.shape
    for row in shape:
        cells = "".join("██" if cell != " " else "  " for cell in row)
        box.append("│" + cells.center(w) + "│")
    box.append("└" + "─" * w + "┘")
    return box


def build_game_frame(total_lines=0, fall_delay=1.5, difficulty="NORMAL",
                     paused=False, score=0, level=1, combo=0, next_block=None):
    """Tạo màn chơi với Next Block phía trên bảng thông số."""
    outer_inner_w = UI_WIDTH - 2
    stats_box = build_stats_box(
        total_lines, fall_delay, difficulty, paused, score, level, combo
    )
    next_box = build_next_box(next_block) if next_block else []
    side_box = next_box + stats_box
    side_box_w = SIDE_PANEL_INNER_W + 2

    lines = ["╔" + "═" * outer_inner_w + "╗"]
    for i in range(H):
        left_part = render_board_row(i)
        right_part = side_box[i] if i < len(side_box) else " " * side_box_w
        content = f"  {left_part}  {right_part}  "
        lines.append("║" + content.ljust(outer_inner_w)[:outer_inner_w] + "║")
    lines.append("╚" + "═" * outer_inner_w + "╝")
    return lines
def draw(total_lines=0, fall_delay=1.5, difficulty="NORMAL", paused=False,
         score=0, level=1, combo=0, next_block=None, overlay=None):
    """Vẽ màn chơi tại tọa độ cố định (1, 1); hỗ trợ ghép bảng nổi không nháy."""
    frame = build_game_frame(
        total_lines=total_lines,
        fall_delay=fall_delay,
        difficulty=difficulty,
        paused=paused,
        score=score,
        level=level,
        combo=combo,
        next_block=next_block,
    )
    if overlay is not None:
        frame = compose_overlay(frame, overlay)
    render_frame(frame)


def make_panel(title, body_lines, width=UI_WIDTH, body_align="center", height=None):
    """Tạo bảng nổi hoặc màn hình con; nếu truyền height thì tự căn chiều cao đồng bộ."""
    inner = width - 2
    formatted_body = []
    for line in body_lines:
        line = line[:inner]
        if body_align == "left":
            formatted_body.append("║" + line.ljust(inner) + "║")
        else:
            formatted_body.append("║" + line.center(inner) + "║")

    if height is not None:
        # 4 dòng cố định: top, title, separator, bottom.
        target_body_rows = max(len(formatted_body), height - 4)
        extra = target_body_rows - len(formatted_body)
        top_pad = extra // 2
        bottom_pad = extra - top_pad
        blank_row = "║" + " " * inner + "║"
        formatted_body = [blank_row] * top_pad + formatted_body + [blank_row] * bottom_pad

    lines = [
        "╔" + "═" * inner + "╗",
        "║" + title.center(inner) + "║",
        "╠" + "═" * inner + "╣",
    ]
    lines.extend(formatted_body)
    lines.append("╚" + "═" * inner + "╝")
    return lines


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
            # Không giảm current_row: cần kiểm tra tiếp hàng vừa được dồn xuống.
        else:
            current_row -= 1
    return lines_cleared


# ==========================================
# JD05: ĐỌC WASD VÀ PHÍM MŨI TÊN WINDOWS
# ==========================================
def read_key():
    """Chuẩn hóa phím chữ và phím mũi tên thành một tên thống nhất."""
    key = msvcrt.getch()

    # Phím mũi tên trả về 2 byte, cần đọc byte thứ hai.
    if key in (b"\x00", b"\xe0"):
        second = msvcrt.getch()
        return {b"H": "up", b"P": "down", b"K": "left", b"M": "right"}.get(second, "unknown")
    if key == b"\r":
        return "enter"
    if key == b"\x1b":
        return "esc"
    try:
        return key.decode("utf-8").lower()
    except UnicodeDecodeError:
        return "unknown"


def wait_key_with_resize(redraw_callback):
    """Chờ người dùng nhấn phím, tự động vẽ lại nếu cửa sổ terminal đổi kích thước."""
    last_size = get_terminal_size()
    while True:
        if msvcrt.kbhit():
            return read_key()
        current_size = get_terminal_size()
        if current_size != last_size:
            last_size = current_size
            redraw_callback()
        time.sleep(0.03)


# ==========================================
# JD05: MENU CHÍNH ĐỒNG BỘ UI_WIDTH x UI_HEIGHT
# ==========================================
def build_menu_frame(menu_options, selected_index, difficulty_name):
    """Tạo khung menu chính có đúng kích thước UI_WIDTH x UI_HEIGHT như màn chơi."""
    inner = UI_WIDTH - 2
    blank_row = "║" + " " * inner + "║"
    top = "╔" + "═" * inner + "╗"
    bottom = "╚" + "═" * inner + "╝"
    inner_top = "╠" + "═" * inner + "╣"

    title_art = [
        "┌──────────────────┐",
        "│      TETRIS      │",
        "└──────┐    ┌──────┘",
        "│    │",
        "└────┘",
    ]
    header = [top, blank_row]
    header.extend("║" + line.center(inner) + "║" for line in title_art)
    header.extend([blank_row, inner_top])

    box_width = inner - 6  # Chừa lề 3 trái, 3 phải.
    option_rows = []
    for idx, option in enumerate(menu_options):
        marker = ">" if idx == selected_index else " "
        label = f"DIFFICULTY: {difficulty_name}" if option == "DIFFICULTY" else option
        content = f" {marker} {label}"
        if idx == selected_index:
            option_rows.append("║" + "   ┌" + "─" * (box_width - 2) + "┐   " + "║")
            option_rows.append("║" + "   │" + content.ljust(box_width - 2) + "│   " + "║")
            option_rows.append("║" + "   └" + "─" * (box_width - 2) + "┘   " + "║")
        else:
            option_rows.append("║" + ("    " + content).ljust(inner) + "║")
        if idx < len(menu_options) - 1:
            option_rows.append(blank_row)

    footer = [
        "║" + "W/S hoặc ↑/↓: Chọn mục  |  Enter: Xác nhận".center(inner) + "║",
        "║" + "A/D hoặc ←/→: Thay đổi độ khó".center(inner) + "║",
        bottom,
    ]

    # Căn giữa khối lựa chọn theo chiều dọc để tổng chiều cao luôn đúng bằng UI_HEIGHT.
    remaining = UI_HEIGHT - len(header) - len(option_rows) - len(footer)
    top_pad = max(0, remaining // 2)
    bottom_pad = max(0, remaining - top_pad)

    return header + [blank_row] * top_pad + option_rows + [blank_row] * bottom_pad + footer


def show_menu():
    """Menu chính đóng khung; GUIDE chỉ mở khi chọn và nhấn Enter."""
    difficulty_index = 1  # NORMAL mặc định.
    selected_index = 0
    menu_options = ["PLAY", "DIFFICULTY", "HIGH SCORES", "GUIDE", "EXIT"]

    while True:
        difficulty_name, _fall_delay = DIFFICULTIES[difficulty_index]

        def redraw_menu():
            render_frame(build_menu_frame(menu_options, selected_index, difficulty_name))

        redraw_menu()
        key = wait_key_with_resize(redraw_menu)

        if key in ("up", "w"):
            selected_index = (selected_index - 1) % len(menu_options)
        elif key in ("down", "s"):
            selected_index = (selected_index + 1) % len(menu_options)
        elif key in ("left", "a") and selected_index == 1:
            difficulty_index = (difficulty_index - 1) % len(DIFFICULTIES)
        elif key in ("right", "d") and selected_index == 1:
            difficulty_index = (difficulty_index + 1) % len(DIFFICULTIES)
        elif key == "enter":
            if selected_index == 0:  # PLAY
                return DIFFICULTIES[difficulty_index]
            elif selected_index == 1:  # DIFFICULTY1
                difficulty_index = (difficulty_index + 1) % len(DIFFICULTIES)
            elif selected_index == 2:  # HIGH SCORES
                panel = make_panel(
                    "HIGH SCORES",
                    [
                        "Chưa có điểm cao được lưu.",
                        "",
                        "Nhấn phím bất kỳ để quay lại Menu.",
                    ],
                    width=UI_WIDTH,
                    height=UI_HEIGHT,
                )
                render_frame(panel)
                wait_key_with_resize(lambda: render_frame(panel))
            elif selected_index == 3:  # GUIDE
                guide_lines = ["  " + item if item else "" for item in GUIDE_ITEMS[:-1]] + [
                    "",
                    "  Nhấn phím bất kỳ để quay lại Menu.",
                ]
                panel = make_panel(
                    "GAME GUIDE",
                    guide_lines,
                    width=UI_WIDTH,
                    body_align="left",
                    height=UI_HEIGHT,
                )
                render_frame(panel)
                wait_key_with_resize(lambda: render_frame(panel))
            else:  # EXIT
                return None


# ==========================================
# JD05: VÒNG LẶP GAME VÀ ĐIỀU KHIỂN
# ==========================================
def play_game(difficulty, base_fall_delay):
    init_board()
    current_block = spawn_block()
    next_block = spawn_block()
    fall_delay = base_fall_delay
    stats = GameStats()
    last_fall_time = time.monotonic()
    last_term_size = get_terminal_size()

    def draw_game(paused=False, overlay=None):
        draw(
            stats.total_lines,
            fall_delay,
            difficulty,
            paused=paused,
            score=stats.score,
            level=stats.level,
            combo=stats.combo,
            next_block=next_block,
            overlay=overlay,
        )

    def show_game_over():
        panel = make_panel(
            "GAME OVER",
            [
                "",
                f"Điểm cuối cùng: {stats.score}",
                f"Hàng đã xóa: {stats.total_lines} | Level: {stats.level}",
                "",
                "Nhấn phím bất kỳ để về menu.",
            ],
            width=46,
        )
        draw_game(overlay=panel)
        wait_key_with_resize(lambda: draw_game(overlay=panel))

    if not current_block.can_move(0, 0):
        show_game_over()
        return

    current_block.to_board()
    draw_game()

    while True:
        needs_redraw = False
        current_term_size = get_terminal_size()
        if current_term_size != last_term_size:
            last_term_size = current_term_size
            needs_redraw = True

        current_block.del_from_board()

        # Đọc phím thường xuyên, độc lập với đồng hồ rơi tự động.
        while msvcrt.kbhit():
            key = read_key()
            if key in ("a", "left") and current_block.can_move(-1, 0):
                current_block.x -= 1
                needs_redraw = True
            elif key in ("d", "right") and current_block.can_move(1, 0):
                current_block.x += 1
                needs_redraw = True
            elif key in ("s", "x", "down") and current_block.can_move(0, 1):
                current_block.y += 1
                last_fall_time = time.monotonic()
                needs_redraw = True
            elif key in ("w", "up"):
                current_block.rotate()
                needs_redraw = True
            elif key == "z":
                current_block.rotate_counterclockwise()
                needs_redraw = True
            elif key == " ":
                # Hard-drop: đưa khối xuống vị trí thấp nhất có thể.
                while current_block.can_move(0, 1):
                    current_block.y += 1
                # Kích hoạt xử lý cố định khối ngay ở vòng lặp kế tiếp.
                last_fall_time = time.monotonic() - fall_delay
                needs_redraw = True
            elif key in ("p","esc"):
                current_block.to_board()
                pause_start = time.monotonic()
                pause_options = ["RESUME", "GUIDE", "EXIT"]
                pause_selected = 0
                pause_action = None

                while pause_action is None:
                    panel_w = 46
                    inner_w = panel_w - 2
                    opt_box_w = inner_w - 6
                    pause_body = [""]
                    for idx, option in enumerate(pause_options):
                        if idx == pause_selected:
                            pause_body.extend([
                                "   ┌" + "─" * (opt_box_w - 2) + "┐",
                                "   │" + f" > {option}".ljust(opt_box_w - 2) + "│",
                                "   └" + "─" * (opt_box_w - 2) + "┘",
                            ])
                        else:
                            pause_body.append(f"      {option}")
                    pause_body.append("")
                    pause_body.append("W/S hoặc ↑/↓: Chọn | Enter: Xác nhận".center(inner_w))
                    pause_panel = make_panel(
                        "PAUSED", pause_body, width=panel_w, body_align="left"
                    )

                    def redraw_pause():
                        draw_game(paused=True, overlay=pause_panel)

                    redraw_pause()
                    pause_key = wait_key_with_resize(redraw_pause)
                    if pause_key in ("up", "w"):
                        pause_selected = (pause_selected - 1) % len(pause_options)
                    elif pause_key in ("down", "s"):
                        pause_selected = (pause_selected + 1) % len(pause_options)
                    elif pause_key in ("q", "esc"):
                        pause_action = "EXIT"
                    elif pause_key in ("p", "esc"):
                        pause_action = "RESUME"
                    elif pause_key == "enter":
                        pause_action = pause_options[pause_selected]

                    if pause_action == "GUIDE":
                        guide_lines = ["  " + item if item else "" for item in GUIDE_ITEMS[:-1]] + [
                            "",
                            "  Nhấn phím bất kỳ để quay lại Pause Menu.",
                        ]
                        guide_panel = make_panel(
                            "GAME GUIDE", guide_lines, width=54, body_align="left"
                        )
                        draw_game(paused=True, overlay=guide_panel)
                        wait_key_with_resize(
                            lambda: draw_game(paused=True, overlay=guide_panel)
                        )
                        pause_action = None
                        pause_selected = 1

                if pause_action == "EXIT":
                    return  # Về menu chính, kết thúc lượt chơi.
                last_fall_time += time.monotonic() - pause_start
                current_block.del_from_board()
                needs_redraw = True
            elif key in ("q", "esc"):
                return  # Trở về menu chính.

        now = time.monotonic()
        if now - last_fall_time >= fall_delay:
            last_fall_time = now
            needs_redraw = True
            if current_block.can_move(0, 1):
                current_block.y += 1
            else:
                # Cố định khối trước khi xóa hàng (JD02).
                current_block.to_board()
                cleared = remove_line()
                stats.record_lock(cleared)

                # JD03: Giữ cơ chế cũ: xóa càng nhiều hàng, rơi càng nhanh.
                if cleared > 0:
                    fall_delay = max(
                        MIN_FALL_DELAY,
                        fall_delay * (0.9797 ** cleared),
                    )

                current_block = next_block
                next_block = spawn_block()
                if not current_block.can_move(0, 0):
                    show_game_over()
                    return

        current_block.to_board()
        if needs_redraw:
            draw_game()
        time.sleep(0.01)


def main():
    random.seed()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    enable_windows_ansi()
    enter_screen_mode()

    try:
        while True:
            selected = show_menu()
            if selected is None:
                break
            difficulty_name, base_fall_delay = selected
            play_game(difficulty_name, base_fall_delay)
    except KeyboardInterrupt:
        pass
    finally:
        exit_screen_mode()


if __name__ == "__main__":
    main()
