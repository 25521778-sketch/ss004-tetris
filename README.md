# SS004.R11 – Đồ án cuối kì: Game Tetris (Python)

Đồ án cuối kỳ môn Kỹ năng nghề nghiệp: xây dựng trò chơi **Tetris** chạy trên Windows Terminal bằng **Python** chỉ dùng thư viện chuẩn.

## Tính năng chính
- **Gameplay chuẩn hóa:** 7 loại khối (`I, O, T, S, Z, J, L`) sinh theo cơ chế **7-Bag Randomizer**, xoay theo 2 chiều kèm **Wall-kick**, **Ghost Piece**, **Next Block** và **Hold Piece**.
- **3 mức độ khó:** `EASY`, `NORMAL`, `HARD`, tự động tăng tốc độ rơi theo số hàng đã xóa.
- **Giao diện & Theme:** Hỗ trợ 4 bộ giao diện (**CLASSIC, NEON, PASTEL, RETRO**) đổi trực tiếp trên Menu.
- **Tính điểm & Bảng xếp hạng:** Tính điểm theo cấp độ, chuỗi Combo, Hard-drop và tự động lưu **Top 10 High Scores** vào `high_scores.json`.

## Yêu cầu & Cách chạy
- **Hệ điều hành:** Windows (sử dụng `msvcrt` và Win32 API `kernel32` / `user32`).
- **Python:** Python 3.8 trở lên.
- **Terminal khuyến nghị:** Windows Terminal, PowerShell hoặc VS Code Terminal (kích thước tối thiểu `66x26` để hiển thị trọn khung và đủ màu ANSI).

```bash
git clone https://github.com/25521778-sketch/ss004-tetris.git
cd ss004-tetris
python tetris.py
```

## Cấu trúc thư mục
```text
ss004-tetris/
├── tetris.py          # Mã nguồn chính toàn bộ trò chơi
├── high_scores.json   # Tự động tạo khi chơi để lưu Top 10 điểm cao
└── README.md          # Tài liệu mô tả đồ án và quy trình làm việc nhóm
```

## Thành viên
| MSSV | Họ tên |
| :--- | :--- |
| 25521778 | Nguyễn Vũ Thịnh (nhóm trưởng) |
| 26520232 | Huỳnh Trần Bảo Đại |
| 26521055 | Trần Tuấn Kiệt |
| 26521973 | Nguyễn Thanh Anh Thư |
| 26522065 | Nguyễn Bảo Trâm |

**GVHD:** Thầy Nguyễn Văn Toàn

## Công cụ
- **Slack** channel `#01`: bàn bạc, nhận thông báo tự động từ GitHub và Trello
- **Trello**: https://trello.com/b/jlAhk1G0 – quản lý task
- **GitHub**: repo này – quản lý code
- **Overleaf**: https://www.overleaf.com/project/6aef0cebf25252a5a328487e – viết báo cáo LaTeX

## Quy trình làm 1 feature
1. **Slack** – đề xuất & bàn bạc feature trong channel `#01`.
2. **Trello** – tạo card ở cột *To Do*, gán người làm, đặt deadline. Khi bắt đầu làm thì kéo sang *Doing*.
3. **GitHub** – kéo `main` mới nhất rồi tạo nhánh riêng:
   ```bash
   git checkout main && git pull origin main
   git checkout -b feature/<ten-feature>
   # code & test...
   git add . && git commit -m "feat: <mo ta ngan>"
   git push -u origin feature/<ten-feature>
   ```
   Mở Pull Request vào `main`.
4. **Trello** – merge xong thì kéo card sang *Done*.
5. **Slack** – bot GitHub và bot Trello tự gửi thông báo vào channel `#01` khi có push / PR / card chuyển sang *Done*.
6. **Overleaf** – người làm feature viết phần mô tả logic kỹ thuật của feature đó vào báo cáo.

## Quy ước
- Không push thẳng lên `main`; mọi thay đổi đi qua Pull Request.
- Tên nhánh: `feature/...` (hoặc `feat/...`), `fix/...`, `docs/...`.
- Commit message: `feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`.