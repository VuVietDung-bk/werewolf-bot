# 🐺 Ma Sói Hoster

Bot Discord quản trò Ma Sói theo luồng trong `design.md`.

## Tính năng chính

- Luồng host: `/host` → `/endregister` → `/settinggame` → `/startgame`
- Điều khiển vòng chơi: `/endday`, `/endnight`, `/endgame`
- Kênh cấu hình: `/setnotifchannel`, `/setgamechannel`
- Người chơi: `/joingame`, `/leavegame`, `/vote`, `/castskill`
- Kênh sói: `/chatsoi`, `/readsoi`, `/votesoi`
- Log game qua DM: `/log`

## Role đã triển khai

- `bao_ve`
- `ke_hap_hoi`
- `tien_tri`
- `canh_sat_truong`
- `soi_gian_diep`
- role nền: `dan_lang`, `soi_thuong`

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
- `castskill` hiện xử lý theo role ban đêm.
