"""JD05: Menu bắt đầu, chọn độ khó và điều khiển bằng WASD/phím mũi tên.

Chương trình chạy trên Windows Terminal/Windows Console và sử dụng mã ANSI.
Các thành viên khác phụ trách xóa hàng, tăng tốc sau khi xóa hàng và chỉnh giao diện.
"""

import os
import random
import sys
import time

try:
    import msvcrt
except ImportError:
    print("Game yeu cau Windows vi su dung thu vien msvcrt.")
    sys.exit(1)

H = 20
W = 15
board = [[' ' for _ in range(W)] for _ in range(H)]

# JD05: Thời gian rơi cơ bản (giây/ô) ứng với từng mức độ khó.
# JD03 sẽ giảm thời gian rơi khi remove_line() trả về số hàng đã xóa.
DIFFICULTIES = (
    ("EASY", 0.80),
    ("NORMAL", 0.50),
    ("HARD", 0.20),
)
FRAME_DELAY = 0.016  # Kiểm tra phím khoảng 60 lần/giây, độc lập với tốc độ rơi.


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
                if matrix[i][j] != ' ':
                    xt = self.x + j + dx
                    yt = self.y + i + dy
                    if xt < 1 or xt >= W - 1 or yt < 1 or yt >= H - 1:
                        return False
                    if board[yt][xt] != ' ':
                        return False
        return True

    def to_board(self):
        for i, row in enumerate(self.shape):
            for j, cell in enumerate(row):
                if cell != ' ':
                    board[self.y + i][self.x + j] = cell

    def del_from_board(self):
        for i, row in enumerate(self.shape):
            for j, cell in enumerate(row):
                if cell != ' ':
                    board[self.y + i][self.x + j] = ' '

    def rotate(self):
        """Xoay khối 90 độ theo chiều kim đồng hồ nếu không bị va chạm."""
        size = len(self.shape)
        rotated = [[' ' for _ in range(size)] for _ in range(size)]
        for i in range(size):
            for j in range(size):
                rotated[j][size - 1 - i] = self.shape[i][j]
        if self.can_move(0, 0, rotated):
            self.shape = rotated


