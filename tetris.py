import os
import time
import random
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Yêu cầu chạy trên Windows Terminal do dùng msvcrt giả lập conio.h
try:
    import msvcrt
except ImportError:
    print("Mã nguồn này yêu cầu Windows để chạy thư viện msvcrt.")
    sys.exit()

H = 20
W = 15

# Khởi tạo ma trận bàn chơi
board = [[' ' for _ in range(W)] for _ in range(H)]


# ==========================================
# LỚP CHA (BASE CLASS) ĐÓNG GÓI DỮ LIỆU KHỐI
# ==========================================
class Block:
    def __init__(self, x=5, y=0):
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
                    if xt < 1 or xt >= W - 1 or yt >= H - 1:
                        return False
                    if board[yt][xt] != ' ':
                        return False
        return True

    def to_board(self):
        size = len(self.shape)
        for i in range(size):
            for j in range(size):
                if self.shape[i][j] != ' ':
                    board[self.y + i][self.x + j] = self.shape[i][j]

    def del_from_board(self):
        size = len(self.shape)
        for i in range(size):
            for j in range(size):
                if self.shape[i][j] != ' ':
                    board[self.y + i][self.x + j] = ' '

    def rotate(self):
        """Phương thức xoay mặc định 90 độ theo chiều kim đồng hồ"""
        size = len(self.shape)
        rotated = [[' ' for _ in range(size)] for _ in range(size)]
        for i in range(size):
            for j in range(size):
                rotated[j][size - 1 - i] = self.shape[i][j]

        if self.can_move(0, 0, rotated):
            self.shape = rotated


# ==========================================
# CÁC LỚP CON KẾ THỪA & ĐA HÌNH PHƯƠNG THỨC ROTATE
# ==========================================
class BlockO(Block):
    def __init__(self, x=5, y=0):
        super().__init__(x, y)
        self.shape = [
            [' ', ' ', ' ', ' '],
            [' ', 'O', 'O', ' '],
            [' ', 'O', 'O', ' '],
            [' ', ' ', ' ', ' ']
        ]

    def rotate(self):
        pass


class BlockI(Block):
    def __init__(self, x=5, y=0):
        super().__init__(x, y)
        self.is_vertical = True
        self.shape = [
            [' ', 'I', ' ', ' '],
            [' ', 'I', ' ', ' '],
            [' ', 'I', ' ', ' '],
            [' ', 'I', ' ', ' ']
        ]

    def rotate(self):
        if self.is_vertical:
            rotated = [
                [' ', ' ', ' ', ' '],
                ['I', 'I', 'I', 'I'],
                [' ', ' ', ' ', ' '],
                [' ', ' ', ' ', ' ']
            ]
        else:
            rotated = [
                [' ', 'I', ' ', ' '],
                [' ', 'I', ' ', ' '],
                [' ', 'I', ' ', ' '],
                [' ', 'I', ' ', ' ']
            ]

        if self.can_move(0, 0, rotated):
            self.shape = rotated
            self.is_vertical = not self.is_vertical


class BlockT(Block):
    def __init__(self, x=5, y=0):
        super().__init__(x, y)
        self.shape = [
            [' ', 'T', ' '],
            ['T', 'T', 'T'],
            [' ', ' ', ' ']
        ]


class BlockS(Block):
    def __init__(self, x=5, y=0):
        super().__init__(x, y)
        self.shape = [
            [' ', 'S', 'S'],
            ['S', 'S', ' '],
            [' ', ' ', ' ']
        ]


class BlockZ(Block):
    def __init__(self, x=5, y=0):
        super().__init__(x, y)
        self.shape = [
            ['Z', 'Z', ' '],
            [' ', 'Z', 'Z'],
            [' ', ' ', ' ']
        ]


class BlockJ(Block):
    def __init__(self, x=5, y=0):
        super().__init__(x, y)
        self.shape = [
            ['J', ' ', ' '],
            ['J', 'J', 'J'],
            [' ', ' ', ' ']
        ]


class BlockL(Block):
    def __init__(self, x=5, y=0):
        super().__init__(x, y)
        self.shape = [
            [' ', ' ', 'L'],
            ['L', 'L', 'L'],
            [' ', ' ', ' ']
        ]


def spawn_block():
    block_classes = [BlockI, BlockO, BlockT, BlockS, BlockZ, BlockJ, BlockL]
    chosen_class = random.choice(block_classes)
    return chosen_class(x=5, y=0)


# ==========================================
# CÁC HÀM QUẢN LÝ BÀN CHƠI & RENDER TỐI ƯU
# ==========================================
def init_board():
    for i in range(H):
        for j in range(W):
            if i == 0 or i == H - 1 or j == 0 or j == W - 1:
                board[i][j] = '#'
            else:
                board[i][j] = ' '


# ==========================================
# GIAO DIỆN VIỀN & GẠCH VUÔNG VỨC (JD 04)
# Ký tự trong console cao gần gấp đôi chiều rộng, nên mỗi ô của
# bàn chơi được vẽ bằng 2 ký tự để trông vuông. Ma trận board
# không đổi, chỉ thay cách hiển thị.
# ==========================================
CELL_BLOCK = '██'   # 1 ô gạch = 2 ký tự khối đặc
CELL_EMPTY = '  '   # 1 ô trống = 2 dấu cách

def render_row(i):
    """Chuyển hàng i của ma trận board thành chuỗi hiển thị."""
    if i == 0:
        return '╔' + '══' * (W - 2) + '╗'
    if i == H - 1:
        return '╚' + '══' * (W - 2) + '╝'
    cells = ''.join(CELL_EMPTY if board[i][j] == ' ' else CELL_BLOCK
                    for j in range(1, W - 1))
    return '║' + cells + '║'

def draw():
    # Đưa con trỏ về góc (1,1) và in đè toàn bộ khung hình trong 1 lần syscall
    frame = "\033[H" + "\n".join(render_row(i) for i in range(H))
    sys.stdout.write(frame + "\n")
    sys.stdout.flush()


def remove_line():
    # TODO (JD 02): Viết logic kiểm tra hàng đầy, xóa hàng và dồn gạch phía trên xuống
    pass


def main():
    random.seed()
    current_block = spawn_block()
    init_board()

    # Kích hoạt VT100/ANSI trên Windows Console, ẩn con trỏ và xóa màn hình 1 lần duy nhất
    os.system('')
    # In được ký tự khung (╔═║) và khối (█) trên console Windows
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.stdout.write('\033[?25l')
    os.system('cls')

    try:
        while True:
            current_block.del_from_board()

            # Đọc phím điều khiển
            if msvcrt.kbhit():
                c = msvcrt.getch()
                try:
                    c = c.decode('utf-8').lower()
                except Exception:
                    c = ''

                if c == 'a' and current_block.can_move(-1, 0):
                    current_block.x -= 1
                elif c == 'd' and current_block.can_move(1, 0):
                    current_block.x += 1
                elif c == 'x' and current_block.can_move(0, 1):
                    current_block.y += 1
                elif c == 'w':
                    current_block.rotate()
                elif c == 'q':
                    break

            # Tự động rơi xuống
            if current_block.can_move(0, 1):
                current_block.y += 1
            else:
                current_block.to_board()
                remove_line()
                current_block = spawn_block()

            current_block.to_board()
            draw()
            time.sleep(0.5)
    finally:
        # Khôi phục lại con trỏ terminal khi thoát game (kể cả khi bấm Ctrl+C)
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()


if __name__ == "__main__":
    main()
