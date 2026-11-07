# SS004.R11 – Đồ án cuối kì: Game Tetris (C++)

Repo code của nhóm. Mã nguồn gốc: `Tetris.cpp` (file của thầy).

## Thành viên
| MSSV | Họ tên |
|---|---|
| 25521778 | Nguyễn Vũ Thịnh (nhóm trưởng) |
| 26520232 | Huỳnh Trần Bảo Đại |
| 26521055 | Trần Tuấn Kiệt |
| 26521973 | Nguyễn Thanh Anh Thư |
| 26522065 | Nguyễn Bảo Trâm |

GV: thầy Toàn (toannv@uit.edu.vn)

## Công cụ
- **Slack** `#doancuoiki`: bàn bạc, nhận thông báo tự động từ GitHub và Trello
- **Trello**: https://trello.com/b/jlAhk1G0 – quản lý task
- **GitHub**: repo này – quản lý code
- **Overleaf**: https://www.overleaf.com/project/6aeec6503ea7a24e3d93a6a5 – viết báo cáo LaTeX

## Quy trình làm 1 feature
1. **Slack** – đề xuất & bàn bạc feature trong `#doancuoiki`.
2. **Trello** – tạo card ở cột *To Do*, gán người làm, đặt deadline. Khi bắt đầu làm thì kéo sang *Doing*.
3. **GitHub** – tạo nhánh riêng từ `main`:
   ```bash
   git checkout main && git pull
   git checkout -b feature/<ten-feature>
   # code...
   git add . && git commit -m "feat: <mo ta ngan>"
   git push -u origin feature/<ten-feature>
   ```
   Mở Pull Request vào `main`, dán link card Trello vào mô tả PR. Cần ít nhất 1 bạn review rồi mới merge.
4. **Trello** – merge xong thì kéo card sang *Done* (đính kèm link PR/commit vào card).
5. **Slack** – bot GitHub và bot Trello tự gửi thông báo vào `#doancuoiki` khi có push / PR / card chuyển sang *Done*.
6. **Overleaf** – người làm feature viết phần mô tả logic kỹ thuật của feature đó vào báo cáo.

## Quy ước
- Không push thẳng lên `main`; mọi thay đổi đi qua Pull Request.
- Tên nhánh: `feature/...`, `fix/...`, `docs/...`.
- Commit message: `feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`.
