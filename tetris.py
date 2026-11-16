import os
import time
import random
import sys

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
        
        # Chỉ cập nhật nếu trạng thái sau khi xoay không đè lên tường hoặc gạch khác
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
        # Đa hình: Khối vuông O không thay đổi hình dạng khi xoay
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
        # Đa hình: Khối I chuyển đổi qua lại 2 trạng thái dọc/ngang quanh trục cố định
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
    """Khởi tạo ngẫu nhiên 1 trong 7 đối tượng khối gạch"""
    block_classes = [BlockI, BlockO, BlockT, BlockS, BlockZ, BlockJ, BlockL]
    chosen_class = random.choice(block_classes)
    return chosen_class(x=5, y=0)


# ==========================================
# CÁC HÀM QUẢN LÝ BÀN CHƠI
# ==========================================
def init_board():
    for i in range(H):
        for j in range(W):
            if i == 0 or i == H - 1 or j == 0 or j == W - 1:
                board[i][j] = '#'
            else:
                board[i][j] = ' '


def draw():
    os.system('cls' if os.name == 'nt' else 'clear')
    for i in range(H):
        print("".join(board[i]))


def remove_line():
    # TODO (JD 02): Viết logic kiểm tra hàng đầy, xóa hàng và dồn gạch phía trên xuống
    pass


def main():
    random.seed()
    current_block = spawn_block()
    init_board()

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
                # Gọi đa hình: tự động thực thi hàm rotate() tương ứng của từng loại khối
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


if __name__ == "__main__":
    main()