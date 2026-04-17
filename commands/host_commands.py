from __future__ import annotations

import io
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from enums import GameState
from enums import WerewolfPhase
from games.werewolf_game import WerewolfGame

if TYPE_CHECKING:
    from bot import MinigameBot


class HostCommands(commands.Cog):
    def __init__(self, bot: MinigameBot):
        self.bot = bot

    @staticmethod
    async def _send_private_messages(bot: MinigameBot, messages: dict[int, list[str]]):
        for user_id, lines in messages.items():
            try:
                user = await bot.fetch_user(user_id)
                await user.send("\n".join(lines))
            except discord.Forbidden:
                continue

    def _current_game(self) -> Optional[WerewolfGame]:
        game = self.bot.current_game
        if isinstance(game, WerewolfGame):
            return game
        return None

    @app_commands.command(name="host", description="Khởi tạo game Ma Sói")
    async def host(self, interaction: discord.Interaction):
        if self.bot.current_game and self.bot.current_game.state not in (
            GameState.IDLE,
            GameState.ENDED,
        ):
            await interaction.response.send_message("❌ Đang có game khác diễn ra!", ephemeral=True)
            return

        game = WerewolfGame(host_id=interaction.user.id)
        self.bot.current_game = game
        self.bot.current_game_type = None

        embed = discord.Embed(
            title="🐺 Ma Sói Hoster",
            description=f"Host: {interaction.user.mention}",
            color=discord.Color.green(),
        )
        embed.add_field(name="Trạng thái", value="Đang mở đăng ký", inline=False)
        embed.add_field(name="Lệnh tiếp theo", value="`/joingame` để tham gia", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="endregister", description="Đóng đăng ký game")
    async def end_register(self, interaction: discord.Interaction):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra!", ephemeral=True)
            return
        if interaction.user.id != game.host_id:
            await interaction.response.send_message("❌ Chỉ host mới dùng được lệnh này!", ephemeral=True)
            return

        ok, message = game.close_registration()
        if not ok:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return

        await interaction.response.send_message(
            f"🔒 Đã đóng đăng ký với **{len(game.players)}** người chơi. Dùng `/settinggame` để chỉnh game."
        )

    @app_commands.command(name="settinggame", description="Chỉnh thông số game")
    @app_commands.describe(
        so_soi="Số sói",
        so_dan="Số dân",
        so_trung_lap="Số role trung lập",
        roles_bat_buoc="CSV role: bao_ve,ke_hap_hoi,tien_tri,canh_sat_truong,soi_gian_diep",
    )
    async def setting_game(
        self,
        interaction: discord.Interaction,
        so_soi: Optional[int] = None,
        so_dan: Optional[int] = None,
        so_trung_lap: Optional[int] = None,
        roles_bat_buoc: Optional[str] = None,
    ):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra!", ephemeral=True)
            return
        if interaction.user.id != game.host_id:
            await interaction.response.send_message("❌ Chỉ host mới dùng được lệnh này!", ephemeral=True)
            return
        if game.phase != WerewolfPhase.SETTING:
            await interaction.response.send_message("❌ Chỉ chỉnh settings sau khi đóng đăng ký.", ephemeral=True)
            return

        updates = {
            "so_soi": so_soi,
            "so_dan": so_dan,
            "so_trung_lap": so_trung_lap,
        }
        ok, message = game.update_settings(**updates)
        if not ok:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return

        if roles_bat_buoc is not None:
            role_names = [x.strip() for x in roles_bat_buoc.split(",") if x.strip()]
            ok, message = game.set_required_roles(role_names)
            if not ok:
                await interaction.response.send_message(f"❌ {message}", ephemeral=True)
                return

        settings = game.settings
        required = ", ".join([r.value for r in settings["roles_bat_buoc"]]) or "(không có)"
        embed = discord.Embed(title="⚙️ Settings Ma Sói", color=discord.Color.blurple())
        embed.add_field(name="Số sói", value=str(settings["so_soi"]))
        embed.add_field(name="Số dân", value=str(settings["so_dan"]))
        embed.add_field(name="Số trung lập", value=str(settings["so_trung_lap"]))
        embed.add_field(name="Role bắt buộc", value=required, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setnotifchannel", description="Set kênh thông báo")
    async def set_notif_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra!", ephemeral=True)
            return
        if interaction.user.id != game.host_id:
            await interaction.response.send_message("❌ Chỉ host mới dùng được lệnh này!", ephemeral=True)
            return

        game.notif_channel_id = channel.id
        game.log_event(f"Set notif channel: {channel.id}")
        await interaction.response.send_message(f"✅ Kênh thông báo: {channel.mention}")

    @app_commands.command(name="setgamechannel", description="Set kênh chơi game")
    async def set_game_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra!", ephemeral=True)
            return
        if interaction.user.id != game.host_id:
            await interaction.response.send_message("❌ Chỉ host mới dùng được lệnh này!", ephemeral=True)
            return

        game.game_channel_id = channel.id
        game.log_event(f"Set game channel: {channel.id}")
        await interaction.response.send_message(f"✅ Kênh chơi game: {channel.mention}")

    @app_commands.command(name="startgame", description="Bắt đầu game Ma Sói")
    async def start_game(self, interaction: discord.Interaction):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra!", ephemeral=True)
            return
        if interaction.user.id != game.host_id:
            await interaction.response.send_message("❌ Chỉ host mới dùng được lệnh này!", ephemeral=True)
            return
        if game.phase != WerewolfPhase.SETTING:
            await interaction.response.send_message("❌ Cần đóng đăng ký trước khi bắt đầu.", ephemeral=True)
            return
        if game.notif_channel_id is None:
            await interaction.response.send_message("❌ Cần set notification channel trước.", ephemeral=True)
            return

        await game.on_game_start()
        channel = self.bot.get_channel(game.notif_channel_id)
        if channel:
            await channel.send("🌞 Game bắt đầu ở **ngày 0**.")
        await interaction.response.send_message("✅ Đã bắt đầu game Ma Sói.")

    @app_commands.command(name="endday", description="Kết thúc ban ngày")
    async def end_day(self, interaction: discord.Interaction):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra!", ephemeral=True)
            return
        if interaction.user.id != game.host_id:
            await interaction.response.send_message("❌ Chỉ host mới dùng được lệnh này!", ephemeral=True)
            return

        result = game.end_day()
        if not result.get("ok"):
            await interaction.response.send_message(f"❌ {result.get('message')}", ephemeral=True)
            return

        day_private: dict[int, list[str]] = {k: [v] for k, v in result["spy_messages"].items()}
        for uid, lines in result.get("villager_messages", {}).items():
            day_private.setdefault(uid, []).extend(lines)
        if day_private:
            await self._send_private_messages(self.bot, day_private)
        winner = result.get("winner")
        if winner:
            await interaction.response.send_message(f"🏁 Game kết thúc. Phe thắng: **{winner}**")
            return

        executed = result.get("executed")
        if executed is None:
            await interaction.response.send_message("🌙 Kết thúc ngày: không ai bị treo cổ, chuyển sang ban đêm.")
        else:
            await interaction.response.send_message(
                f"🌙 Kết thúc ngày: người chơi **{executed}** bị treo cổ, chuyển sang ban đêm."
            )

    @app_commands.command(name="endnight", description="Kết thúc ban đêm")
    async def end_night(self, interaction: discord.Interaction):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra!", ephemeral=True)
            return
        if interaction.user.id != game.host_id:
            await interaction.response.send_message("❌ Chỉ host mới dùng được lệnh này!", ephemeral=True)
            return

        result = game.end_night()
        if not result.get("ok"):
            await interaction.response.send_message(f"❌ {result.get('message')}", ephemeral=True)
            return

        await self._send_private_messages(self.bot, result["private_messages"])
        winner = result.get("winner")
        if winner:
            await interaction.response.send_message(f"🏁 Game kết thúc. Phe thắng: **{winner}**")
            return

        deaths = result.get("deaths", [])
        if deaths:
            await interaction.response.send_message(
                f"🌞 Ban ngày bắt đầu. Người chết trong đêm: {', '.join(str(x) for x in deaths)}."
            )
        else:
            await interaction.response.send_message("🌞 Ban ngày bắt đầu. Đêm qua không ai chết.")

    @app_commands.command(name="endgame", description="Kết thúc game")
    async def end_game(self, interaction: discord.Interaction):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra!", ephemeral=True)
            return
        if interaction.user.id != game.host_id:
            await interaction.response.send_message("❌ Chỉ host mới dùng được lệnh này!", ephemeral=True)
            return

        await game.on_game_end()
        self.bot.current_game = None
        self.bot.current_game_type = None
        await interaction.response.send_message("🛑 Đã kết thúc và reset game.")

    @app_commands.command(name="log", description="Gửi log game qua DM")
    async def log_command(self, interaction: discord.Interaction):
        game = self._current_game()
        if not game:
            await interaction.response.send_message("❌ Không có game Ma Sói nào đang diễn ra!", ephemeral=True)
            return
        if interaction.user.id != game.host_id:
            await interaction.response.send_message("❌ Chỉ host mới dùng được lệnh này!", ephemeral=True)
            return

        content = "\n".join(game.event_log) or "(trống)"
        file = discord.File(io.BytesIO(content.encode("utf-8")), filename="log.txt")
        try:
            dm = await interaction.user.create_dm()
            await dm.send("📝 Log game:", file=file)
            await interaction.response.send_message("✅ Đã gửi log qua DM.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Không thể gửi DM cho bạn.", ephemeral=True)


async def setup(bot: MinigameBot):
    await bot.add_cog(HostCommands(bot))
