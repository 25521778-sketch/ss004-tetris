import os
import random
import sys
import time
sys.stdout.reconfigure(encoding='utf-8')

# Trò chơi sử dụng msvcrt để đọc bàn phím không cần nhấn Enter trên Windows.
try:
  import msvcrt
except ImportError:
  print("Mã nguồn này yêu cầu Windows để chạy thư viện msvcrt.")
  sys.exit()

H = 20
W = 15
board = [[" " for _ in range(W)] for _ in range(H)]

# JD05: Tốc độ rơi ban đầu ứng với từng độ khó (giây / ô).
DIFFICULTIES = [
    ("EASY", 0.8),
    ("NORMAL", 0.5),
    ("HARD", 0.2),
]
MIN_FALL_DELAY = 0.08  # JD03: Không để tốc độ rơi tăng vô hạn.

# Hệ thống điểm: Single / Double / Triple / Tetris (4 hàng).
LINE_CLEAR_POINTS = {1: 100, 2: 300, 3: 500, 4: 800}
COMBO_BONUS = 50
LINES_PER_LEVEL = 10


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

  def rotate(self):
    """Phương thức xoay mặc định 90 độ theo chiều kim đồng hồ"""
    size = len(self.shape)
    rotated = [[" " for _ in range(size)] for _ in range(size)]
    for i in range(size):
      for j in range(size):
        rotated[j][size - 1 - i] = self.shape[i][j]

    if self.can_move(0, 0, rotated):
      self.shape = rotated


class BlockO(Block):

  def __init__(self, x=5, y=1):
    super().__init__(x, y)
    self.shape = [
        [" ", " ", " ", " "],
        [" ", "O", "O", " "],
        [" ", "O", "O", " "],
        [" ", " ", " ", " "],
    ]

  def rotate(self):
    pass


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

    def rotate(self):
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
                break


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


def spawn_block():
  block_classes = [BlockI, BlockO, BlockT, BlockS, BlockZ, BlockJ, BlockL]
  chosen_class = random.choice(block_classes)
  return chosen_class(x=5, y=1)


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


def draw(total_lines=0, fall_delay=1.5, difficulty="NORMAL", paused=False,
         score=0, level=1, combo=0):
    # Chỉ đưa con trỏ lên đầu để vẽ lại, tránh xóa trắng cả màn hình.
    content = "\n".join(render_row(i) for i in range(H))
    status = (
        f"\nĐộ khó: {difficulty} | Điểm: {score} | Level: {level}"
        f"\nHàng đã xóa: {total_lines} | Combo: {combo} "
        f"| Tốc độ: {fall_delay:.2f}s/ô"
        "\nA/D hoặc ←/→: di chuyển | W hoặc ↑: xoay"
        "\nS/X hoặc ↓: rơi nhanh | P: tạm dừng | Q/Esc: về menu"
    )
    if paused:
        status += "\n*** TẠM DỪNG *** | P: tiếp tục | Q/Esc: về menu"
    sys.stdout.write("\033[H" + content + status + "\033[J")
    sys.stdout.flush()


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
        return {
            b"H": "up",
            b"P": "down",
            b"K": "left",
            b"M": "right",
        }.get(second, "unknown")
    if key == b"\r":
        return "enter"
    if key == b"\x1b":
        return "esc"
    try:
        return key.decode("utf-8").lower()
    except UnicodeDecodeError:
        return "unknown"


def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