class BlockO(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.shape = [
            [' ', ' ', ' ', ' '],
            [' ', 'O', 'O', ' '],
            [' ', 'O', 'O', ' '],
            [' ', ' ', ' ', ' '],
        ]

    def rotate(self):
        pass


class BlockI(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.is_vertical = True
        self.shape = [
            [' ', 'I', ' ', ' '],
            [' ', 'I', ' ', ' '],
            [' ', 'I', ' ', ' '],
            [' ', 'I', ' ', ' '],
        ]

    def rotate(self):
        if self.is_vertical:
            rotated = [
                [' ', ' ', ' ', ' '],
                ['I', 'I', 'I', 'I'],
                [' ', ' ', ' ', ' '],
                [' ', ' ', ' ', ' '],
            ]
        else:
            rotated = [
                [' ', 'I', ' ', ' '],
                [' ', 'I', ' ', ' '],
                [' ', 'I', ' ', ' '],
                [' ', 'I', ' ', ' '],
            ]
        if self.can_move(0, 0, rotated):
            self.shape = rotated
            self.is_vertical = not self.is_vertical


class BlockT(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.shape = [
            [' ', 'T', ' '],
            ['T', 'T', 'T'],
            [' ', ' ', ' '],
        ]


class BlockS(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.shape = [
            [' ', 'S', 'S'],
            ['S', 'S', ' '],
            [' ', ' ', ' '],
        ]


class BlockZ(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.shape = [
            ['Z', 'Z', ' '],
            [' ', 'Z', 'Z'],
            [' ', ' ', ' '],
        ]


class BlockJ(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.shape = [
            ['J', ' ', ' '],
            ['J', 'J', 'J'],
            [' ', ' ', ' '],
        ]


class BlockL(Block):
    def __init__(self, x=5, y=1):
        super().__init__(x, y)
        self.shape = [
            [' ', ' ', 'L'],
            ['L', 'L', 'L'],
            [' ', ' ', ' '],
        ]


def spawn_block():
    chosen_class = random.choice((BlockI, BlockO, BlockT, BlockS, BlockZ, BlockJ, BlockL))
    return chosen_class(x=5, y=1)  # Hàng số 0 là đường viền trên của bàn chơi.


def init_board():
    for i in range(H):
        for j in range(W):
            board[i][j] = '#' if (i in (0, H - 1) or j in (0, W - 1)) else ' '


def draw():
    frame = "\033[H" + "\n".join("".join(row) for row in board)
    sys.stdout.write(frame + "\n")
    sys.stdout.flush()


def remove_line():
    # TODO (JD02): Xóa hàng đầy và dồn các hàng phía trên xuống.
    # Đề xuất tích hợp: trả về số hàng đã xóa để JD03 tính tốc độ.
    pass


# ==========================================
# JD05: XỬ LÝ BÀN PHÍM (WASD VÀ PHÍM MŨI TÊN)
# ==========================================
def read_key():
    """Đọc phím không chặn và quy đổi thành tên thao tác.

    Trả về None khi người chơi chưa nhấn phím.
    Phím mũi tên trên Windows có hai byte: byte mở đầu b'\\xe0' hoặc
    b'\\x00', sau đó là mã phím; phải đọc đủ cả hai byte.
    """
    if not msvcrt.kbhit():
        return None

    raw = msvcrt.getch()
    if raw in (b'\x00', b'\xe0'):
        scan_code = msvcrt.getch()
        return {
            b'K': 'LEFT',
            b'M': 'RIGHT',
            b'H': 'UP',
            b'P': 'DOWN',
        }.get(scan_code)

    if raw == b'\r':
        return 'ENTER'
    if raw == b'\x1b':
        return 'ESC'

    try:
        char = raw.decode('utf-8').lower()
    except UnicodeDecodeError:
        return None

    return {
        'a': 'LEFT',
        'd': 'RIGHT',
        'w': 'UP',
        's': 'DOWN',
        'x': 'DOWN',  # Giữ phím X để đi xuống như trong mã gốc.
        'q': 'QUIT',
        '1': '1',
        '2': '2',
        '3': '3',
    }.get(char)


def wait_key():
    while True:
        key = read_key()
        if key is not None:
            return key
        time.sleep(FRAME_DELAY)


# ==========================================
# JD05: MENU CHÍNH VÀ LỰA CHỌN ĐỘ KHÓ
# ==========================================
def draw_menu(selection, difficulty_index):
    difficulty, interval = DIFFICULTIES[difficulty_index]
    options = ["PLAY", "DIFFICULTY: " + difficulty, "EXIT"]
    lines = [
        "=" * 37,
        "             T E T R I S",
        "=" * 37,
        "",
    ]
    lines.extend(("   > " if idx == selection else "     ") + option
                 for idx, option in enumerate(options))
    lines.extend([
        "",
        "Up/Down or W/S : select menu item",
        "Left/Right or A/D: change difficulty",
        "Enter          : confirm",
        "1/2/3          : quick menu actions",
        "",
        "Fall interval: {:.2f} seconds".format(interval),
        "=" * 37,
    ])
    sys.stdout.write("\033[2J\033[H" + "\n".join(lines) + "\n")
    sys.stdout.flush()


def main_menu():
    """Trả về thời gian rơi đã chọn (giây); trả về None nếu chọn EXIT."""
    selection = 0
    difficulty_index = 1  # Mặc định chọn độ khó NORMAL.
    draw_menu(selection, difficulty_index)

    while True:
        key = wait_key()
        previous = (selection, difficulty_index)

        if key == 'UP':
            selection = (selection - 1) % 3
        elif key == 'DOWN':
            selection = (selection + 1) % 3
        elif key in ('LEFT', 'RIGHT') and selection == 1:
            direction = 1 if key == 'RIGHT' else -1
            difficulty_index = (difficulty_index + direction) % len(DIFFICULTIES)
        elif key == '2':
            selection = 1
            difficulty_index = (difficulty_index + 1) % len(DIFFICULTIES)
        elif key == '1':
            return DIFFICULTIES[difficulty_index][1]
        elif key in ('3', 'ESC', 'QUIT'):
            return None
        elif key == 'ENTER':
            if selection == 0:
                return DIFFICULTIES[difficulty_index][1]
            if selection == 1:
                difficulty_index = (difficulty_index + 1) % len(DIFFICULTIES)
            else:
                return None

        if (selection, difficulty_index) != previous:
            draw_menu(selection, difficulty_index)


def apply_game_action(current_block, action):
    """Xử lý thao tác của người chơi; trả về True nếu cần vẽ lại bàn."""
    if action == 'LEFT' and current_block.can_move(-1, 0):
        current_block.x -= 1
        return True
    if action == 'RIGHT' and current_block.can_move(1, 0):
        current_block.x += 1
        return True
    if action == 'DOWN' and current_block.can_move(0, 1):
        current_block.y += 1
        return True
    if action == 'UP':
        old_shape = [row[:] for row in current_block.shape]
        current_block.rotate()
        return current_block.shape != old_shape
    return False


def game_over_screen():
    sys.stdout.write("\n      GAME OVER\n      Enter / Q / Esc: back to menu\n")
    sys.stdout.flush()
    while wait_key() not in ('ENTER', 'QUIT', 'ESC'):
        pass


def play_game(drop_interval):
    """Chạy một ván chơi; về menu khi nhấn Q/Esc hoặc kết thúc ván."""
    init_board()
    current_block = spawn_block()

    if not current_block.can_move(0, 0):
        draw()
        game_over_screen()
        return

    current_block.to_board()
    sys.stdout.write("\033[2J")
    draw()
    sys.stdout.write("A/D or Left/Right: move | S/X or Down: down | W or Up: rotate | Q/Esc: menu\n")
    sys.stdout.flush()
    last_fall = time.monotonic()

    while True:
        action = read_key()
        now = time.monotonic()
        if action is None and now - last_fall < drop_interval:
            time.sleep(FRAME_DELAY)
            continue
        if action in ('QUIT', 'ESC'):
            return

        # Tạm xóa khối đang rơi khỏi ma trận để kiểm tra va chạm.
        # Những khối đã chạm đáy vẫn được giữ nguyên trên bàn chơi.
        current_block.del_from_board()
        changed = apply_game_action(current_block, action)

        if now - last_fall >= drop_interval:
            if current_block.can_move(0, 1):
                current_block.y += 1
            else:
                current_block.to_board()  # Cố định khối trước khi xử lý hàng.
                remove_line()             # JD02 chịu trách nhiệm hoàn thiện hàm này.
                # JD03 có thể cập nhật drop_interval dựa trên số hàng đã xóa.
                current_block = spawn_block()
                if not current_block.can_move(0, 0):
                    draw()
                    game_over_screen()
                    return
            last_fall = now
            changed = True

        current_block.to_board()
        if changed:
            draw()
            # Hiển thị dòng hướng dẫn điều khiển phía dưới bàn chơi.
            sys.stdout.write(
                "A/D or Left/Right: move | S/X or Down: down | W or Up: rotate | Q/Esc: menu\n"
            )
            sys.stdout.flush()
        time.sleep(FRAME_DELAY)


def main():
    random.seed()
    os.system('')  # Kích hoạt mã ANSI/VT trên terminal Windows tương thích.
    os.system('cls')
    sys.stdout.write('\033[?25l')  # Ẩn con trỏ terminal.
    sys.stdout.flush()
    try:
        while True:
            interval = main_menu()
            if interval is None:
                return
            play_game(interval)
    finally:
        sys.stdout.write('\033[?25h')  # Hiện lại con trỏ kể cả khi nhấn Ctrl+C.
        sys.stdout.flush()


if __name__ == '__main__':
    main()
