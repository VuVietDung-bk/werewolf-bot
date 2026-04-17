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

    @app_commands.command(name="help", description="Hiển thị hướng dẫn")
    @app_commands.describe(role="Xem mô tả role cụ thể")
    async def help_command(self, interaction: discord.Interaction, role: Optional[str] = None):
        game = self._current_game()
        role_defs = WerewolfGame.ROLE_DEFINITIONS

        if role:
            role_key = role.strip().lower()
            role_obj = None
            for role_type in RoleType:
                if role_type.value == role_key:
                    role_obj = role_type
                    break
            if role_obj is None:
                await interaction.response.send_message("❌ Role không hợp lệ.", ephemeral=True)
                return

            role_def = role_defs[role_obj]
            embed = discord.Embed(
                title=f"📘 {role_obj.value}",
                description=self._build_role_help(role_def),
                color=discord.Color.blue(),
            )
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
                "`/chatsoi`, `/readsoi`, `/votesoi`"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roles", description="Danh sách role hiện tại")
    @app_commands.describe(page="Trang (mỗi trang 6 role)")
    async def roles(self, interaction: discord.Interaction, page: int = 1):
        roles = list(WerewolfGame.ROLE_DEFINITIONS.values())
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
    @app_commands.describe(target="Mục tiêu của kỹ năng")
    async def cast_skill(self, interaction: discord.Interaction, target: discord.Member):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra.", ephemeral=True)
            return

        ok, message, private_lines = game.cast_skill(interaction.user.id, [target.id])
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


async def setup(bot: MinigameBot):
    await bot.add_cog(UserCommands(bot))