# ==========================================
# JD05: MENU PLAY / DIFFICULTY / EXIT
# ==========================================
def show_menu():
    """Trả về (tên độ khó, tốc độ rơi), hoặc None nếu chọn thoát."""
    difficulty_index = 1  # Chọn NORMAL làm mặc định.
    selected_index = 0     # Trỏ vào PLAY khi mở menu.

    while True:
        difficulty_name, fall_delay = DIFFICULTIES[difficulty_index]
        options = ["PLAY", f"DIFFICULTY: {difficulty_name}", "EXIT"]
        lines = [
            "╔════════════════════════════════════╗",
            "║              TETRIS                ║",
            "╚════════════════════════════════════╝",
            "",
        ]
        for index, option in enumerate(options):
            cursor = "❯" if index == selected_index else " "
            lines.append(f"  {cursor} {option}")
        lines.extend([
            "",
            "W/S hoặc ↑/↓: chọn mục | Enter: xác nhận",
            "A/D hoặc ←/→: đổi độ khó tại DIFFICULTY",
            "Có thể bấm 1: PLAY, 2: đổi độ khó, 3: EXIT",
        ])
        clear_screen()
        print("\n".join(lines), flush=True)

        key = read_key()
        if key in ("up", "w"):
            selected_index = (selected_index - 1) % len(options)
        elif key in ("down", "s"):
            selected_index = (selected_index + 1) % len(options)
        elif key in ("left", "a") and selected_index == 1:
            difficulty_index = (difficulty_index - 1) % len(DIFFICULTIES)
        elif key in ("right", "d") and selected_index == 1:
            difficulty_index = (difficulty_index + 1) % len(DIFFICULTIES)
        elif key == "2":
            selected_index = 1
            difficulty_index = (difficulty_index + 1) % len(DIFFICULTIES)
        elif key == "1":
            return DIFFICULTIES[difficulty_index]
        elif key in ("3", "q", "esc"):
            return None
        elif key == "enter":
            if selected_index == 0:
                return DIFFICULTIES[difficulty_index]
            if selected_index == 1:
                difficulty_index = (difficulty_index + 1) % len(DIFFICULTIES)
            else:
                return None


# ==========================================
# JD05: VÒNG LẶP GAME VÀ ĐIỀU KHIỂN
# ==========================================
def play_game(difficulty, base_fall_delay):
    init_board()
    current_block = spawn_block()
    fall_delay = base_fall_delay
    stats = GameStats()
    last_fall_time = time.monotonic()

    def draw_game(paused=False):
        draw(stats.total_lines, fall_delay, difficulty, paused=paused,
             score=stats.score, level=stats.level, combo=stats.combo)

    clear_screen()
    sys.stdout.write("\033[?25l")  # Ẩn con trỏ trong lúc chơi.
    sys.stdout.flush()

    try:
        if not current_block.can_move(0, 0):
            # Trường hợp không còn chỗ đặt khối đầu tiên.
            draw_game()
            print("\nGAME OVER! Nhấn phím bất kỳ để về menu.", flush=True)
            read_key()
            return

        current_block.to_board()
        draw_game()

        while True:
            needs_redraw = False
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
                elif key == "p":
                    # Giữ nguyên khối đang rơi và hiển thị trạng thái tạm dừng.
                    current_block.to_board()
                    draw_game(paused=True)
                    pause_start = time.monotonic()
                    while True:
                        pause_key = read_key()  # Đợi phím, không cập nhật game.
                        if pause_key == "p":
                            # Bù thời gian pause để khối không rơi bù khi tiếp tục.
                            last_fall_time += time.monotonic() - pause_start
                            needs_redraw = True
                            break
                        if pause_key in ("q", "esc"):
                            return  # Thoát về menu ngay cả khi đang tạm dừng.
                    current_block.del_from_board()
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
                    # Level tăng sau mỗi 10 hàng và nhân điểm theo bảng quy định.
                    if cleared > 0:
                        fall_delay = max(
                            MIN_FALL_DELAY,
                            fall_delay * (0.9 ** cleared),
                        )

                    current_block = spawn_block()
                    # Kiểm tra ngay tại vị trí sinh khối, tránh ghi đè gạch cũ.
                    if not current_block.can_move(0, 0):
                        draw_game()
                        print("\nGAME OVER! Nhấn phím bất kỳ để về menu.", flush=True)
                        read_key()
                        return

            current_block.to_board()
            if needs_redraw:
                draw_game()
            time.sleep(0.01)
    finally:
        sys.stdout.write("\033[?25h")  # Hiện con trỏ khi rời màn chơi.
        sys.stdout.flush()


def main():
    random.seed()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    # Kích hoạt khả năng xử lý mã ANSI trên Windows Console nếu được hỗ trợ.
    os.system("")

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
        sys.stdout.write("\033[?25h\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
