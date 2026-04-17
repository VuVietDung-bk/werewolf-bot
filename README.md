# 🐺 Ma Sói Hoster

Bot Discord quản trò Ma Sói theo luồng trong `design.md`.

## Tính năng chính

- Luồng host: `/host` → `/endregister` → `/settinggame` → `/startgame`
- Điều khiển vòng chơi: `/endday`, `/endnight`, `/endgame`
- Kênh cấu hình: `/setnotifchannel`, `/setgamechannel`
- Người chơi: `/joingame`, `/leavegame`, `/vote`, `/castskill`
- Lệnh role riêng theo roles.md: `/passbomb`, `/detectivevote`, `/specialkill`, `/revealshield`
- Kênh sói: `/chatsoi`, `/readsoi`, `/votesoi`
- Log game qua DM: `/log`

## Role đã triển khai

- Đã định nghĩa tường minh **toàn bộ role trong `roles.md`** dưới dạng class riêng.
- Engine gọi trực tiếp lifecycle của role: `onDie`, `onVoted`, `onSkill`, `onNightStart`, `onDayStart`.

## Cài đặt

1. Cài dependencies:
```bash
pip install -r requirements.txt
```

2. Cấu hình `.env`:
```bash
DISCORD_BOT_TOKEN=your_token_here
```

3. Chạy bot:
```bash
python3 main.py
```

## Ghi chú

- Game bắt đầu ở **ngày 0**.
- Chỉ host mới có quyền đóng/mở phase.
- `castskill` hỗ trợ `skill_name` và nhiều mục tiêu (tùy skill của từng role).
