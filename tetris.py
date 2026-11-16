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

# Khởi tạo ma trận (tương đương char board[H][W])
board = [[' ' for _ in range(W)] for _ in range(H)]

x = 5
y = 0
b = 0

blocks = [
    [[' ','I',' ',' '], [' ','I',' ',' '], [' ','I',' ',' '], [' ','I',' ',' ']],
    [[' ','I',' ',' '], [' ','I',' ',' '], [' ','I',' ',' '], [' ','I',' ',' ']],
    [[' ',' ',' ',' '], [' ','O','O',' '], [' ','O','O',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], [' ','O','O',' '], [' ','O','O',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], [' ','O','O',' '], [' ','O','O',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], [' ','O','O',' '], [' ','O','O',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], [' ','O','O',' '], [' ','O','O',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], [' ','O','O',' '], [' ','O','O',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], [' ','O','O',' '], [' ','O','O',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], ['I','I','I','I'], [' ',' ',' ',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], [' ','O','O',' '], [' ','O','O',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], [' ','T',' ',' '], ['T','T','T',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], [' ','S','S',' '], ['S','S',' ',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], ['Z','Z',' ',' '], [' ','Z','Z',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], ['J',' ',' ',' '], ['J','J','J',' '], [' ',' ',' ',' ']],
    [[' ',' ',' ',' '], [' ',' ','L',' '], ['L','L','L',' '], [' ',' ',' ',' ']]
]

def can_move(dx, dy):
    for i in range(4):
        for j in range(4):
            if blocks[b][i][j] != ' ':
                xt = x + j + dx
                yt = y + i + dy
                if xt < 1 or xt >= W - 1 or yt >= H - 1:
                    return False
                if board[yt][xt] != ' ':
                    return False
    return True

def block_to_board():
    for i in range(4):
        for j in range(4):
            if blocks[b][i][j] != ' ':
                board[y+i][x+j] = blocks[b][i][j]

def board_del_block():
    for i in range(4):
        for j in range(4):
            if blocks[b][i][j] != ' ':
                board[y+i][x+j] = ' '

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

def main():
    global x, y, b
    random.seed()
    
    x = 5
    y = 0
    b = random.randint(0, len(blocks) - 1)
    
    init_board()
    
    while True:
        board_del_block()
        
        # Intercept System I/O Interrupt
        if msvcrt.kbhit():
            c = msvcrt.getch()
            try:
                c = c.decode('utf-8').lower()
            except Exception:
                c = ''
                
            if c == 'a' and can_move(-1, 0): x -= 1
            if c == 'd' and can_move(1, 0): x += 1
            if c == 'x' and can_move(0, 1): y += 1
            if c == 'q': break
            
        if can_move(0, 1):
            y += 1
        else:
            block_to_board()
            remove_line()
            x = 5
            y = 0
            b = random.randint(0, len(blocks) - 1)
            
        block_to_board()
        draw()
        time.sleep(0.5) # Sleep thread 500ms

if __name__ == "__main__":
    main()