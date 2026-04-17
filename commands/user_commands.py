from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from enums import RoleType, Side, WerewolfPhase
from games.werewolf_game import RoleDefinition, WerewolfGame

if TYPE_CHECKING:
    from bot import MinigameBot


def _in_game_channel(bot: MinigameBot, interaction: discord.Interaction) -> bool:
    game = bot.current_game
    if not isinstance(game, WerewolfGame):
        return True
    if game.game_channel_id is None:
        return True
    return interaction.channel_id == game.game_channel_id


class UserCommands(commands.Cog):
    def __init__(self, bot: MinigameBot):
        self.bot = bot

    def _current_game(self) -> Optional[WerewolfGame]:
        game = self.bot.current_game
        if isinstance(game, WerewolfGame):
            return game
        return None

    @staticmethod
    def _build_role_help(role_def: RoleDefinition) -> str:
        side_name = {
            Side.DAN: "Dân",
            Side.SOI: "Sói",
            Side.TRUNG_LAP: "Trung lập",
        }[role_def.side]
        return f"**Phe:** {side_name}\n{role_def.description}"

    @staticmethod
    def _parse_role_input(raw_role: str) -> Optional[RoleType]:
        normalized = raw_role.strip().lower()
        if not normalized:
            return None

        compact = normalized.replace("-", "_").replace(" ", "_")
        candidates = [normalized, compact]

        if compact.startswith("roletype."):
            candidates.append(compact.split(".", 1)[1])
        if normalized.startswith("roletype."):
            candidates.append(normalized.split(".", 1)[1].replace("-", "_").replace(" ", "_"))

        for candidate in candidates:
            try:
                return RoleType(candidate)
            except ValueError:
                pass
            for role_type in RoleType:
                if role_type.name.lower() == candidate:
                    return role_type
        return None

    @app_commands.command(name="help", description="Hiển thị hướng dẫn")
    @app_commands.describe(role="Xem mô tả role cụ thể", dms="Gửi hướng dẫn qua DM thay vì hiện ở kênh")
    async def help_command(
        self,
        interaction: discord.Interaction,
        role: Optional[str] = None,
        dms: bool = False,
    ):
        game = self._current_game()
        role_defs = WerewolfGame._load_role_definitions()

        if role:
            role_obj = self._parse_role_input(role)
            if role_obj is None:
                await interaction.response.send_message("❌ Role không hợp lệ.", ephemeral=True)
                return

            role_def = role_defs.get(role_obj)
            if role_def is None:
                await interaction.response.send_message("❌ Chưa tải được dữ liệu role.", ephemeral=True)
                return
            embed = discord.Embed(
                title=f"📘 {role_obj.value}",
                description=self._build_role_help(role_def),
                color=discord.Color.blue(),
            )
            if dms:
                try:
                    dm = await interaction.user.create_dm()
                    await dm.send(embed=embed)
                    await interaction.response.send_message("📩 Đã gửi hướng dẫn role qua DM.", ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("❌ Không thể gửi DM. Hãy mở DM với bot.", ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed)
            return

        phase_text = game.phase.value if game else "chưa có game"
        embed = discord.Embed(
            title="📖 Hướng dẫn Ma Sói Hoster",
            description=f"Trạng thái hiện tại: **{phase_text}**",
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Lệnh Host",
            value=(
                "`/host`, `/endregister`, `/settinggame`, `/startgame`, `/endday`, "
                "`/endnight`, `/endgame`, `/log`, `/setnotifchannel`, `/setgamechannel`"
            ),
            inline=False,
        )
        embed.add_field(
            name="Lệnh Người chơi",
            value=(
                "`/joingame`, `/leavegame`, `/roles`, `/vote`, `/castskill`, "
                "`/chatsoi`, `/readsoi`, `/votesoi`, `/passbomb`, `/detectivevote`, "
                "`/specialkill`, `/revealshield`, `/transfercoins`, `/daychat`"
            ),
            inline=False,
        )
        if dms:
            try:
                dm = await interaction.user.create_dm()
                await dm.send(embed=embed)
                await interaction.response.send_message("📩 Đã gửi hướng dẫn tổng quan qua DM.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Không thể gửi DM. Hãy mở DM với bot.", ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roles", description="Danh sách role hiện tại")
    @app_commands.describe(page="Trang (mỗi trang 6 role)")
    async def roles(self, interaction: discord.Interaction, page: int = 1):
        roles = list(WerewolfGame._load_role_definitions().values())
        order = {Side.DAN: 0, Side.SOI: 1, Side.TRUNG_LAP: 2}
        roles.sort(key=lambda r: (order[r.side], r.role.value))

        page_size = 6
        total_pages = max(1, (len(roles) + page_size - 1) // page_size)
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        chunk = roles[start : start + page_size]

        embed = discord.Embed(
            title=f"🎭 Danh sách role (trang {page}/{total_pages})",
            color=discord.Color.purple(),
        )
        for role in chunk:
            side_text = {
                Side.DAN: "Dân",
                Side.SOI: "Sói",
                Side.TRUNG_LAP: "Trung lập",
            }[role.side]
            embed.add_field(
                name=role.role.value,
                value=f"Phe: {side_text}",
                inline=True,
            )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="joingame", description="Tham gia game")
    async def join_game(self, interaction: discord.Interaction):
        if not _in_game_channel(self.bot, interaction):
            await interaction.response.send_message("❌ Lệnh này chỉ được dùng trong game channel.", ephemeral=True)
            return

        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang mở.", ephemeral=True)
            return

        ok, message = game.register_player(interaction.user.id)
        if not ok:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return

        await interaction.response.send_message(
            f"✅ {interaction.user.mention} đã tham gia game ({len(game.players)} người)."
        )

    @app_commands.command(name="leavegame", description="Rời game")
    async def leave_game(self, interaction: discord.Interaction):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang mở.", ephemeral=True)
            return

        ok, message = game.unregister_player(interaction.user.id)
        if not ok:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return

        await interaction.response.send_message(f"👋 {interaction.user.mention} đã rời game.")

    @app_commands.command(name="vote", description="Vote treo cổ một người hoặc skip")
    @app_commands.describe(target="Mục tiêu vote", skip="Vote bỏ qua")
    async def vote(self, interaction: discord.Interaction, target: Optional[discord.Member] = None, skip: bool = False):
        if not _in_game_channel(self.bot, interaction):
            await interaction.response.send_message("❌ Lệnh này chỉ được dùng trong game channel.", ephemeral=True)
            return

        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra.", ephemeral=True)
            return
        if game.phase != WerewolfPhase.DAY:
            await interaction.response.send_message("❌ Chỉ được vote ở ban ngày.", ephemeral=True)
            return
        if skip and target is not None:
            await interaction.response.send_message("❌ Chỉ chọn target hoặc skip, không chọn cả hai.", ephemeral=True)
            return

        target_id = None if skip or target is None else target.id
        ok, message = game.vote_day(interaction.user.id, target_id)
        if not ok:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return

        vote_label = "SKIP" if target_id is None else f"{target.mention}"
        await interaction.response.send_message(f"🗳️ Đã vote: **{vote_label}**")

    @app_commands.command(name="castskill", description="Dùng kỹ năng role")
    @app_commands.describe(
        target="Mục tiêu 1 (nếu skill cần)",
        target2="Mục tiêu 2 (nếu skill cần)",
        target3="Mục tiêu 3 (nếu skill cần)",
        skill_name="Tên skill cụ thể (nếu role có nhiều skill)",
    )
    async def cast_skill(
        self,
        interaction: discord.Interaction,
        target: Optional[discord.Member] = None,
        target2: Optional[discord.Member] = None,
        target3: Optional[discord.Member] = None,
        skill_name: Optional[str] = None,
    ):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra.", ephemeral=True)
            return

        targets = []
        if target:
            targets.append(target.id)
        if target2:
            targets.append(target2.id)
        if target3:
            targets.append(target3.id)
        ok, message, private_lines = game.cast_skill(interaction.user.id, targets, skill_name=skill_name)
        if not ok:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return

        if private_lines:
            try:
                dm = await interaction.user.create_dm()
                await dm.send("\n".join(private_lines))
            except discord.Forbidden:
                pass

        await interaction.response.send_message(f"✅ {message}", ephemeral=True)

    @app_commands.command(name="chatsoi", description="Chat riêng cho phe sói")
    async def chat_soi(self, interaction: discord.Interaction, message: str):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra.", ephemeral=True)
            return

        ok, result = game.add_wolf_chat(interaction.user.id, message)
        if not ok:
            await interaction.response.send_message(f"❌ {result}", ephemeral=True)
            return

        await interaction.response.send_message("✅ Đã gửi chat sói.", ephemeral=True)

    @app_commands.command(name="readsoi", description="Đọc chat sói")
    async def read_soi(self, interaction: discord.Interaction, page: int = 1):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra.", ephemeral=True)
            return

        player = game.players.get(interaction.user.id)
        if not player or not player.is_alive or game.side_of(interaction.user.id) != Side.SOI:
            await interaction.response.send_message("❌ Chỉ sói còn sống mới đọc được chat sói.", ephemeral=True)
            return

        lines, total_pages = game.read_wolf_chat(page=page)
        content = "\n".join(lines) if lines else "(chưa có tin nhắn)"
        await interaction.response.send_message(
            f"📜 Chat sói (trang {max(1, min(page, total_pages))}/{total_pages})\n{content}",
            ephemeral=True,
        )

    @app_commands.command(name="votesoi", description="Vote giết người vào ban đêm")
    async def vote_soi(self, interaction: discord.Interaction, target: discord.Member):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra.", ephemeral=True)
            return

        ok, message = game.vote_wolf(interaction.user.id, target.id)
        if not ok:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return

        await interaction.response.send_message(f"✅ Đã vote sói: {target.mention}", ephemeral=True)

    @app_commands.command(name="passbomb", description="(Người Cầm Bom) Trao bom cho người khác")
    async def pass_bomb(self, interaction: discord.Interaction, target: discord.Member):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra.", ephemeral=True)
            return
        ok, message = game.pass_bomb(interaction.user.id, target.id)
        if not ok:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        await interaction.response.send_message(f"💣 {message}", ephemeral=True)

    @app_commands.command(name="detectivevote", description="(Thám tử tư) Dùng xu để cộng thêm phiếu")
    async def detective_vote(self, interaction: discord.Interaction, target: discord.Member):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra.", ephemeral=True)
            return
        ok, message = game.detective_coin_vote(interaction.user.id, target.id)
        if not ok:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        await interaction.response.send_message(f"🪙 {message}", ephemeral=True)

    @app_commands.command(
        name="specialkill",
        description="(Kẻ Phóng Hỏa/Kẻ Đánh Bạc/Kẻ Nối Hồn) Lệnh giết dùng chung",
    )
    async def special_kill(self, interaction: discord.Interaction, target: discord.Member):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra.", ephemeral=True)
            return
        ok, message = game.special_role_kill(interaction.user.id, target.id)
        if not ok:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        await interaction.response.send_message(f"🗡️ {message}", ephemeral=True)

    @app_commands.command(name="revealshield", description="(Sói Có Khiên) Công khai khiên để miễn nhiễm vote")
    async def reveal_shield(self, interaction: discord.Interaction):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra.", ephemeral=True)
            return
        ok, message = game.reveal_wolf_shield(interaction.user.id)
        if not ok:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        await interaction.response.send_message(f"🛡️ {message}", ephemeral=True)

    @app_commands.command(name="transfercoins", description="(Role có xu) Chuyển xu cho người chơi khác")
    @app_commands.describe(target="Người nhận xu", amount="Số xu muốn chuyển")
    async def transfer_coins(self, interaction: discord.Interaction, target: discord.Member, amount: int):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra.", ephemeral=True)
            return
        ok, message = game.transfer_coins(interaction.user.id, target.id, amount)
        if not ok:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        await interaction.response.send_message(f"🪙 {message}", ephemeral=True)

    @app_commands.command(name="daychat", description="Chat công khai ban ngày (ghi nhận cho role liên quan)")
    @app_commands.describe(message="Nội dung chat")
    async def day_chat(self, interaction: discord.Interaction, message: str):
        if not _in_game_channel(self.bot, interaction):
            await interaction.response.send_message("❌ Lệnh này chỉ được dùng trong game channel.", ephemeral=True)
            return
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra.", ephemeral=True)
            return
        if game.phase != WerewolfPhase.DAY:
            await interaction.response.send_message("❌ Chỉ được chat bằng lệnh này vào ban ngày.", ephemeral=True)
            return
        player = game.players.get(interaction.user.id)
        if not player or not player.is_alive:
            await interaction.response.send_message("❌ Bạn không thể chat lúc này.", ephemeral=True)
            return
        if player.role == RoleType.KE_TAM_LY_YEU:
            await interaction.response.send_message("❌ Kẻ Tâm Lý Yếu không thể chat ban ngày.", ephemeral=True)
            return

        game.mark_day_chat(interaction.user.id)
        await interaction.response.send_message(f"💬 {interaction.user.mention}: {message}")


async def setup(bot: MinigameBot):
    await bot.add_cog(UserCommands(bot))
