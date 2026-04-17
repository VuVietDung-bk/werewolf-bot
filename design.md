Tên bot: Ma Sói Hoster
Features:
Nên nhớ đây chỉ là các lệnh được gọi, còn những hàm backend thì phải tự xử lý
Host
- /host - Khởi tạo game, trả về thông báo thất bại nếu đang có game khác diễn ra. Người gọi lệnh này được nhận là host và không thay đổi cho đến khi game kết thúc.
- /endRegister - Đóng đăng ký game hiện tại. Chỉ người mang quyền host được gọi lệnh.
- /settingGame - Chỉnh thông số game sau khi gọi lệnh /host. Chỉ người mang quyền host được gọi lệnh này, không thì trả về thông báo thất bại. Hiển thị một danh sách các thông số để host chỉnh. Chỉ được gọi sau khi đóng đăng ký.
- /startGame - Bắt đầu game ngay. Trả về lỗi nếu chưa đóng đăng ký hoặc người gọi không phải host.
- /endGame - Kết thúc game, có thể gọi bất cứ lúc nào. Nên nhớ ngay cả khi game thật sự kết thúc vẫn phải gọi lệnh này để reset, để cho người chơi một khoảng thời gian xem trạng thái trước khi reset. Sau khi gọi lệnh này reset vai trò host.
- /log - Log các event tương tác giữa các người chơi hoặc meta event trong game. Chỉ host được gọi. Gửi file log.txt qua DM cho host.
- /setNotifChannel (channel: channel) - Cài đặt kênh để bot thông báo vào những mốc thời gian quan trọng của minigame. Buộc phải setting trước khi bắt đầu game. Chỉ host có quyền gọi lệnh này.
- /setGameChannel (channel: channel) - Cài đặt kênh mà các người chơi dùng để chơi game. Lệnh của bot chỉ được phép gọi trong kênh này. Nếu không setting thì người chơi gọi lệnh của bot ở đâu cũng được. Chỉ host có quyền gọi lệnh này.
/endDay: Kết thúc ngày hiện tại. Game default bắt đầu vào ngày 0.
/endNight: Kết thúc đêm hiện tại. Sau ngày 0 là đêm 1.
# Non-host user
- /help - Hiển thị hướng dẫn sử dụng cơ bản.
- /help (role: ROLETYPE enum) - Hiển thị cơ chế role.
- /roles: hiển thị danh sách các role hiện tại và mã enum của chúng. Phân trang. Sắp xếp Dân -> Sói -> Trung lập.
- /joinGame - Tham gia game hiện tại nếu vẫn đang mở đăng ký. Host không được tham gia.
- /leaveGame - Rời game nếu đã đăng ký và game chưa bắt đầu.
- /vote (user: user hoặc SKIP) - vote công khai một người hoặc bỏ qua. Ai cũng sẽ thấy được vote của người chơi, trừ những ngày bị hiệu ứng vote ẩn danh. Chỉ được gọi vào phase ban ngày.
- /castSkill (users: user[]) - dùng skill lên một danh sách người chơi. Phải điền vào đúng số người chơi để dùng. Nếu không thể dùng skill thì không được phép dùng.
- /chatSoi - gửi chat vào chat riêng của những con sói. Chỉ sói được dùng lệnh này. Sói chết rồi thì không được dùng.
- /readSoi - đọc chat riêng tư của sói. Hiển thị phân trang, tối đa 10 trang. Sói chết rồi thì không được dùng.
/voteSoi - vote người để giết ban đêm. Vote sẽ chốt khi toàn bộ sói còn sống vote một người
# Luồng trò chơi
- Quản trò setting game. Các setting: Số sói, số dân, số trung lập, các role bắt buộc xuất hiện (dạng danh sách, không được nhiều hơn số người chơi)
- Ban đêm, các role đặc biệt gọi lệnh và sói chốt người giết, sau khi xong hết thì báo quản trò để kết thúc ban đêm.
- Ban ngày, các role đặc biệt có thể gọi lệnh, và người chơi vote. Khi vote xong hết thì báo quản trò để kết thúc ban ngày. Nếu hòa hoặc Skip là đa số thì không ai bị treo cổ.
- Khi điều kiện chiến thắng của phe nào được đáp ứng, phe đó được báo chiến thắng. Game kết thúc, và log được gửi qua DMs của quản trò.
# Thiết kế hệ thống trạng thái người chơi, role và game:
- Người chơi: ROLETYPE role (enum); int livesLeft; bool isAlive; Effect[] effectCasted (những hiệu ứng đang bị dính); user voted (người mà người chơi này vote); int voteCount (số vote người này nhận được).
struct Effect {
   string name;
   int duration;
   int priority;
   function apply();
}
- Role: ROLETYPE role (enum); SIDE side (enum); int numberOfSkillCast (số người ảnh hưởng trong skill); int priority (độ ưu tiên trong đêm); bool canTargetSelf; int cooldown; string description; function onDie(){}; function onVoted(){}; function onSkill(user[]){}; function onNightStart(){}; function onDayStart(){}; 
- Game: GamePhase {WAITING, SETTING, NIGHT, DAY, ENDED}, checkWinCondition(): chạy sau mỗi lệnh skill của người chơi, và sau mỗi lần chuyển ngày đêm.
