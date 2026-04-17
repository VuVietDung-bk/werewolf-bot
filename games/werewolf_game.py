from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from enums import GameState, RoleType, Side, WerewolfPhase
from games.base_game import BaseGame
from games.role_specs import ROLE_SPECS, RoleSpec


@dataclass
class Effect:
    name: str
    duration: int
    priority: int


@dataclass
class RoleDefinition:
    role: RoleType
    side: Side
    number_of_skill_cast: int
    priority: int
    can_target_self: bool
    cooldown: int
    description: str
    kill_capable: bool = False
    info_capable: bool = False
    vote_capable: bool = False
    protect_capable: bool = False
    skill_phase: str = "night"


@dataclass
class PlayerState:
    user_id: int
    role: Optional[RoleType] = None
    lives_left: int = 1
    is_alive: bool = True
    effects_casted: List[Effect] = field(default_factory=list)
    voted: Optional[int] = None
    vote_count: int = 0
    pending_death_day: Optional[int] = None
    last_attacker: Optional[int] = None
    cooldowns: Dict[str, object] = field(default_factory=dict)


class WerewolfGame(BaseGame):
    ROLE_DEFINITIONS: Dict[RoleType, RoleDefinition] = {}

    @classmethod
    def _load_role_definitions(cls) -> Dict[RoleType, RoleDefinition]:
        if cls.ROLE_DEFINITIONS:
            return cls.ROLE_DEFINITIONS

        role_defs: Dict[RoleType, RoleDefinition] = {}
        for role, spec in ROLE_SPECS.items():
            effects = [effect for skill in spec.skills for effect in skill.effects]
            number_of_skill_cast = max(
                (skill.max_targets or skill.target_count for skill in spec.skills),
                default=0,
            )
            role_defs[role] = RoleDefinition(
                role=role,
                side=spec.side,
                number_of_skill_cast=number_of_skill_cast,
                priority=spec.priority,
                can_target_self=spec.can_target_self,
                cooldown=spec.cooldown,
                description=spec.description,
                kill_capable="kill_target" in effects,
                info_capable=any(x in effects for x in ("info_role", "info_side", "compare_side")),
                vote_capable="vote_bonus" in effects,
                protect_capable="protect_target" in effects,
                skill_phase=spec.skills[0].phase if spec.skills else "night",
            )

        cls.ROLE_DEFINITIONS = role_defs
        return cls.ROLE_DEFINITIONS

    def __init__(self, host_id: int):
        super().__init__(host_id)
        self._load_role_definitions()
        self.state = GameState.REGISTERING
        self.phase = WerewolfPhase.WAITING
        self.players: Dict[int, PlayerState] = {}
        self.settings = {
            "so_soi": 2,
            "so_dan": 6,
            "so_trung_lap": 0,
            "roles_bat_buoc": [],
        }
        self.day_number = 0
        self.night_number = 0
        self.wolf_votes: Dict[int, int] = {}
        self.day_votes: Dict[int, Optional[int]] = {}
        self.day_vote_order: List[int] = []
        self.night_skills: Dict[int, List[int]] = {}
        self.pending_night_kills: Dict[int, int] = {}
        self.vote_bonus: Dict[int, int] = {}
        self.next_day_vote_bonus: Dict[int, int] = {}
        self.day_vote_immune_targets: set[int] = set()
        self.vote_locked_players: set[int] = set()
        self.jailed_players_today: set[int] = set()
        self.jailed_players_next_day: set[int] = set()
        self.night_blocked_players: set[int] = set()
        self.wolf_barrier_active: bool = False
        self.wolf_bite_block_nights: int = 0
        self.wolf_curse_targets: set[int] = set()
        self.stolen_identity_targets: Dict[int, int] = {}
        self.pending_villager_announcements: List[str] = []
        self.night_wake_watch: Dict[int, int] = {}
        self.night_killer_watch: Dict[int, tuple[int, int]] = {}
        self.prev_day_voted_targets: set[int] = set()
        self.ke_bao_thu_partner: Dict[int, int] = {}
        self.ke_bao_thu_revenge_ready: set[int] = set()
        self.ke_da_nghi_marks: Dict[int, List[int]] = {}
        self.ke_da_nghi_opt_out: set[int] = set()
        self.ke_tham_do_last_target: Dict[int, int] = {}
        self.ke_ke_thua_partner: Dict[int, int] = {}
        self.yandere_target: Dict[int, int] = {}
        self.nguoi_gay_partner: Dict[int, int] = {}
        self.nguoi_gay_last_target: Dict[int, int] = {}
        self.tham_phan_targets: Dict[int, int] = {}
        self.chan_don_redirect: Dict[int, int] = {}
        self.chan_don_tank_wolf: Optional[int] = None
        self.soi_dat_bay_targets: set[int] = set()
        self.soi_dat_bay_last_target: Dict[int, int] = {}
        self.soi_hac_am_target: Optional[int] = None
        self.soi_hac_am_hide_votes: bool = False
        self.soi_goku_pierce_attackers: set[int] = set()
        self.wolf_extra_kill_charges: int = 0
        self.day_skip_forced: bool = False
        self.ke_dat_bom_placements: Dict[int, int] = {}
        self.phong_hoa_doused: set[int] = set()
        self.phong_hoa_burn_targets: set[int] = set()
        self.lolicon_enraged: set[int] = set()
        self.con_qua_marked_target: Dict[int, int] = {}
        self.con_qua_kill_ready: set[int] = set()
        self.electricity_off: bool = False
        self.ke_tang_hinh_day_chatters: set[int] = set()
        self.ke_tang_hinh_day_killed: set[int] = set()
        self.tim_su_that_correct_targets: Dict[int, set[int]] = {}
        self.ke_nghien_co_bac_bets: Dict[int, tuple[int, set[int], int]] = {}
        self.ke_danh_bac_predictions: Dict[int, tuple[int, int]] = {}
        self.daily_coin_spent_by_others: int = 0
        self.daily_villager_coin_income: int = 0
        self.latest_dead_player_id: Optional[int] = None
        self.latest_dead_role: Optional[RoleType] = None
        self.bomb_holder_id: Optional[int] = None
        self.bomb_start_night: Optional[int] = None
        self.bomb_passed_this_night: bool = False
        self.detective_coins: Dict[int, int] = {}
        self.wolf_chat_log: List[str] = []
        self.winner: Optional[Side] = None

    @property
    def alive_players(self) -> List[int]:
        return [pid for pid, p in self.players.items() if p.is_alive]

    def side_of(self, user_id: int) -> Optional[Side]:
        player = self.players.get(user_id)
        if not player or not player.role:
            return None
        return self.ROLE_DEFINITIONS.get(player.role, self.ROLE_DEFINITIONS[RoleType.DAN_LANG]).side

    def get_default_settings(self) -> dict:
        return self.settings.copy()

    def validate_settings(self, settings: dict) -> tuple[bool, str]:
        so_soi = int(settings.get("so_soi", self.settings["so_soi"]))
        so_dan = int(settings.get("so_dan", self.settings["so_dan"]))
        so_trung_lap = int(settings.get("so_trung_lap", self.settings["so_trung_lap"]))
        roles_bat_buoc = settings.get("roles_bat_buoc", self.settings["roles_bat_buoc"])
        total_roles = so_soi + so_dan + so_trung_lap

        if so_soi < 1:
            return False, "Số sói phải >= 1."
        if so_dan < 1:
            return False, "Số dân phải >= 1."
        if so_trung_lap < 0:
            return False, "Số trung lập không thể âm."
        if len(roles_bat_buoc) > total_roles:
            return False, "Số role bắt buộc không được lớn hơn tổng số vai trò."
        if len(self.players) > 0 and total_roles > len(self.players):
            return False, "Tổng số vai trò không được lớn hơn số người chơi."
        if len(self.players) > 0 and len(roles_bat_buoc) > len(self.players):
            return False, "Số role bắt buộc không được lớn hơn số người chơi."
        return True, ""

    def register_player(self, user_id: int) -> tuple[bool, str]:
        if self.phase != WerewolfPhase.WAITING:
            return False, "Đã đóng đăng ký."
        if user_id == self.host_id:
            return False, "Host không thể tham gia game."
        if user_id in self.players:
            return False, "Bạn đã tham gia rồi."
        self.players[user_id] = PlayerState(user_id=user_id)
        self.log_event(f"Player {user_id} joined")
        return True, "Tham gia thành công."

    def unregister_player(self, user_id: int) -> tuple[bool, str]:
        if self.phase != WerewolfPhase.WAITING:
            return False, "Không thể rời game khi đã đóng đăng ký."
        if user_id not in self.players:
            return False, "Bạn chưa tham gia game."
        del self.players[user_id]
        self.log_event(f"Player {user_id} left")
        return True, "Rời game thành công."

    def close_registration(self) -> tuple[bool, str]:
        if self.phase != WerewolfPhase.WAITING:
            return False, "Đăng ký đã đóng."
        if len(self.players) < 4:
            return False, "Cần tối thiểu 4 người chơi."
        self.phase = WerewolfPhase.SETTING
        self.state = GameState.REGISTRATION_CLOSED
        self.log_event("Đã đóng đăng ký")
        return True, "Đã đóng đăng ký."

    def update_settings(self, **kwargs) -> tuple[bool, str]:
        merged = self.settings.copy()
        merged.update({k: v for k, v in kwargs.items() if v is not None})
        ok, err = self.validate_settings(merged)
        if not ok:
            return False, err
        self.settings.update(merged)
        self.log_event(f"Cập nhật settings: {self.settings}")
        return True, "Đã cập nhật settings."

    def _parse_role(self, value: str) -> Optional[RoleType]:
        normalized = value.strip().lower()
        try:
            return RoleType(normalized)
        except ValueError:
            return None

    def _split_skill_name(self, value: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        if value is None:
            return None, None
        raw = value.strip()
        if ":" not in raw:
            return raw, None
        name, arg = raw.split(":", 1)
        return name.strip(), arg.strip() or None

    def _any_alive_role(self, role: RoleType) -> bool:
        return any(self.players[pid].is_alive and self.players[pid].role == role for pid in self.players)

    def _effective_coin_cost(self, spender_id: int, base_cost: int) -> int:
        if not self._any_alive_role(RoleType.SOI_TU_BAN):
            return base_cost
        return base_cost * 2

    def _spend_coins(self, spender_id: int, base_cost: int) -> tuple[bool, int]:
        spender = self.players.get(spender_id)
        if not spender:
            return False, 0
        cost = self._effective_coin_cost(spender_id, base_cost)
        current = int(spender.cooldowns.get("coins", 0))
        if current < cost:
            return False, cost
        spender.cooldowns["coins"] = current - cost
        if spender.role != RoleType.SOI_TU_BAN:
            self.daily_coin_spent_by_others += cost
        return True, cost

    def set_required_roles(self, roles: List[str]) -> tuple[bool, str]:
        parsed: List[RoleType] = []
        for role_name in roles:
            role = self._parse_role(role_name)
            if not role:
                return False, f"Role không hợp lệ: {role_name}"
            parsed.append(role)
        self.settings["roles_bat_buoc"] = parsed
        ok, err = self.validate_settings(self.settings)
        if not ok:
            return False, err
        return True, "Đã cập nhật role bắt buộc."

    def _build_role_pool(self) -> List[RoleType]:
        total_players = len(self.players)
        required_roles: List[RoleType] = list(dict.fromkeys(self.settings["roles_bat_buoc"]))
        role_pool = required_roles.copy()

        normal_roles = {RoleType.DAN_LANG, RoleType.SOI_THUONG}

        def count_side(roles: List[RoleType], side: Side) -> int:
            return sum(1 for role in roles if self.ROLE_DEFINITIONS[role].side == side)

        wolves_in_pool = count_side(role_pool, Side.SOI)
        villagers_in_pool = count_side(role_pool, Side.DAN)
        neutral_in_pool = count_side(role_pool, Side.TRUNG_LAP)

        target_wolves = self.settings["so_soi"]
        target_villagers = self.settings["so_dan"]
        target_neutral = self.settings["so_trung_lap"]

        # Ưu tiên rút random các role đặc biệt (không phải dân/sói thường), không lặp.
        # Chỉ bù bằng role thường khi hết role đặc biệt phù hợp.
        for side, target_count in (
            (Side.SOI, target_wolves),
            (Side.DAN, target_villagers),
            (Side.TRUNG_LAP, target_neutral),
        ):
            current_count = count_side(role_pool, side)
            remaining = max(0, target_count - current_count)
            if remaining == 0:
                continue

            special_candidates = [
                role
                for role, definition in self.ROLE_DEFINITIONS.items()
                if definition.side == side
                and role not in normal_roles
                and role not in role_pool
            ]
            take = min(remaining, len(special_candidates))
            if take > 0:
                role_pool.extend(random.sample(special_candidates, take))

        wolves_in_pool = count_side(role_pool, Side.SOI)
        villagers_in_pool = count_side(role_pool, Side.DAN)

        wolves_to_add = max(0, target_wolves - wolves_in_pool)
        villagers_to_add = max(0, target_villagers - villagers_in_pool)

        role_pool.extend([RoleType.SOI_THUONG] * wolves_to_add)
        role_pool.extend([RoleType.DAN_LANG] * villagers_to_add)

        while len(role_pool) < total_players:
            role_pool.append(RoleType.DAN_LANG)

        if len(role_pool) > total_players:
            role_pool = role_pool[:total_players]

        return role_pool

    async def on_game_start(self):
        role_pool = self._build_role_pool()
        random.shuffle(role_pool)
        for idx, player_id in enumerate(self.players.keys()):
            role = role_pool[idx]
            self.players[player_id].role = role
            if role == RoleType.BAO_VE:
                self.players[player_id].lives_left = 2
            elif role == RoleType.MEO_BEO:
                self.players[player_id].lives_left = 9
            elif role in (RoleType.NGUOI_NHAN_NHIN, RoleType.KE_CHAN_DON):
                self.players[player_id].lives_left = 2
            if role == RoleType.NGUOI_CAM_BOM:
                self.bomb_holder_id = player_id
                self.bomb_start_night = 1
            if role == RoleType.THAM_TU_TU:
                self.detective_coins[player_id] = 1
            if role == RoleType.XA_THU:
                self.players[player_id].cooldowns["xa_thu_bullets"] = 2
            if role == RoleType.THICH_KHACH:
                self.players[player_id].cooldowns["thich_khach_charge"] = 1
            if role == RoleType.NGUOI_VAN_DONG_HANH_LANG:
                self.players[player_id].cooldowns["hanh_lang_charge"] = 0
            if role == RoleType.SOI_CO_KHIEN:
                self.players[player_id].cooldowns["soi_co_khien_shields"] = 1
            if role == RoleType.PHAP_SU:
                self.players[player_id].cooldowns["phap_su_revive_left"] = 1
            if role == RoleType.SOI_SAT_THU:
                self.players[player_id].cooldowns["soi_sat_thu_uses_left"] = 2
            if role == RoleType.SOI_GOKU:
                self.players[player_id].cooldowns["soi_goku_uses_left"] = 1
            if role == RoleType.SOI_HAC_AM:
                self.players[player_id].cooldowns["soi_hac_am_uses_left"] = 1
            if role == RoleType.SOI_GIAN_LAN:
                self.players[player_id].cooldowns["soi_gian_lan_uses_left"] = 1
            if role == RoleType.KE_HOI_LO:
                self.players[player_id].cooldowns["coins"] = 0
            if role == RoleType.KE_NGHIEN_CO_BAC:
                self.players[player_id].cooldowns["coins"] = 1
            if role == RoleType.GIAN_THUONG:
                self.players[player_id].cooldowns["coins"] = 0
            if role == RoleType.SOI_TU_BAN:
                self.players[player_id].cooldowns["coins"] = 0
        self.phase = WerewolfPhase.DAY
        self.state = GameState.RUNNING
        self.day_number = 0
        self.night_number = 0
        self.log_event("Game Ma Sói bắt đầu ở ngày 0")

    async def on_game_end(self):
        self.phase = WerewolfPhase.ENDED
        self.state = GameState.ENDED
        self.log_event("Game Ma Sói kết thúc")

    def _kill(self, user_id: int, reason: str):
        player = self.players.get(user_id)
        if not player or not player.is_alive:
            return
        if player.role == RoleType.AYANOKOJI:
            if "ayanokoji_scan_hit" in reason:
                hits = int(player.cooldowns.get("ayanokoji_scan_hits", 0)) + 1
                player.cooldowns["ayanokoji_scan_hits"] = hits
                if hits < 2:
                    return
            elif "sat_thu" in reason:
                hits = int(player.cooldowns.get("ayanokoji_assassin_hits", 0)) + 1
                player.cooldowns["ayanokoji_assassin_hits"] = hits
                if hits < 2:
                    return
            else:
                return
        if player.role == RoleType.VUA_LI_DON and "treo cổ" not in reason:
            return
        if player.role == RoleType.MA_CA_RONG and self.phase == WerewolfPhase.DAY and "treo cổ" not in reason:
            return
        if player.role in (RoleType.NGUOI_NHAN_NHIN, RoleType.KE_NOI_HON) and "sói cắn" in reason:
            return
        if player.role == RoleType.KE_TANG_HINH and "sói cắn" in reason and not player.cooldowns.get("tang_hinh_revived_once"):
            player.cooldowns["tang_hinh_revived_once"] = True
            return
        if player.role == RoleType.SOI_TINH_BAN and self._alive_wolf_count() > 2:
            return
        if player.role == RoleType.LOLICON and "sói cắn" in reason and not player.cooldowns.get("lolicon_revived_once"):
            player.cooldowns["lolicon_revived_once"] = True
            return
        if player.role in (RoleType.NGUOI_NHAN_NHIN, RoleType.KE_CHAN_DON) and player.lives_left > 1:
            player.lives_left -= 1
            self.log_event(f"Player {user_id} mất 1 mạng ({reason}), còn {player.lives_left}")
            return
        if player.role == RoleType.MEO_BEO:
            damage = 2 if any(x in reason for x in ("sói cắn", "kết liễu", "tấn công")) else 1
            player.lives_left -= damage
            if player.lives_left > 0:
                self.log_event(f"Mèo béo {user_id} mất {damage} mạng ({reason}), còn {player.lives_left}")
                return
        player.is_alive = False
        self.log_event(f"Player {user_id} chết ({reason})")
        self.latest_dead_player_id = user_id
        self.latest_dead_role = player.role
        if player.role == RoleType.KE_NOI_DOI and "treo cổ" in reason:
            self.winner = Side.TRUNG_LAP
            self.phase = WerewolfPhase.ENDED
            self.state = GameState.ENDED
        if player.role == RoleType.NGUOI_NOI_TIENG:
            self.pending_villager_announcements.append(
                f"Tin nóng: Người chơi {user_id} (Người Nổi Tiếng) đã chết."
            )
        if player.role == RoleType.KE_CAT_DIEN:
            self.electricity_off = False
        if player.role == RoleType.SOI_TICH_LUY:
            self.wolf_extra_kill_charges = 0

        for pid in self.alive_players:
            p = self.players[pid]
            if p.role == RoleType.KE_BAO_THU and self.ke_bao_thu_partner.get(pid) == user_id:
                self.ke_bao_thu_revenge_ready.add(pid)
            if p.role == RoleType.KE_KE_THUA and self.ke_ke_thua_partner.get(pid) == user_id:
                inherited = self.players[user_id].role
                if inherited and self.ROLE_DEFINITIONS[inherited].side == Side.SOI:
                    self._kill(pid, "Kẻ Kế Thừa chết vì kế thừa vai trò sói")
                elif inherited:
                    p.role = inherited
                    self.log_event(f"Kẻ Kế Thừa {pid} kế thừa vai trò {inherited.value}")
            if p.role == RoleType.YANDERE and self.yandere_target.get(pid) == user_id and p.is_alive:
                self._kill(pid, "Yandere chết theo mục tiêu đã chọn")

        for yid, target in list(self.yandere_target.items()):
            if yid == user_id and target in self.players and self.players[target].is_alive:
                self._kill(target, "chết theo Yandere")

        if player.role == RoleType.LOLI:
            for pid in self.alive_players:
                lp = self.players[pid]
                if lp.role == RoleType.LOLICON:
                    self.lolicon_enraged.add(pid)

        if player.role == RoleType.KE_GHI_HAN:
            charge = int(player.cooldowns.get("ghi_han_charge", 0))
            revenge_kills = min((charge // 2) * 2, max(0, len(self.alive_players)))
            for target_id in self.alive_players[:revenge_kills]:
                if target_id != user_id:
                    self._kill(target_id, "chết theo Kẻ Ghi Hận")

        linked = player.cooldowns.get("linked")
        if isinstance(linked, set):
            for linked_id in list(linked):
                linked_player = self.players.get(linked_id)
                if linked_player and linked_player.is_alive:
                    self._kill(linked_id, f"chết dây chuyền từ liên kết với {user_id}")

    def _alive_wolf_count(self) -> int:
        return sum(1 for pid in self.alive_players if self.side_of(pid) == Side.SOI)

    def _is_tay_chay_active(self, user_id: int) -> bool:
        player = self.players.get(user_id)
        if not player or player.role != RoleType.NGUOI_BI_TAY_CHAY:
            return False
        dead_count = len(self.players) - len(self.alive_players)
        return dead_count < max(1, len(self.players) // 3)

    def _visible_role_for_scan(self, target_id: int) -> Optional[RoleType]:
        target = self.players.get(target_id)
        if not target or not target.role:
            return None
        role = target.role
        if role == RoleType.SOI_CUOP_DANH_TINH and target_id in self.stolen_identity_targets:
            copied_id = self.stolen_identity_targets[target_id]
            copied = self.players.get(copied_id)
            if copied and copied.role:
                role = copied.role
        if target_id in self.wolf_curse_targets:
            return RoleType.SOI_THUONG
        return role

    def _visible_side_for_scan(self, target_id: int) -> Optional[Side]:
        target_role = self._visible_role_for_scan(target_id)
        if not target_role:
            return None
        return self.ROLE_DEFINITIONS[target_role].side

    def _collect_villager_announcements(self) -> Dict[int, List[str]]:
        if not self.pending_villager_announcements:
            return {}
        messages = self.pending_villager_announcements[:]
        self.pending_villager_announcements.clear()
        return {
            pid: messages[:]
            for pid in self.alive_players
            if self.side_of(pid) == Side.DAN
        }

    def _redirect_targets_for_simp(self, caster_id: int, target_ids: List[int]) -> List[int]:
        redirected: List[int] = []
        for target_id in target_ids:
            redirected_target = target_id
            for simp_id in self.alive_players:
                if simp_id == caster_id:
                    continue
                simp = self.players[simp_id]
                if simp.role != RoleType.SIMP:
                    continue
                simp_target = simp.cooldowns.get("simp_target")
                if simp_target == target_id:
                    redirected_target = simp_id
                    break
            redirected.append(redirected_target)
        return redirected

    def _revive(self, caster_id: int, target_id: int) -> tuple[bool, str]:
        caster = self.players.get(caster_id)
        target = self.players.get(target_id)
        if not caster or not caster.role or not target:
            return False, "Không thể hồi sinh mục tiêu."
        if target.is_alive:
            return False, "Chỉ có thể hồi sinh người đã chết."
        target.is_alive = True
        target.pending_death_day = None
        target.last_attacker = None
        if target.role == RoleType.BAO_VE and target.lives_left < 1:
            target.lives_left = 1
        elif target.role == RoleType.MEO_BEO and target.lives_left < 1:
            target.lives_left = 1
        elif target.role in (RoleType.NGUOI_NHAN_NHIN, RoleType.KE_CHAN_DON) and target.lives_left < 1:
            target.lives_left = 1
        else:
            target.lives_left = max(1, target.lives_left)
        self.log_event(f"{caster.role.value} {caster_id} hồi sinh {target_id}")
        return True, f"Đã hồi sinh người chơi {target_id}."

    def _count_votes_for_target(self, target_id: int) -> int:
        return sum(1 for vote in self.day_votes.values() if vote == target_id)

    def _is_jailed(self, user_id: int) -> bool:
        return user_id in self.jailed_players_today

    def check_win_condition(self) -> Optional[Side]:
        if self.winner is not None:
            return self.winner

        # Điều kiện thắng đặc biệt theo vai trò
        if len(self.alive_players) <= 4:
            for pid in self.alive_players:
                if self.players[pid].role == RoleType.KE_SONG_SOT:
                    self.winner = Side.DAN
                    self.phase = WerewolfPhase.ENDED
                    self.state = GameState.ENDED
                    return self.winner
        if len(self.alive_players) == 5:
            for pid in self.alive_players:
                if self.players[pid].role == RoleType.VUA_LI_DON:
                    self.winner = Side.TRUNG_LAP
                    self.phase = WerewolfPhase.ENDED
                    self.state = GameState.ENDED
                    return self.winner
        if len(self.alive_players) == 3:
            for pid in self.alive_players:
                if self.players[pid].role == RoleType.MA_CA_RONG:
                    self.winner = Side.TRUNG_LAP
                    self.phase = WerewolfPhase.ENDED
                    self.state = GameState.ENDED
                    return self.winner
        for pid in self.alive_players:
            p = self.players[pid]
            if p.role != RoleType.KIM_JONG_UN:
                continue
            if len(self.alive_players) <= max(1, (len(self.players) * 4) // 7):
                if "kim_deadline_day" not in p.cooldowns:
                    p.cooldowns["kim_deadline_day"] = self.day_number + 2
            deadline = p.cooldowns.get("kim_deadline_day")
            if isinstance(deadline, int) and self.day_number >= deadline:
                self.winner = Side.TRUNG_LAP
                self.phase = WerewolfPhase.ENDED
                self.state = GameState.ENDED
                return self.winner

        alive = [self.players[pid] for pid in self.alive_players]
        wolves = sum(
            1
            for p in alive
            if p.role and self.ROLE_DEFINITIONS[p.role].side == Side.SOI
        )
        villagers = sum(
            1
            for p in alive
            if p.role and self.ROLE_DEFINITIONS[p.role].side == Side.DAN
        )

        if wolves == 0 and alive:
            ayan_alive = next(
                (p for p in alive if p.role == RoleType.AYANOKOJI),
                None,
            )
            if ayan_alive is not None:
                alive_villager_scanners = sum(
                    1
                    for p in alive
                    if p.role
                    and self.ROLE_DEFINITIONS[p.role].side == Side.DAN
                    and self.ROLE_DEFINITIONS[p.role].info_capable
                )
                if alive_villager_scanners == 0:
                    self.winner = Side.TRUNG_LAP
                    self.phase = WerewolfPhase.ENDED
                    self.state = GameState.ENDED
                    return self.winner
            self.winner = Side.DAN
            self.phase = WerewolfPhase.ENDED
            self.state = GameState.ENDED
            return self.winner
        if wolves > 0 and wolves >= villagers:
            self.winner = Side.SOI
            self.phase = WerewolfPhase.ENDED
            self.state = GameState.ENDED
            return self.winner
        return None

    def vote_day(self, voter_id: int, target_id: Optional[int]) -> tuple[bool, str]:
        if self.phase != WerewolfPhase.DAY:
            return False, "Chỉ được vote vào ban ngày."
        voter = self.players.get(voter_id)
        if not voter or not voter.is_alive:
            return False, "Bạn không thể vote."
        if self._is_jailed(voter_id):
            return False, "Bạn đang bị nhốt và không thể vote hôm nay."
        if voter.role == RoleType.MA_CA_RONG:
            return False, "Ma Cà Rồng không thể vote."
        if voter.role == RoleType.KE_CAT_DIEN and target_id is not None:
            return False, "Kẻ Cắt Điện chỉ được vote bỏ qua."
        if voter.role == RoleType.THICH_KHACH and target_id == voter_id:
            return False, "Thích Khách không thể tự vote bản thân."
        if voter_id in self.vote_locked_players and voter_id in self.day_votes:
            return False, "Bạn đã bị khóa vote và không thể đổi phiếu."
        if target_id is not None:
            target = self.players.get(target_id)
            if not target or not target.is_alive:
                return False, "Mục tiêu không hợp lệ."
            if target_id in self.day_vote_immune_targets:
                target_id = None
        if voter_id not in self.day_vote_order:
            self.day_vote_order.append(voter_id)
        self.day_votes[voter_id] = target_id
        voter.voted = target_id
        self.log_event(f"Vote ngày: {voter_id} -> {target_id if target_id else 'SKIP'}")
        if target_id is not None:
            target_player = self.players.get(target_id)
            if target_player and target_player.role == RoleType.KE_TAM_LY_YEU:
                votes_from_others = sum(
                    1 for vid, t in self.day_votes.items() if t == target_id and vid != target_id
                )
                if votes_from_others >= 3:
                    self._kill(target_id, "Kẻ Tâm Lý Yếu chịu không nổi áp lực bỏ phiếu")
                    self.check_win_condition()
            threshold = max(1, (2 * len(self.players) + 6) // 7)
            for judge_id, judged_target in list(self.tham_phan_targets.items()):
                judge = self.players.get(judge_id)
                if not judge or not judge.is_alive or judged_target != target_id:
                    continue
                judged_player = self.players.get(judged_target)
                if not judged_player or not judged_player.is_alive:
                    continue
                if self.side_of(judged_target) == Side.DAN:
                    continue
                if self._count_votes_for_target(judged_target) >= threshold:
                    self._kill(judged_target, "bị Thẩm Phán kết tội")
                    self.check_win_condition()
                    break
        return True, "Đã ghi nhận vote."

    def vote_wolf(self, voter_id: int, target_id: int) -> tuple[bool, str]:
        if self.phase != WerewolfPhase.NIGHT:
            return False, "Chỉ được vote sói vào ban đêm."
        voter = self.players.get(voter_id)
        if not voter or not voter.is_alive:
            return False, "Bạn không thể vote."
        if self.side_of(voter_id) != Side.SOI:
            return False, "Chỉ sói còn sống mới được vote sói."
        target = self.players.get(target_id)
        if not target or not target.is_alive:
            return False, "Mục tiêu không hợp lệ."
        if target_id == voter_id:
            return False, "Không thể tự cắn."
        self.wolf_votes[voter_id] = target_id
        self.log_event(f"Vote sói: {voter_id} -> {target_id}")
        return True, "Đã ghi nhận vote sói."

    def cast_skill(
        self, caster_id: int, targets: List[int], skill_name: Optional[str] = None
    ) -> tuple[bool, str, List[str]]:
        caster = self.players.get(caster_id)
        if not caster or not caster.role:
            return False, "Bạn không thể dùng kỹ năng.", []
        if not caster.is_alive and caster.role != RoleType.PHAP_SU:
            return False, "Bạn không thể dùng kỹ năng.", []
        if self.phase == WerewolfPhase.DAY and self._is_jailed(caster_id):
            return False, "Bạn đang bị nhốt và không thể dùng skill ban ngày.", []
        if self.phase == WerewolfPhase.NIGHT and caster_id in self.night_blocked_players:
            return False, "Bạn đã bị khóa kỹ năng trong đêm này.", []
        if self.electricity_off and caster.role != RoleType.KE_CAT_DIEN:
            return False, "Điện đang bị cắt, kỹ năng đặc biệt tạm thời vô hiệu.", []
        ok, message, private_messages = self._apply_role_skill(
            caster_id=caster_id,
            targets=targets,
            skill_name=skill_name,
        )
        return ok, message, private_messages

    def _role_priority(self, user_id: int) -> int:
        player = self.players.get(user_id)
        if not player or not player.role:
            return -1
        role_def = self.ROLE_DEFINITIONS.get(player.role)
        return role_def.priority if role_def else -1

    def _apply_role_skill(
        self,
        caster_id: int,
        targets: List[int],
        skill_name: Optional[str] = None,
    ) -> tuple[bool, str, List[str]]:
        caster = self.players.get(caster_id)
        if not caster or not caster.role:
            return False, "Bạn không thể dùng kỹ năng.", []
        role = caster.role
        spec: Optional[RoleSpec] = ROLE_SPECS.get(role)
        if not spec or not spec.skills:
            return False, "Role này chưa có kỹ năng chủ động.", []

        base_skill_name, skill_arg = self._split_skill_name(skill_name)
        chosen_skill = None
        if base_skill_name:
            for skill in spec.skills:
                if skill.name == base_skill_name:
                    chosen_skill = skill
                    break
            if chosen_skill is None:
                return False, "Kỹ năng không hợp lệ cho role này.", []
        else:
            chosen_skill = spec.skills[0]

        if chosen_skill.phase == "night" and self.phase != WerewolfPhase.NIGHT:
            return False, "Kỹ năng này chỉ dùng ban đêm.", []
        if chosen_skill.phase == "day" and self.phase != WerewolfPhase.DAY:
            return False, "Kỹ năng này chỉ dùng ban ngày.", []

        if spec.cooldown > 0 and self.phase == WerewolfPhase.NIGHT:
            cooldown_key = f"cooldown:{chosen_skill.name}:until_night"
            until_night = int(caster.cooldowns.get(cooldown_key, 0))
            if self.night_number < until_night:
                return False, "Kỹ năng đang hồi chiêu.", []

        min_targets = chosen_skill.target_count
        max_targets = chosen_skill.max_targets or chosen_skill.target_count
        if len(targets) < min_targets or len(targets) > max_targets:
            if min_targets == max_targets:
                return False, f"Kỹ năng này cần đúng {min_targets} mục tiêu.", []
            return False, f"Kỹ năng này cần từ {min_targets} đến {max_targets} mục tiêu.", []

        target_ids = targets
        if len(set(target_ids)) != len(target_ids):
            return False, "Không thể chọn trùng mục tiêu.", []

        for target_id in target_ids:
            target = self.players.get(target_id)
            if not target:
                return False, "Mục tiêu không hợp lệ.", []
            if "revive_target" in chosen_skill.effects:
                if target.is_alive:
                    return False, "Chỉ có thể chọn người đã chết để hồi sinh.", []
            elif not target.is_alive:
                return False, "Mục tiêu không hợp lệ.", []
            if self.phase == WerewolfPhase.NIGHT and target.role == RoleType.KE_TAM_LY_YEU and target_id != caster_id:
                return False, "Không thể tác động Kẻ Tâm Lý Yếu vào ban đêm.", []
            if not spec.can_target_self and target_id == caster_id:
                return False, "Không thể tự nhắm mục tiêu.", []
            if chosen_skill.allowed_target_sides is not None:
                side = self.side_of(target_id)
                if side not in chosen_skill.allowed_target_sides:
                    return False, "Mục tiêu không đúng phe cho kỹ năng này.", []
            target_role = target.role
            if (
                self.phase == WerewolfPhase.NIGHT
                and target_role == RoleType.KE_PHAN_DON
                and target_id != caster_id
                and "kill_target" not in chosen_skill.effects
                and "revive_target" not in chosen_skill.effects
            ):
                self._kill(caster_id, "bị Kẻ Phản Đòn phản kích")
                return False, "Bạn bị Kẻ Phản Đòn phản kích và không thể dùng kỹ năng.", []

        if self.phase == WerewolfPhase.NIGHT and int(caster.cooldowns.get("night_skill_blocked", 0)) > 0:
            return False, "Bạn đang bị mất kỹ năng trong đêm này.", []
        if self.phase == WerewolfPhase.NIGHT and caster_id in self.chan_don_redirect and role != RoleType.KE_CHAN_DON:
            redirected_target = self.chan_don_redirect[caster_id]
            target_ids = [redirected_target for _ in target_ids]
        target_ids = self._redirect_targets_for_simp(caster_id, target_ids)
        if len(set(target_ids)) != len(target_ids):
            return False, "Mục tiêu bị chuyển hướng Simp trùng nhau, không thể dùng kỹ năng.", []

        if chosen_skill.usage_limit is not None:
            usage_key = chosen_skill.usage_limit_key or f"{role.value}:{chosen_skill.name}:uses_left"
            raw_remaining = caster.cooldowns.get(usage_key, chosen_skill.usage_limit)
            remaining = int(raw_remaining) if isinstance(raw_remaining, int) else chosen_skill.usage_limit
            usage_cost = len(target_ids) if chosen_skill.usage_cost_per_target else 1
            if remaining is None or remaining < usage_cost:
                return False, "Bạn đã dùng hết lượt của kỹ năng này.", []
            caster.cooldowns[usage_key] = remaining - usage_cost

        if role == RoleType.KE_HOI_LO and chosen_skill.name == "hoi_lo":
            if self.phase != WerewolfPhase.DAY:
                return False, "Kẻ Hối Lộ chỉ dùng kỹ năng ban ngày.", []
            ok_spend, _ = self._spend_coins(caster_id, 1)
            if not ok_spend:
                return False, "Bạn không đủ xu để hối lộ.", []
            if self.latest_dead_player_id is None or self.latest_dead_role is None:
                return True, "Đã hối lộ nhưng chưa có người chết để công bố.", []
            return True, "Đã hối lộ thành công.", [
                f"Quản trò tiết lộ: người chết gần nhất là {self.latest_dead_player_id} với vai trò **{self.latest_dead_role.value}**."
            ]

        if role == RoleType.KE_NGHIEN_CO_BAC and chosen_skill.name == "cuoc_dem":
            if self.phase != WerewolfPhase.NIGHT:
                return False, "Kẻ Nghiện Cờ Bạc chỉ cược vào ban đêm.", []
            if caster_id not in self.players:
                return False, "Người chơi không hợp lệ.", []
            stake = 1
            if skill_arg is not None:
                try:
                    stake = int(skill_arg)
                except ValueError:
                    return False, "Số xu cược không hợp lệ.", []
            if stake <= 0:
                return False, "Số xu cược phải > 0.", []
            coins = int(caster.cooldowns.get("coins", 0))
            if coins < stake:
                return False, "Bạn không đủ xu để cược.", []
            if len(target_ids) == 0 or len(target_ids) > 3:
                return False, "Cần chọn từ 1 đến 3 người cho cửa cược.", []
            caster.cooldowns["coins"] = coins - stake
            self.ke_nghien_co_bac_bets[caster_id] = (stake, set(target_ids), self.night_number)
            return True, "Đã đặt cược thành công.", []

        if role == RoleType.KE_DANH_BAC and chosen_skill.name == "doan_so_nguoi_chet":
            if self.phase != WerewolfPhase.NIGHT:
                return False, "Kẻ Đánh Bạc chỉ đoán vào ban đêm.", []
            if skill_arg is None:
                return False, "Hãy truyền số dự đoán theo dạng doan_so_nguoi_chet:<so_nguoi_chet>.", []
            try:
                guess_count = int(skill_arg)
            except ValueError:
                return False, "Số người chết dự đoán không hợp lệ.", []
            if guess_count < 0:
                return False, "Số người chết dự đoán phải >= 0.", []
            self.ke_danh_bac_predictions[caster_id] = (guess_count, self.night_number)
            return True, "Đã ghi nhận dự đoán số người chết.", []

        if role in (RoleType.SAT_THU, RoleType.SOI_SAT_THU) and chosen_skill.name == "sat_thu":
            if skill_arg is None:
                return False, "Hãy dùng dạng sat_thu:<role_guess> để đoán vai trò.", []
            guessed_role = self._parse_role(skill_arg)
            if not guessed_role:
                return False, "Role đoán không hợp lệ.", []
            target_role = self.players[target_ids[0]].role
            if target_role == guessed_role:
                if self.phase == WerewolfPhase.DAY:
                    self._kill(target_ids[0], f"bị {role.value} đoán đúng và kết liễu")
                    self.check_win_condition()
                else:
                    self.pending_night_kills[caster_id] = target_ids[0]
                return True, "Đoán đúng vai trò, đã ghi nhận đòn kết liễu.", []
            self._kill(caster_id, f"{role.value} đoán sai vai trò")
            self.check_win_condition()
            return False, "Đoán sai vai trò, bạn đã chết.", []

        if role == RoleType.KE_TIM_SU_THAT and chosen_skill.name == "tim_su_that":
            if self.phase != WerewolfPhase.DAY:
                return False, "Kẻ Tìm Sự Thật chỉ công bố ban ngày.", []
            if skill_arg is None:
                return False, "Hãy dùng dạng tim_su_that:<role_guess>.", []
            guessed_role = self._parse_role(skill_arg)
            if not guessed_role:
                return False, "Role đoán không hợp lệ.", []
            target_id = target_ids[0]
            target = self.players.get(target_id)
            if not target or not target.is_alive or not target.role:
                return False, "Mục tiêu không hợp lệ.", []
            if guessed_role != target.role:
                return False, "Công bố sai vai trò.", []
            hit_set = self.tim_su_that_correct_targets.setdefault(caster_id, set())
            hit_set.add(target_id)
            alive_hits = [pid for pid in hit_set if self.players.get(pid) and self.players[pid].is_alive]
            if len(alive_hits) >= 3:
                self.winner = Side.TRUNG_LAP
                self.phase = WerewolfPhase.ENDED
                self.state = GameState.ENDED
            return True, "Công bố vai trò chính xác.", []

        if role == RoleType.KE_BAO_THU and chosen_skill.name == "tam_giao":
            partner_id = target_ids[0]
            if partner_id == caster_id:
                return False, "Không thể chọn chính mình làm tâm giao.", []
            self.ke_bao_thu_partner[caster_id] = partner_id
            return True, "Đã chọn tâm giao cho đêm nay.", []

        if role == RoleType.KE_BAO_THU and chosen_skill.name == "bao_thu":
            if self.phase != WerewolfPhase.DAY:
                return False, "Chỉ trả thù vào ban ngày.", []
            if caster_id not in self.ke_bao_thu_revenge_ready:
                return False, "Tâm giao của bạn chưa chết, chưa thể trả thù.", []
            self.ke_bao_thu_revenge_ready.discard(caster_id)
            self._kill(target_ids[0], "bị Kẻ Báo Thù trả thù")
            self.check_win_condition()
            return True, "Đã trả thù thành công.", []

        if role == RoleType.KE_DA_NGHI:
            if chosen_skill.name == "tu_choi_tiet_lo":
                self.ke_da_nghi_opt_out.add(caster_id)
                return True, "Bạn đã từ chối tiết lộ của Kẻ Đa Nghi.", []
            marks = self.ke_da_nghi_marks.setdefault(caster_id, [])
            if self.night_number >= 3:
                return False, "Kẻ Đa Nghi chỉ được đánh dấu trong 3 đêm đầu.", []
            if target_ids[0] in marks:
                return False, "Bạn đã đánh dấu người này rồi.", []
            if len(marks) >= 3:
                return False, "Bạn đã đánh dấu đủ 3 người.", []
            marks.append(target_ids[0])
            return True, "Đã đánh dấu mục tiêu.", []

        if role == RoleType.KE_THAM_DO:
            target_id = target_ids[0]
            if target_id not in self.prev_day_voted_targets:
                return False, "Kẻ Thăm Dò chỉ soi người có phiếu ở buổi sáng trước.", []
            visible_role = self._visible_role_for_scan(target_id)
            self.ke_tham_do_last_target[caster_id] = target_id
            return True, "Đã soi thăm dò.", [f"Vai trò của {target_id}: **{visible_role.value if visible_role else 'chưa rõ'}**"]

        if role == RoleType.KE_KE_THUA:
            partner_id = target_ids[0]
            if partner_id == caster_id:
                return False, "Không thể tự kết hữu.", []
            self.ke_ke_thua_partner[caster_id] = partner_id
            return True, "Đã chọn người kết hữu.", []

        if role == RoleType.YANDERE:
            if caster_id in self.yandere_target:
                return False, "Yandere chỉ được chọn mục tiêu một lần.", []
            self.yandere_target[caster_id] = target_ids[0]
            return True, "Đã chọn mục tiêu định mệnh.", []

        if role == RoleType.NGUOI_GAY:
            target_id = target_ids[0]
            if self.nguoi_gay_last_target.get(caster_id) == target_id:
                return False, "Không được chọn cùng một người hai đêm liên tiếp.", []
            self.nguoi_gay_partner[caster_id] = target_id
            self.nguoi_gay_last_target[caster_id] = target_id
            if self.side_of(target_id) == Side.SOI:
                self._kill(caster_id, "Người Gay ngủ cùng Sói")
                return True, "Bạn đã ngủ cùng Sói và tử nạn.", []
            return True, "Đã chọn người ngủ cùng cho đêm nay.", []

        if role == RoleType.KE_TANG_HINH:
            if self.phase != WerewolfPhase.DAY:
                return False, "Kẻ Tàng Hình chỉ dùng kỹ năng bắn ban ngày.", []
            if caster_id in self.ke_tang_hinh_day_chatters:
                return False, "Bạn đã chat trong ngày nên không thể tàng hình bắn.", []
            if caster_id in self.ke_tang_hinh_day_killed:
                return False, "Bạn đã bắn trong ngày này.", []
            self.ke_tang_hinh_day_killed.add(caster_id)

        if role == RoleType.KE_PHONG_HOA and chosen_skill.name == "phong_hoa":
            if skill_arg == "dot":
                if not self.phong_hoa_doused:
                    return False, "Chưa có ai bị tẩm xăng để đốt.", []
                for pid in list(self.phong_hoa_doused):
                    if self.players.get(pid) and self.players[pid].is_alive:
                        self.phong_hoa_burn_targets.add(pid)
                self.phong_hoa_doused.clear()
                return True, "Đã châm lửa toàn bộ mục tiêu bị tẩm xăng.", []
            for tid in target_ids:
                self.phong_hoa_doused.add(tid)
            return True, "Đã tẩm xăng mục tiêu.", []

        if role == RoleType.THAM_PHAN:
            target_id = target_ids[0]
            self.tham_phan_targets[caster_id] = target_id
            return True, "Đã đặt bản án cho ngày hôm sau.", []

        if role == RoleType.SIMP:
            if chosen_skill.name == "nhan_hieu_ung":
                self.players[caster_id].cooldowns["simp_target"] = target_ids[0]
                return True, "Đã chọn người để simp.", []
            simp_target = self.players[caster_id].cooldowns.get("simp_target")
            if simp_target is None:
                return False, "Bạn chưa chọn người để simp.", []
            if self.players[caster_id].cooldowns.get("simp_revenge_used"):
                return False, "Bạn đã dùng quyền phản simp.", []
            if self.day_votes.get(target_ids[0]) != simp_target:
                return False, "Chỉ được giết người đã vote mục tiêu bạn simp.", []
            self.players[caster_id].cooldowns["simp_revenge_used"] = True
            self._kill(target_ids[0], "bị Simp phản kích")
            self.check_win_condition()
            return True, "Đã phản simp và kết liễu mục tiêu.", []

        if role == RoleType.KE_CHAN_DON:
            chosen = target_ids[0]
            self.chan_don_redirect[chosen] = caster_id
            self.chan_don_tank_wolf = caster_id if self.side_of(chosen) == Side.SOI else self.chan_don_tank_wolf
            return True, "Đã kích hoạt chắn đòn.", []

        if role == RoleType.NGUOI_NHAN_NHIN:
            if self.phase != WerewolfPhase.DAY:
                return False, "Chỉ dùng kỹ năng Nhẫn Nhịn ban ngày.", []
            if caster.cooldowns.get("nhan_nhin_used"):
                return False, "Bạn đã dùng quyền Nhẫn Nhịn.", []
            current_counts: Dict[int, int] = {}
            for voted_target in self.day_votes.values():
                if voted_target is not None and self.players.get(voted_target) and self.players[voted_target].is_alive:
                    current_counts[voted_target] = current_counts.get(voted_target, 0) + 1
            if not current_counts:
                return False, "Chưa có phiếu để chuyển hướng.", []
            highest = max(current_counts.values())
            top_targets = {pid for pid, c in current_counts.items() if c == highest}
            for voter_id, voted_target in list(self.day_votes.items()):
                if voted_target in top_targets:
                    self.day_votes[voter_id] = caster_id
            caster.cooldowns["nhan_nhin_used"] = True
            self._kill(caster_id, "Người Nhẫn Nhịn dùng kỹ năng nhận vote")
            return True, "Đã nhận toàn bộ phiếu cao nhất về mình.", []

        if role == RoleType.SOI_BANG:
            target_id = target_ids[0]
            last_target = caster.cooldowns.get("soi_bang_last_target")
            if last_target == target_id:
                return False, "Sói Băng không được chọn cùng mục tiêu hai đêm liên tiếp.", []
            caster.cooldowns["soi_bang_last_target"] = target_id
            self.night_blocked_players.add(target_id)
            self.log_event(f"{role.value} {caster_id} đóng băng kỹ năng của {target_id}")
            return True, "Đã khóa kỹ năng mục tiêu trong đêm.", []

        if role == RoleType.KE_TINH_GIAC_GIUA_DEM:
            self.night_wake_watch[caster_id] = target_ids[0]
            return True, "Đã theo dõi mục tiêu cho đêm này.", [
                f"Bạn sẽ nhận báo cáo về hoạt động đêm của {target_ids[0]} sau khi đêm kết thúc."
            ]

        if role == RoleType.NHA_NGOAI_CAM:
            self.night_killer_watch[caster_id] = (target_ids[0], target_ids[1])
            return True, "Đã ghi nhận 2 mục tiêu theo dõi cho đêm này.", [
                f"Bạn sẽ nhận báo cáo liệu {target_ids[0]} hoặc {target_ids[1]} có giết người đêm nay hay không."
            ]

        if role == RoleType.SOI_MACH_LEO:
            target_id = target_ids[0]
            last_target = caster.cooldowns.get("soi_mach_leo_last_target")
            if last_target == target_id:
                return False, "Sói Mách Lẻo không được chọn cùng mục tiêu hai đêm liên tiếp.", []
            caster.cooldowns["soi_mach_leo_last_target"] = target_id
            self.jailed_players_next_day.add(target_id)
            self.log_event(f"{role.value} {caster_id} nhốt {target_id} cho ban ngày hôm sau")
            return True, "Đã nhốt mục tiêu cho ngày hôm sau.", []

        if role == RoleType.SOI_PHAP_SU:
            target_id = target_ids[0]
            self.wolf_curse_targets.add(target_id)
            self.log_event(f"{role.value} {caster_id} yểm {target_id}")
            return True, "Đã yểm mục tiêu cho đêm này.", [f"Mục tiêu {target_id} bị soi thành phe Sói trong đêm này."]

        if role == RoleType.SOI_CUOP_DANH_TINH:
            target_id = target_ids[0]
            last_target = caster.cooldowns.get("soi_cuop_last_target")
            if last_target == target_id:
                return False, "Không được cướp cùng một người hai đêm liên tiếp.", []
            caster.cooldowns["soi_cuop_last_target"] = target_id
            self.stolen_identity_targets[caster_id] = target_id
            self.log_event(f"{role.value} {caster_id} cướp danh tính {target_id}")
            return True, "Đã cướp danh tính mục tiêu trong đêm này.", [
                f"Bạn đang mang danh tính vai trò/phe của {target_id} trong đêm này."
            ]

        if role == RoleType.SOI_GOKU:
            self.soi_goku_pierce_attackers.add(caster_id)
            self.pending_night_kills[caster_id] = target_ids[0]
            self.log_event(f"{role.value} {caster_id} dùng Kamehameha vào {target_ids[0]}")
            return True, "Đã tung Kamehameha xuyên bảo vệ.", []

        if role == RoleType.SOI_HAC_AM:
            self.soi_hac_am_target = target_ids[0]
            self.soi_hac_am_hide_votes = True
            return True, "Đã đánh dấu nhân đôi phiếu cho ngày sau.", []

        if role == RoleType.SOI_PHAN_DONG:
            if not caster.cooldowns.get("soi_phan_dong_ready"):
                return False, "Bạn chưa có lượt phản động bổ sung.", []
            caster.cooldowns["soi_phan_dong_ready"] = False
            self.pending_night_kills[caster_id] = target_ids[0]
            return True, "Đã dùng lượt phản động để giết.", []

        if role == RoleType.SOI_DAT_BAY:
            target_id = target_ids[0]
            if self.soi_dat_bay_last_target.get(caster_id) == target_id:
                return False, "Không thể đặt bẫy cùng mục tiêu hai đêm liên tiếp.", []
            self.soi_dat_bay_last_target[caster_id] = target_id
            self.soi_dat_bay_targets.add(target_id)
            return True, "Đã đặt bẫy mục tiêu trong đêm.", []

        if role == RoleType.SOI_GIAN_LAN:
            self.day_skip_forced = True
            return True, "Đã sẵn sàng gian lận bỏ qua vote nếu đủ skip.", []

        if role == RoleType.SOI_TU_BAN and chosen_skill.name == "tu_ban_bao_ke":
            ok_spend, _ = self._spend_coins(caster_id, 2)
            if not ok_spend:
                return False, "Sói Tư Bản cần 2 xu để bảo kê.", []
            self.night_skills[caster_id] = target_ids[:]
            return True, "Đã dùng 2 xu để bảo kê sói.", []

        if role == RoleType.KE_DAT_BOM:
            self.ke_dat_bom_placements[target_ids[0]] = self.night_number + 1
            return True, "Đã cài bom, sẽ nổ vào đêm kế tiếp.", []

        if role == RoleType.LOLICON and chosen_skill.name == "soi_loli":
            loli_id = next((pid for pid, p in self.players.items() if p.role == RoleType.LOLI), None)
            if loli_id is None:
                return True, "Không có Loli trong ván này.", []
            return True, "Đã nhận thông tin Loli.", [f"Loli là người chơi **{loli_id}**."]

        if role == RoleType.CON_QUA:
            if caster_id in self.con_qua_kill_ready:
                self.con_qua_kill_ready.discard(caster_id)
                self.pending_night_kills[caster_id] = target_ids[0]
                return True, "Đã dùng lượt giết thưởng của Con Quạ.", []
            self.con_qua_marked_target[caster_id] = target_ids[0]

        if role == RoleType.CAO_BOI:
            target_id = target_ids[0]
            target_player = self.players.get(target_id)
            if target_player and target_player.role and self.ROLE_DEFINITIONS[target_player.role].kill_capable:
                self._kill(caster_id, "Cao bồi thua trong màn đấu súng")
                return True, "Đọ súng thất bại, bạn đã chết.", []
            self.pending_night_kills[caster_id] = target_id
            return True, "Đọ súng thành công, mục tiêu sẽ chết đêm nay.", []

        if role == RoleType.KE_CAT_DIEN and chosen_skill.name == "cat_dien":
            self.electricity_off = True
            return True, "Đã cắt điện toàn bộ ván chơi.", []

        if role == RoleType.SOI_KET_GIOI:
            if caster.cooldowns.get("soi_ket_gioi_used"):
                return False, "Sói Kết Giới chỉ có thể dùng một lần mỗi ván.", []
            caster.cooldowns["soi_ket_gioi_used"] = True
            self.wolf_barrier_active = True
            self.log_event(f"{role.value} {caster_id} kích hoạt kết giới cho phe sói")
            return True, "Đã tạo kết giới cho phe sói trong đêm này.", []

        if role == RoleType.SOI_HO_VE and self.phase == WerewolfPhase.DAY:
            if caster.cooldowns.get("soi_ho_ve_used"):
                return False, "Sói Hộ Vệ chỉ có thể cứu treo cổ một lần mỗi ván.", []
            self.day_vote_immune_targets.add(target_ids[0])
            caster.cooldowns["soi_ho_ve_used"] = True
            self.log_event(f"{role.value} {caster_id} bảo hộ treo cổ cho {target_ids[0]}")
            return True, "Đã bảo hộ mục tiêu khỏi treo cổ trong ngày.", []

        private_messages: List[str] = []

        if role == RoleType.MEO_BEO and "info_role" in chosen_skill.effects:
            if caster.lives_left <= 1:
                return False, "Mèo Béo không đủ mạng để dùng kỹ năng soi.", []
            caster.lives_left -= 1

        if "protect_target" in chosen_skill.effects:
            self.night_skills[caster_id] = target_ids[:]
            self.log_event(f"{role.value} {caster_id} bảo vệ {target_ids}")

        if "info_role" in chosen_skill.effects:
            if chosen_skill.target_count == 1:
                target_id = target_ids[0]
                if self.phase == WerewolfPhase.NIGHT and self._is_tay_chay_active(target_id):
                    private_messages.append(f"Không thể soi người chơi {target_id} trong đêm này.")
                else:
                    target_player = self.players.get(target_id)
                    visible_role = self._visible_role_for_scan(target_id)
                    if target_player and target_player.role == RoleType.AYANOKOJI and target_id != caster_id:
                        scan_hits = int(target_player.cooldowns.get("ayanokoji_scan_hits", 0)) + 1
                        target_player.cooldowns["ayanokoji_scan_hits"] = scan_hits
                        if scan_hits >= 2:
                            self._kill(target_id, "ayanokoji_scan_hit")
                        visible_role = RoleType.DAN_LANG if scan_hits == 1 else visible_role
                    if role == RoleType.KE_HOANG_TUONG and visible_role and random.random() < 0.5:
                        fake_pool = [r for r in RoleType if r != visible_role]
                        visible_role = random.choice(fake_pool)
                    role_name = visible_role.value if visible_role else "chưa rõ"
                    private_messages.append(f"Vai trò của {target_id}: **{role_name}**")
            else:
                lines = []
                for target_id in target_ids:
                    if self.phase == WerewolfPhase.NIGHT and self._is_tay_chay_active(target_id):
                        lines.append(f"{target_id}: **không thể soi**")
                    else:
                        target_player = self.players.get(target_id)
                        visible_role = self._visible_role_for_scan(target_id)
                        if target_player and target_player.role == RoleType.AYANOKOJI and target_id != caster_id:
                            scan_hits = int(target_player.cooldowns.get("ayanokoji_scan_hits", 0)) + 1
                            target_player.cooldowns["ayanokoji_scan_hits"] = scan_hits
                            if scan_hits >= 2:
                                self._kill(target_id, "ayanokoji_scan_hit")
                            visible_role = RoleType.DAN_LANG if scan_hits == 1 else visible_role
                        if role == RoleType.KE_HOANG_TUONG and visible_role and random.random() < 0.5:
                            fake_pool = [r for r in RoleType if r != visible_role]
                            visible_role = random.choice(fake_pool)
                        role_name = visible_role.value if visible_role else "chưa rõ"
                        lines.append(f"{target_id}: **{role_name}**")
                private_messages.append("Thông tin vai trò: " + ", ".join(lines))

        if "info_side" in chosen_skill.effects:
            lines = []
            for target_id in target_ids:
                if self.phase == WerewolfPhase.NIGHT and self._is_tay_chay_active(target_id):
                    lines.append(f"{target_id}: **không thể soi**")
                else:
                    target_player = self.players.get(target_id)
                    side = self._visible_side_for_scan(target_id)
                    if target_player and target_player.role == RoleType.AYANOKOJI and target_id != caster_id:
                        scan_hits = int(target_player.cooldowns.get("ayanokoji_scan_hits", 0)) + 1
                        target_player.cooldowns["ayanokoji_scan_hits"] = scan_hits
                        if scan_hits >= 2:
                            self._kill(target_id, "ayanokoji_scan_hit")
                        side = Side.DAN if scan_hits == 1 else side
                    lines.append(f"{target_id}: **{side.value if side else 'không rõ'}**")
            private_messages.append("Thông tin phe: " + ", ".join(lines))
            if role == RoleType.NHA_BAO:
                noi_tieng = next(
                    (pid for pid, p in self.players.items() if p.role == RoleType.NGUOI_NOI_TIENG),
                    None,
                )
                if noi_tieng is not None:
                    private_messages.append(f"Nhà báo biết Người Nổi Tiếng là: **{noi_tieng}**")

        if "compare_side" in chosen_skill.effects:
            left, right = target_ids[0], target_ids[1]
            if self.phase == WerewolfPhase.NIGHT and (self._is_tay_chay_active(left) or self._is_tay_chay_active(right)):
                private_messages.append(f"So sánh phe {left} và {right}: **không thể soi chính xác**.")
                same_side = True
            else:
                left_side = self._visible_side_for_scan(left)
                right_side = self._visible_side_for_scan(right)
                for target_id in (left, right):
                    target_player = self.players.get(target_id)
                    if target_player and target_player.role == RoleType.AYANOKOJI and target_id != caster_id:
                        scan_hits = int(target_player.cooldowns.get("ayanokoji_scan_hits", 0)) + 1
                        target_player.cooldowns["ayanokoji_scan_hits"] = scan_hits
                        if scan_hits >= 2:
                            self._kill(target_id, "ayanokoji_scan_hit")
                        if target_id == left:
                            left_side = Side.DAN if scan_hits == 1 else left_side
                        else:
                            right_side = Side.DAN if scan_hits == 1 else right_side
                same_side = left_side == right_side
                private_messages.append(
                    f"So sánh phe {left} và {right}: {'cùng phe' if same_side else 'khác phe'}."
                )
            detective = self.players.get(caster_id)
            if detective and detective.role == RoleType.THAM_TU_TU and not same_side:
                self.detective_coins[caster_id] = self.detective_coins.get(caster_id, 0) + 1

        if "info_counts" in chosen_skill.effects:
            alive_dan = sum(1 for pid in self.alive_players if self.side_of(pid) == Side.DAN)
            alive_soi = sum(1 for pid in self.alive_players if self.side_of(pid) == Side.SOI)
            alive_trung_lap = sum(1 for pid in self.alive_players if self.side_of(pid) == Side.TRUNG_LAP)
            private_messages.append(
                f"Thống kê còn sống - Dân: **{alive_dan}**, Sói: **{alive_soi}**, Trung lập: **{alive_trung_lap}**"
            )
            if role == RoleType.NHA_BAO:
                noi_tieng = next(
                    (pid for pid, p in self.players.items() if p.role == RoleType.NGUOI_NOI_TIENG),
                    None,
                )
                if noi_tieng is not None:
                    private_messages.append(f"Người Nổi Tiếng hiện tại là: **{noi_tieng}**")

        if "revive_target" in chosen_skill.effects:
            ok, msg = self._revive(caster_id, target_ids[0])
            if not ok:
                return False, msg, []
            return True, msg, private_messages

        if "vote_bonus" in chosen_skill.effects:
            target_id = target_ids[0]
            if role == RoleType.CON_QUA and self.phase == WerewolfPhase.NIGHT:
                self.next_day_vote_bonus[target_id] = (
                    self.next_day_vote_bonus.get(target_id, 0) + chosen_skill.vote_bonus
                )
                self.log_event(f"{role.value} {caster_id} gắn +{chosen_skill.vote_bonus} phiếu cho {target_id} vào ngày sau")
            else:
                self.vote_bonus[target_id] = self.vote_bonus.get(target_id, 0) + chosen_skill.vote_bonus
            self.log_event(
                f"{role.value} {caster_id} cộng {chosen_skill.vote_bonus} phiếu cho {target_id}"
            )

        if "kill_target" in chosen_skill.effects:
            target_id = target_ids[0]
            if role == RoleType.KE_CAT_DIEN and chosen_skill.name == "cat_dien_giet":
                if not self.electricity_off:
                    return False, "Chỉ có thể giết sau khi đã cắt điện.", []
                last_night = int(caster.cooldowns.get("ke_cat_dien_last_kill_night", -1))
                if self.night_number == last_night:
                    return False, "Kẻ Cắt Điện chỉ được giết 1 lần mỗi đêm.", []
                caster.cooldowns["ke_cat_dien_last_kill_night"] = self.night_number
            if role == RoleType.KE_TU_DAO:
                if self.phase != WerewolfPhase.DAY or self.day_number < 3:
                    return False, "Kẻ Tử Đạo chỉ có thể hiến tế từ ngày 3 trở đi.", []
                target_side = self.side_of(target_id)
                self._kill(target_id, "bị Kẻ Tử Đạo hiến tế")
                self._kill(caster_id, "Kẻ Tử Đạo hiến tế bản thân")
                if target_side == Side.SOI:
                    for pid in self.alive_players:
                        p = self.players[pid]
                        if p.role == RoleType.MUC_SU:
                            p.lives_left += 1
                self.check_win_condition()
                return True, "Đã hiến tế và kết liễu mục tiêu.", []
            if role == RoleType.KE_DANH_BAC:
                charge = int(caster.cooldowns.get("ke_danh_bac_charge", 0))
                if charge < 1:
                    return False, "Bạn chưa có tích lũy để giết.", []
                caster.cooldowns["ke_danh_bac_charge"] = charge - 1
            if role == RoleType.DAO_PHU and self.phase == WerewolfPhase.DAY:
                if caster.cooldowns.get("dao_phu_disabled"):
                    return False, "Đao Phủ đã mất khả năng hành quyết.", []
                if self._count_votes_for_target(target_id) < 1:
                    return False, "Đao Phủ chỉ có thể giết người đang có ít nhất 1 phiếu.", []
            if role == RoleType.NGUOI_VAN_DONG_HANH_LANG and self.phase == WerewolfPhase.DAY:
                charge = int(caster.cooldowns.get("hanh_lang_charge", 0))
                if charge < 1:
                    return False, "Bạn chưa có tích lũy để giết.", []
                caster.cooldowns["hanh_lang_charge"] = charge - 1
                self.vote_locked_players = set(self.day_votes.keys())
            if role == RoleType.THICH_KHACH and self.phase == WerewolfPhase.NIGHT:
                charge = int(caster.cooldowns.get("thich_khach_charge", 1))
                if charge < 1:
                    return False, "Bạn đã hết tích lũy để giết.", []
                caster.cooldowns["thich_khach_charge"] = charge - 1
            if role == RoleType.MA_CA_RONG and self.phase == WerewolfPhase.NIGHT:
                charge = int(caster.cooldowns.get("ma_ca_rong_charge", 0))
                if charge < 1:
                    return False, "Ma Cà Rồng chưa có tích lũy để giết.", []
                caster.cooldowns["ma_ca_rong_charge"] = charge - 1
            if role == RoleType.KE_TAM_LY_YEU and self.phase == WerewolfPhase.NIGHT:
                threshold = max(1, (2 * len(self.players) + 4) // 5)
                if len(self.alive_players) > threshold:
                    return False, "Kẻ Tâm Lý Yếu chưa đủ ổn định để giết vào ban đêm.", []
            if role == RoleType.XA_THU and self.phase == WerewolfPhase.DAY:
                bullets = int(caster.cooldowns.get("xa_thu_bullets", 2))
                if bullets < 1:
                    return False, "Xạ thủ đã hết đạn.", []
                caster.cooldowns["xa_thu_bullets"] = bullets - 1
            if role == RoleType.SOI_CO_DOC and self.phase == WerewolfPhase.NIGHT:
                cooldown_key = "cooldown:soi_co_doc:until_night"
                until_night = int(caster.cooldowns.get(cooldown_key, 0))
                if self.night_number < until_night:
                    return False, "Sói Cô Độc cần nghỉ 1 đêm trước khi giết tiếp.", []
                caster.cooldowns[cooldown_key] = self.night_number + 2
            if role == RoleType.SOI_TU_BAN and chosen_skill.name == "tu_ban":
                ok_spend, _ = self._spend_coins(caster_id, 4)
                if not ok_spend:
                    return False, "Sói Tư Bản cần 4 xu để thêm lượt giết.", []
            if role == RoleType.GIAN_THUONG:
                if self.phase != WerewolfPhase.NIGHT:
                    return False, "Gian Thương chỉ giết bằng xu vào ban đêm.", []
                kills_used = int(caster.cooldowns.get("gian_thuong_kills_used", 0))
                if kills_used >= 3:
                    return False, "Gian Thương đã dùng đủ 3 lượt giết trong đêm.", []
                ok_spend, _ = self._spend_coins(caster_id, 2)
                if not ok_spend:
                    return False, "Bạn không đủ xu để ra giá giết người.", []
                caster.cooldowns["gian_thuong_kills_used"] = kills_used + 1
            if role == RoleType.KE_NOI_HON and chosen_skill.name == "noi_hon_giet":
                if caster.cooldowns.get("ke_noi_hon_kill_used"):
                    return False, "Kẻ Nối Hồn chỉ được giết 1 lần mỗi ván.", []
                caster.cooldowns["ke_noi_hon_kill_used"] = True
            if role == RoleType.KE_PHAN_DON and self.phase == WerewolfPhase.NIGHT:
                cooldown_key = "ke_phan_don_kill_until"
                until_night = int(caster.cooldowns.get(cooldown_key, 0))
                if self.night_number < until_night:
                    return False, "Kẻ Phản Đòn chỉ được giết 1 lần mỗi 2 đêm.", []
                caster.cooldowns[cooldown_key] = self.night_number + 2
            if role == RoleType.LOLICON and self.phase == WerewolfPhase.NIGHT:
                if caster_id not in self.lolicon_enraged:
                    return False, "Lolicon chỉ có thể giết khi đã nổi điên vì Loli chết.", []
            if role == RoleType.CANH_SAT_TRUONG and self.phase == WerewolfPhase.NIGHT:
                self.night_skills[caster_id] = [target_id]
                self.log_event(f"{role.value} {caster_id} xử bắn {target_id} (ban đêm)")
            elif self.phase == WerewolfPhase.DAY:
                self._kill(target_id, f"bị {role.value} kết liễu ban ngày")
                if role == RoleType.MUC_SU and self.side_of(target_id) != Side.SOI:
                    self._kill(caster_id, "Mục sư vẩy nhầm người không phải sói")
                if role == RoleType.DAO_PHU and self.side_of(target_id) == Side.DAN:
                    caster.cooldowns["dao_phu_disabled"] = True
                target_player = self.players.get(target_id)
                if target_player and target_player.role == RoleType.NGUOI_BENH and self.side_of(caster_id) == Side.TRUNG_LAP:
                    caster.cooldowns["night_skill_blocked"] = max(
                        int(caster.cooldowns.get("night_skill_blocked", 0)),
                        1,
                    )
                self.log_event(f"{role.value} {caster_id} kết liễu {target_id} ngay lập tức (ban ngày)")
                self.check_win_condition()
            else:
                self.pending_night_kills[caster_id] = target_id
                if role == RoleType.LOLICON:
                    self.lolicon_enraged.discard(caster_id)
                self.log_event(f"{role.value} {caster_id} chuẩn bị giết {target_id} (ban đêm)")

        if "link_targets" in chosen_skill.effects:
            a, b = target_ids[0], target_ids[1]
            self.players[a].cooldowns.setdefault("linked", set())
            self.players[b].cooldowns.setdefault("linked", set())
            linked_a = self.players[a].cooldowns["linked"]
            linked_b = self.players[b].cooldowns["linked"]
            if isinstance(linked_a, set) and isinstance(linked_b, set):
                linked_a.add(b)
                linked_b.add(a)
            self.log_event(f"{role.value} nối hồn {a} <-> {b}")

        if not chosen_skill.effects:
            return False, "Kỹ năng chưa có hiệu ứng được hỗ trợ.", []
        return True, "Đã ghi nhận kỹ năng.", private_messages

    def _resolve_wolf_target(self) -> Optional[int]:
        if not self.wolf_votes:
            return None
        counter: Dict[int, int] = {}
        for target_id in self.wolf_votes.values():
            counter[target_id] = counter.get(target_id, 0) + 1
        top = max(counter.values())
        winners = [pid for pid, count in counter.items() if count == top]
        if len(winners) > 1:
            return None
        return winners[0]

    def end_day(self) -> dict:
        if self.phase != WerewolfPhase.DAY:
            return {"ok": False, "message": "Không ở pha ban ngày."}

        for judge_id, target_id in list(self.tham_phan_targets.items()):
            judge = self.players.get(judge_id)
            target = self.players.get(target_id)
            if judge and judge.is_alive and target and target.is_alive:
                if judge_id not in self.day_vote_order:
                    self.day_vote_order.append(judge_id)
                self.day_votes[judge_id] = target_id

        alive_voters = [pid for pid in self.alive_players]
        counter: Dict[Optional[int], int] = {}
        for voter_id in alive_voters:
            vote = self.day_votes.get(voter_id)
            counter[vote] = counter.get(vote, 0) + 1
        if self.day_vote_order:
            first_voter_id = self.day_vote_order[0]
            first_voter = self.players.get(first_voter_id)
            if first_voter and first_voter.role == RoleType.NGUOI_TIEN_PHONG:
                first_vote = self.day_votes.get(first_voter_id)
                if first_vote is not None and self.players.get(first_vote) and self.players[first_vote].is_alive:
                    counter[first_vote] = counter.get(first_vote, 0) + 1
        for target_id, bonus in self.vote_bonus.items():
            if target_id in self.players and self.players[target_id].is_alive:
                counter[target_id] = counter.get(target_id, 0) + bonus
        for target_id, bonus in self.next_day_vote_bonus.items():
            if target_id in self.players and self.players[target_id].is_alive:
                counter[target_id] = counter.get(target_id, 0) + bonus
        if (
            self.soi_hac_am_target is not None
            and self.soi_hac_am_target in self.players
            and self.players[self.soi_hac_am_target].is_alive
        ):
            current_votes = counter.get(self.soi_hac_am_target, 0)
            counter[self.soi_hac_am_target] = current_votes * 2

        spy_messages: Dict[int, str] = {}
        for voter_id in alive_voters:
            voter = self.players[voter_id]
            if voter.role != RoleType.SOI_GIAN_DIEP:
                continue
            target_id = self.day_votes.get(voter_id)
            if target_id is None:
                continue
            if counter.get(target_id, 0) == 1:
                target = self.players.get(target_id)
                if target and target.role:
                    spy_messages[voter_id] = (
                        f"Sói Gián Điệp: mục tiêu {target_id} có vai trò **{target.role.value}**."
                    )

        executed: Optional[int] = None
        skip_votes = counter.get(None, 0)
        skip_threshold = max(1, len(self.alive_players) // 4)
        if self.day_skip_forced and skip_votes > skip_threshold:
            for pid in self.alive_players:
                p = self.players[pid]
                if p.role == RoleType.SOI_GIAN_LAN and int(p.cooldowns.get("soi_gian_lan_uses_left", 0)) > 0:
                    p.cooldowns["soi_gian_lan_uses_left"] = int(p.cooldowns.get("soi_gian_lan_uses_left", 0)) - 1
                    break
        elif counter:
            top_votes = max(counter.values())
            top_targets = [target for target, c in counter.items() if c == top_votes]
            if len(top_targets) == 1 and top_targets[0] is not None:
                executed = top_targets[0]
                target_player = self.players.get(executed)
                if target_player and target_player.role == RoleType.LOLI and not target_player.cooldowns.get("loli_saved_once"):
                    target_player.cooldowns["loli_saved_once"] = True
                    executed = None
                else:
                    voters_for_target = [pid for pid, vote in self.day_votes.items() if vote == top_targets[0]]
                    self._kill(top_targets[0], "bị treo cổ")
                    if (
                        target_player
                        and target_player.role == RoleType.KE_DIEU_HUONG_DU_LUAN
                        and not target_player.cooldowns.get("du_luan_used")
                    ):
                        target_player.cooldowns["du_luan_used"] = True
                        second = sorted(
                            [t for t in counter.keys() if t is not None and t != top_targets[0]],
                            key=lambda t: counter.get(t, 0),
                            reverse=True,
                        )
                        if second and counter.get(second[0], 0) > 0:
                            self._kill(second[0], "bị kéo chết bởi Kẻ Điều Hướng Dư Luận")
                    if target_player and target_player.role == RoleType.SOI_CAM_TU and voters_for_target:
                        self._kill(voters_for_target[0], "chết theo Sói Cảm Tử")
        self.prev_day_voted_targets = {vote for vote in self.day_votes.values() if vote is not None}
        if executed is not None:
            for pid in self.alive_players:
                p = self.players[pid]
                if p.role == RoleType.KE_GHI_HAN and self.side_of(executed) == Side.DAN:
                    p.cooldowns["ghi_han_charge"] = int(p.cooldowns.get("ghi_han_charge", 0)) + 1
            for crow_id, marked_id in list(self.con_qua_marked_target.items()):
                if marked_id == executed and self.players.get(crow_id) and self.players[crow_id].is_alive:
                    self.con_qua_kill_ready.add(crow_id)
            self.con_qua_marked_target.clear()

        day_skill_deaths: List[int] = []

        deaths_by_delay: List[int] = []
        for pid in self.alive_players:
            player = self.players[pid]
            if player.pending_death_day is not None and player.pending_death_day <= self.day_number:
                deaths_by_delay.append(pid)
        for pid in deaths_by_delay:
            self._kill(pid, "vết thương từ Kẻ hấp hối phát tác")

        base_threshold = max(1, (len(self.players) + 4) // 5)
        for pid, player in self.players.items():
            received_votes = counter.get(pid, 0)
            if player.role == RoleType.NGUOI_VAN_DONG_HANH_LANG:
                gain = received_votes // base_threshold
                if gain > 0:
                    player.cooldowns["hanh_lang_charge"] = int(player.cooldowns.get("hanh_lang_charge", 0)) + gain
            if player.role == RoleType.THICH_KHACH:
                gain = received_votes // 2
                if gain > 0:
                    player.cooldowns["thich_khach_charge"] = int(player.cooldowns.get("thich_khach_charge", 1)) + gain
            if player.role == RoleType.MA_CA_RONG and received_votes == 0:
                player.cooldowns["ma_ca_rong_charge"] = int(player.cooldowns.get("ma_ca_rong_charge", 0)) + 1

        villager_messages = self._collect_villager_announcements()
        for pid in self.alive_players:
            p = self.players[pid]
            if p.role == RoleType.KE_HOI_LO:
                before = int(p.cooldowns.get("coins", 0))
                after = min(2, before + 1)
                p.cooldowns["coins"] = after
                self.daily_villager_coin_income += max(0, after - before)
        merchant_income = self.daily_villager_coin_income // 2
        if merchant_income > 0:
            for pid in self.alive_players:
                p = self.players[pid]
                if p.role == RoleType.GIAN_THUONG:
                    p.cooldowns["coins"] = int(p.cooldowns.get("coins", 0)) + merchant_income
        if self.daily_coin_spent_by_others > 0:
            alive_tu_ban = [pid for pid in self.alive_players if self.players[pid].role == RoleType.SOI_TU_BAN]
            if alive_tu_ban:
                rebate = self.daily_coin_spent_by_others // 2
                per = rebate // len(alive_tu_ban)
                extra = rebate % len(alive_tu_ban)
                for idx, pid in enumerate(alive_tu_ban):
                    add = per + (1 if idx < extra else 0)
                    self.players[pid].cooldowns["coins"] = int(self.players[pid].cooldowns.get("coins", 0)) + add
        self.soi_hac_am_target = None
        self.soi_hac_am_hide_votes = False
        self.daily_coin_spent_by_others = 0
        self.daily_villager_coin_income = 0

        self.day_votes.clear()
        self.day_vote_order.clear()
        self.vote_locked_players.clear()
        self.jailed_players_today.clear()
        self.tham_phan_targets.clear()
        self.chan_don_redirect.clear()
        self.night_skills.clear()
        self.wolf_votes.clear()
        self.vote_bonus.clear()
        self.next_day_vote_bonus.clear()
        self.day_vote_immune_targets.clear()
        self.day_skip_forced = False
        self.ke_tang_hinh_day_chatters.clear()
        self.ke_tang_hinh_day_killed.clear()
        self.bomb_passed_this_night = False
        for pid in self.alive_players:
            p = self.players[pid]
            if p.role == RoleType.GIAN_THUONG:
                p.cooldowns["gian_thuong_kills_used"] = 0
        self.phase = WerewolfPhase.NIGHT
        self.night_number += 1
        winner = self.check_win_condition()

        return {
            "ok": True,
            "executed": executed,
            "day_skill_deaths": sorted(list(set(day_skill_deaths))),
            "deaths_by_delay": deaths_by_delay,
            "spy_messages": spy_messages,
            "villager_messages": villager_messages,
            "winner": winner.value if winner else None,
        }

    def end_night(self) -> dict:
        if self.phase != WerewolfPhase.NIGHT:
            return {"ok": False, "message": "Không ở pha ban đêm."}

        private_messages: Dict[int, List[str]] = {}

        guard_targets: Dict[int, List[int]] = {}
        sheriff_actions: Dict[int, int] = {}
        ordered_casters = sorted(
            self.night_skills.keys(),
            key=lambda pid: self._role_priority(pid),
            reverse=True,
        )
        for caster_id in ordered_casters:
            targets = self.night_skills[caster_id]
            caster = self.players.get(caster_id)
            if not caster or not caster.is_alive or not caster.role:
                continue
            role_def = self.ROLE_DEFINITIONS.get(caster.role)
            if role_def and role_def.protect_capable and targets:
                guard_targets[caster_id] = targets[:]
            if caster.role == RoleType.CANH_SAT_TRUONG:
                sheriff_actions[caster_id] = targets[0]

        def consume_night_protection(target_id: int) -> bool:
            protected_by = [pid for pid, target_ids in guard_targets.items() if target_id in target_ids]
            if not protected_by:
                return False
            protected = False
            for protector_id in protected_by:
                protector = self.players.get(protector_id)
                if not protector or not protector.is_alive or not protector.role:
                    continue
                if target_id in self.soi_dat_bay_targets:
                    protector.lives_left -= 1
                    if protector.lives_left <= 0:
                        self._kill(protector_id, "mất mạng vì dẫm bẫy Sói Đặt Bẫy")
                        deaths.append(protector_id)
                if protector.role == RoleType.BAO_VE:
                    protector.lives_left -= 1
                    protected = True
                    if protector.lives_left <= 0:
                        self._kill(protector_id, "Bảo vệ cạn mạng khi đỡ đòn")
                        deaths.append(protector_id)
                elif protector.role == RoleType.SOI_CO_KHIEN:
                    shields = int(protector.cooldowns.get("soi_co_khien_shields", 1))
                    if shields > 0 and self.side_of(target_id) == Side.SOI:
                        protector.cooldowns["soi_co_khien_shields"] = shields - 1
                        protected = True
                else:
                    protected = True
            if protected:
                self.log_event(f"Mục tiêu {target_id} được bảo vệ khỏi đòn tấn công ban đêm")
            return protected

        wolf_target = None if self.wolf_bite_block_nights > 0 else self._resolve_wolf_target()
        deaths: List[int] = []
        wolf_side_kill_happened = False
        if wolf_target is not None:
            redirected = self._redirect_targets_for_simp(-1, [wolf_target])
            if redirected:
                wolf_target = redirected[0]
        if self.chan_don_tank_wolf is not None and self.players.get(self.chan_don_tank_wolf):
            tanker = self.players[self.chan_don_tank_wolf]
            if tanker.is_alive:
                wolf_target = self.chan_don_tank_wolf
        if wolf_target is not None and wolf_target in self.soi_dat_bay_targets:
            self.log_event(f"Sói không thể cắn mục tiêu {wolf_target} vì đang bị đặt bẫy")
            wolf_target = None

        if wolf_target is not None and self.players.get(wolf_target) and self.players[wolf_target].is_alive:
            if consume_night_protection(wolf_target):
                pass
            else:
                target_player = self.players[wolf_target]
                handled_wolf_bite = False
                gay_linked = next(
                    (
                        gay_id
                        for gay_id, partner_id in self.nguoi_gay_partner.items()
                        if partner_id == wolf_target and self.players.get(gay_id) and self.players[gay_id].is_alive
                    ),
                    None,
                )
                if gay_linked is not None:
                    self._kill(wolf_target, "bị sói cắn khi ngủ cùng Người Gay")
                    deaths.append(wolf_target)
                    self._kill(gay_linked, "chết theo người ngủ cùng bị tấn công")
                    deaths.append(gay_linked)
                    if self.players.get(wolf_target) and not self.players[wolf_target].is_alive:
                        wolf_side_kill_happened = True
                    if self.players.get(gay_linked) and not self.players[gay_linked].is_alive:
                        wolf_side_kill_happened = True
                    handled_wolf_bite = True
                elif target_player.role == RoleType.NGUOI_GAY:
                    partner_id = self.nguoi_gay_partner.get(wolf_target)
                    if partner_id and self.players.get(partner_id) and self.side_of(partner_id) != Side.SOI:
                        self.log_event(f"Người Gay {wolf_target} sống sót khi bị sói tấn công")
                        handled_wolf_bite = True
                if not handled_wolf_bite and target_player.role == RoleType.KE_HAP_HOI:
                    target_player.pending_death_day = self.day_number + 1
                    attacker_id = next(iter(self.wolf_votes.keys()), None)
                    target_player.last_attacker = attacker_id
                    if attacker_id is not None:
                        private_messages.setdefault(wolf_target, []).append(
                            f"Bạn bị tấn công bởi người chơi {attacker_id} và sẽ chết vào cuối ngày {self.day_number + 1}."
                        )
                    else:
                        private_messages.setdefault(wolf_target, []).append(
                            f"Bạn bị tấn công và sẽ chết vào cuối ngày {self.day_number + 1}."
                        )
                elif not handled_wolf_bite:
                    if target_player.role == RoleType.NGUOI_BENH:
                        self.wolf_bite_block_nights = max(self.wolf_bite_block_nights, 2)
                    if target_player.role == RoleType.NGUOI_BI_TAY_CHAY and self._is_tay_chay_active(wolf_target):
                        self.log_event(f"{wolf_target} miễn nhiễm sói cắn do trạng thái tẩy chay")
                    else:
                        self._kill(wolf_target, "bị sói cắn")
                        deaths.append(wolf_target)
                        if self.players.get(wolf_target) and not self.players[wolf_target].is_alive:
                            wolf_side_kill_happened = True
                        if target_player.role in (RoleType.CANH_SAT_TRUONG, RoleType.NGUOI_VAN_DONG_HANH_LANG):
                            for pid in self.alive_players:
                                p = self.players[pid]
                                if p.role == RoleType.SOI_PHAN_DONG:
                                    p.cooldowns["soi_phan_dong_ready"] = True

        for burn_target in list(self.phong_hoa_burn_targets):
            target = self.players.get(burn_target)
            if target and target.is_alive:
                self._kill(burn_target, "bị thiêu cháy bởi Kẻ Phóng Hỏa")
                deaths.append(burn_target)
        self.phong_hoa_burn_targets.clear()

        has_soi_tich_luy = any(
            self.players[pid].is_alive and self.players[pid].role == RoleType.SOI_TICH_LUY
            for pid in self.players
        )
        if self.wolf_extra_kill_charges > 0 and has_soi_tich_luy:
            ranked_targets: Dict[int, int] = {}
            for voted_target in self.wolf_votes.values():
                if voted_target in self.players and self.players[voted_target].is_alive:
                    ranked_targets[voted_target] = ranked_targets.get(voted_target, 0) + 1
            bonus_target = None
            if ranked_targets:
                bonus_target = sorted(
                    ranked_targets.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )[0][0]
            if bonus_target is not None and self.players.get(bonus_target) and self.players[bonus_target].is_alive:
                self._kill(bonus_target, "bị phe Sói kết liễu từ tích lũy")
                deaths.append(bonus_target)
                if self.players.get(bonus_target) and not self.players[bonus_target].is_alive:
                    wolf_side_kill_happened = True
            self.wolf_extra_kill_charges -= 1

        kill_actions: List[tuple[int, int, int, bool]] = []
        for sheriff_id, target_id in sheriff_actions.items():
            kill_actions.append((self._role_priority(sheriff_id), sheriff_id, target_id, False))
        for killer_id, target_id in list(self.pending_night_kills.items()):
            pierce = killer_id in self.soi_goku_pierce_attackers
            kill_actions.append((self._role_priority(killer_id), killer_id, target_id, pierce))
        kill_actions.sort(key=lambda item: item[0], reverse=True)

        for _, killer_id, target_id, pierce in kill_actions:
            killer = self.players.get(killer_id)
            target = self.players.get(target_id)
            if not killer or not killer.is_alive or not target or not target.is_alive:
                continue
            if consume_night_protection(target_id) and not pierce:
                continue
            if self.wolf_barrier_active and self.side_of(target_id) == Side.SOI:
                self.log_event(f"Kết giới chặn đòn giết vào sói {target_id}")
                continue
            self._kill(target_id, f"bị {killer.role.value} kết liễu ban đêm")
            deaths.append(target_id)
            if self.side_of(killer_id) == Side.SOI and self.players.get(target_id) and not self.players[target_id].is_alive:
                wolf_side_kill_happened = True
            if (
                killer.role
                and self.ROLE_DEFINITIONS[killer.role].side == Side.SOI
                and target.role in (RoleType.CANH_SAT_TRUONG, RoleType.NGUOI_VAN_DONG_HANH_LANG)
            ):
                for pid in self.alive_players:
                    p = self.players[pid]
                    if p.role == RoleType.SOI_PHAN_DONG:
                        p.cooldowns["soi_phan_dong_ready"] = True
            for yid, y_target in list(self.yandere_target.items()):
                if y_target == target_id and self.players.get(yid) and self.players[yid].is_alive:
                    if killer_id != yid and killer.is_alive:
                        self._kill(killer_id, "chết theo mục tiêu của Yandere")
                        deaths.append(killer_id)
                    self._kill(yid, "Yandere chết theo mục tiêu đã bị giết")
                    deaths.append(yid)
            if target.role == RoleType.NGUOI_BENH and self.side_of(killer_id) == Side.TRUNG_LAP:
                killer.cooldowns["night_skill_blocked"] = max(
                    int(killer.cooldowns.get("night_skill_blocked", 0)),
                    2,
                )
            if killer.role == RoleType.CANH_SAT_TRUONG and self.side_of(target_id) == Side.DAN:
                self._kill(killer_id, "Cảnh sát trưởng bắn nhầm dân")
                deaths.append(killer_id)

        if has_soi_tich_luy and not wolf_side_kill_happened:
            self.wolf_extra_kill_charges += 2

        night_awake = set(self.wolf_votes.keys()) | set(self.night_skills.keys()) | set(self.pending_night_kills.keys())
        night_killers = set(self.wolf_votes.keys()) | {k for _, k, _, _ in kill_actions}
        for watcher_id, watched_id in list(self.night_wake_watch.items()):
            if watcher_id in self.alive_players:
                private_messages.setdefault(watcher_id, []).append(
                    f"Theo dõi {watched_id}: {'có thức dậy ban đêm' if watched_id in night_awake else 'không có hoạt động đêm'}."
                )
        for watcher_id, pair in list(self.night_killer_watch.items()):
            if watcher_id in self.alive_players:
                a, b = pair
                detected = (a in night_killers) or (b in night_killers)
                private_messages.setdefault(watcher_id, []).append(
                    f"Ngoại cảm ({a}, {b}): {'có ít nhất một người đã giết ai đó đêm qua' if detected else 'không ai trong cặp giết người đêm qua'}."
                )
        self.pending_night_kills.clear()
        self.soi_goku_pierce_attackers.clear()

        due_bombs = [
            target_id
            for target_id, explode_night in list(self.ke_dat_bom_placements.items())
            if self.night_number >= explode_night
        ]
        for target_id in due_bombs:
            if self.players.get(target_id) and self.players[target_id].is_alive:
                self._kill(target_id, "bom của Kẻ Đặt Bom phát nổ")
                deaths.append(target_id)
            self.ke_dat_bom_placements.pop(target_id, None)

        if self.night_number + 1 == 4:
            for pid, marks in self.ke_da_nghi_marks.items():
                player = self.players.get(pid)
                if not player or not player.is_alive:
                    continue
                if pid in self.ke_da_nghi_opt_out:
                    private_messages.setdefault(pid, []).append("Bạn đã từ chối tiết lộ vai trò từ Kẻ Đa Nghi.")
                    continue
                lines = []
                has_wolf = False
                for target_id in marks:
                    role = self.players[target_id].role if self.players.get(target_id) else None
                    if role and self.ROLE_DEFINITIONS[role].side == Side.SOI:
                        has_wolf = True
                    lines.append(f"{target_id}: **{role.value if role else 'không rõ'}**")
                if lines:
                    private_messages.setdefault(pid, []).append("Kẻ Đa Nghi nhận kết quả: " + ", ".join(lines))
                if marks and not has_wolf:
                    self._kill(pid, "Kẻ Đa Nghi chết vì không đánh dấu trúng sói")
                    deaths.append(pid)

        if self.bomb_holder_id is not None and not self.bomb_passed_this_night:
            holder = self.players.get(self.bomb_holder_id)
            if holder and holder.is_alive:
                self._kill(self.bomb_holder_id, "chết vì không chuyển bom trong đêm")
                deaths.append(self.bomb_holder_id)
            self.bomb_holder_id = None

        if self.bomb_holder_id is not None and self.night_number + 1 >= 5:
            holder = self.players.get(self.bomb_holder_id)
            if holder and holder.is_alive:
                self._kill(self.bomb_holder_id, "bom phát nổ đêm 5")
                deaths.append(self.bomb_holder_id)
            self.bomb_holder_id = None

        for pid in list(self.alive_players):
            p = self.players[pid]
            if p.role == RoleType.MEO_BEO:
                p.lives_left -= 1
                if p.lives_left <= 0:
                    self._kill(pid, "Mèo Béo cạn mạng theo thời gian")
                    deaths.append(pid)

        unique_deaths = set(deaths)
        for pid, prediction in list(self.ke_danh_bac_predictions.items()):
            guessed_count, guess_night = prediction
            if guess_night != self.night_number:
                continue
            if self.players.get(pid):
                if guessed_count == len(unique_deaths):
                    self.players[pid].cooldowns["ke_danh_bac_charge"] = (
                        int(self.players[pid].cooldowns.get("ke_danh_bac_charge", 0)) + guessed_count
                    )
            self.ke_danh_bac_predictions.pop(pid, None)

        for pid, bet in list(self.ke_nghien_co_bac_bets.items()):
            stake, targets, bet_night = bet
            if bet_night != self.night_number:
                continue
            if any(t in unique_deaths for t in targets):
                player = self.players.get(pid)
                if player:
                    player.cooldowns["coins"] = int(player.cooldowns.get("coins", 0)) + stake * 2
            self.ke_nghien_co_bac_bets.pop(pid, None)

        merchant_bonus = len(unique_deaths) // 3
        if merchant_bonus > 0:
            for pid in self.alive_players:
                p = self.players[pid]
                if p.role == RoleType.GIAN_THUONG:
                    p.cooldowns["coins"] = int(p.cooldowns.get("coins", 0)) + merchant_bonus

        villager_messages = self._collect_villager_announcements()
        for uid, lines in villager_messages.items():
            private_messages.setdefault(uid, []).extend(lines)

        self.night_skills.clear()
        self.night_blocked_players.clear()
        self.soi_dat_bay_targets.clear()
        self.chan_don_tank_wolf = None
        self.wolf_barrier_active = False
        if self.wolf_bite_block_nights > 0:
            self.wolf_bite_block_nights -= 1
        for pid in self.players:
            p = self.players[pid]
            blocked = int(p.cooldowns.get("night_skill_blocked", 0))
            if blocked > 0:
                p.cooldowns["night_skill_blocked"] = blocked - 1
        self.wolf_curse_targets.clear()
        self.night_wake_watch.clear()
        self.night_killer_watch.clear()
        self.jailed_players_today = set(self.jailed_players_next_day)
        self.jailed_players_next_day.clear()
        self.wolf_votes.clear()
        self.phase = WerewolfPhase.DAY
        self.day_number += 1
        winner = self.check_win_condition()

        return {
            "ok": True,
            "deaths": sorted(list(set(deaths))),
            "private_messages": private_messages,
            "winner": winner.value if winner else None,
        }

    def pass_bomb(self, user_id: int, target_id: int) -> tuple[bool, str]:
        if self.phase != WerewolfPhase.NIGHT:
            return False, "Chỉ trao bom vào ban đêm."
        user = self.players.get(user_id)
        target = self.players.get(target_id)
        if not user or not user.is_alive or not target or not target.is_alive:
            return False, "Người chơi không hợp lệ."
        if user_id == target_id:
            return False, "Không thể tự trao bom."
        if self.bomb_holder_id is not None and self.bomb_holder_id != user_id:
            return False, "Bạn không cầm bom."
        if user.role != RoleType.NGUOI_CAM_BOM and self.bomb_holder_id is None:
            return False, "Chỉ Người Cầm Bom mới được bắt đầu cơ chế bom."

        self.bomb_holder_id = target_id
        self.bomb_passed_this_night = True
        self.log_event(f"Bomb transferred: {user_id} -> {target_id}")
        if self.side_of(target_id) == Side.SOI:
            self._kill(target_id, "trúng bom khi nhận bom")
            self.bomb_holder_id = None
            return True, "Bom đã nổ khi tới tay sói."
        return True, "Đã trao bom."

    def detective_coin_vote(self, user_id: int, target_id: int) -> tuple[bool, str]:
        if self.phase != WerewolfPhase.DAY:
            return False, "Chỉ dùng xu vote vào ban ngày."
        player = self.players.get(user_id)
        target = self.players.get(target_id)
        if not player or not player.is_alive or not target or not target.is_alive:
            return False, "Người chơi không hợp lệ."
        if player.role != RoleType.THAM_TU_TU:
            return False, "Chỉ Thám tử tư mới dùng được lệnh này."
        if self.detective_coins.get(user_id, 0) <= 0:
            return False, "Bạn không đủ xu."

        self.detective_coins[user_id] -= 1
        self.vote_bonus[target_id] = self.vote_bonus.get(target_id, 0) + 1
        self.log_event(f"Detective coin vote: {user_id} -> {target_id}")
        return True, "Đã dùng xu để cộng thêm 1 phiếu."

    def transfer_coins(self, user_id: int, target_id: int, amount: int) -> tuple[bool, str]:
        giver = self.players.get(user_id)
        receiver = self.players.get(target_id)
        if not giver or not receiver:
            return False, "Người chơi không hợp lệ."
        if amount <= 0:
            return False, "Số xu phải lớn hơn 0."
        if user_id == target_id:
            return False, "Không thể tự chuyển xu."
        if giver.role not in (RoleType.KE_HOI_LO, RoleType.KE_NGHIEN_CO_BAC):
            return False, "Role này không thể chuyển xu."
        if giver.role != RoleType.KE_NGHIEN_CO_BAC and not giver.is_alive:
            return False, "Bạn phải còn sống để chuyển xu."
        current = int(giver.cooldowns.get("coins", 0))
        if current < amount:
            return False, "Bạn không đủ xu."
        giver.cooldowns["coins"] = current - amount
        receiver.cooldowns["coins"] = int(receiver.cooldowns.get("coins", 0)) + amount
        return True, f"Đã chuyển {amount} xu cho {target_id}."

    def mark_day_chat(self, user_id: int) -> tuple[bool, str]:
        player = self.players.get(user_id)
        if not player or not player.is_alive:
            return False, "Bạn không hợp lệ."
        self.ke_tang_hinh_day_chatters.add(user_id)
        return True, "Đã ghi nhận chat ban ngày."

    def special_role_kill(self, user_id: int, target_id: int) -> tuple[bool, str]:
        player = self.players.get(user_id)
        target = self.players.get(target_id)
        if not player or not player.is_alive or not target or not target.is_alive:
            return False, "Người chơi không hợp lệ."
        special_roles = {
            RoleType.KE_PHONG_HOA,
            RoleType.KE_DANH_BAC,
            RoleType.KE_NOI_HON,
        }
        if player.role not in special_roles:
            return False, "Role của bạn không thuộc nhóm dùng lệnh giết chung."
        if user_id == target_id:
            return False, "Không thể tự giết bản thân."
        if self.phase == WerewolfPhase.NIGHT and int(player.cooldowns.get("night_skill_blocked", 0)) > 0:
            return False, "Bạn đang bị mất kỹ năng trong đêm này."

        if self.phase == WerewolfPhase.DAY:
            self._kill(target_id, f"bị {player.role.value} kết liễu ban ngày")
            if target.role == RoleType.NGUOI_BENH and self.side_of(user_id) == Side.TRUNG_LAP:
                player.cooldowns["night_skill_blocked"] = max(
                    int(player.cooldowns.get("night_skill_blocked", 0)),
                    1,
                )
            self.log_event(f"Special role kill: {user_id} -> {target_id} (ban ngày, tức thì)")
            self.check_win_condition()
            return True, "Đã xử lý lệnh giết đặc biệt ngay lập tức."
        elif self.phase == WerewolfPhase.NIGHT:
            self.pending_night_kills[user_id] = target_id
        else:
            return False, "Không thể giết ở phase hiện tại."
        self.log_event(f"Special role kill queued: {user_id} -> {target_id}")
        return True, "Đã ghi nhận lệnh giết đặc biệt."

    def reveal_wolf_shield(self, user_id: int) -> tuple[bool, str]:
        player = self.players.get(user_id)
        if not player or not player.is_alive:
            return False, "Bạn không hợp lệ."
        if player.role != RoleType.SOI_CO_KHIEN:
            return False, "Chỉ Sói Có Khiên mới dùng được lệnh này."
        if self.phase != WerewolfPhase.DAY:
            return False, "Chỉ công khai khiên vào ban ngày."

        self.day_vote_immune_targets.add(user_id)
        player.cooldowns["soi_co_khien_shields"] = int(player.cooldowns.get("soi_co_khien_shields", 0)) + 1
        self.log_event(f"Wolf shield revealed: {user_id}")
        return True, "Bạn đã công khai khiên và miễn nhiễm vote trong ngày hiện tại."

    def add_wolf_chat(self, user_id: int, message: str) -> tuple[bool, str]:
        player = self.players.get(user_id)
        if not player or not player.is_alive or self.side_of(user_id) != Side.SOI:
            return False, "Chỉ sói còn sống mới được chat sói."
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {user_id}: {message}"
        self.wolf_chat_log.append(line)
        self.log_event(f"Chat sói: {line}")
        return True, "Đã gửi chat sói."

    def read_wolf_chat(self, page: int = 1, page_size: int = 10) -> tuple[List[str], int]:
        if page < 1:
            page = 1
        total_pages = max(1, (len(self.wolf_chat_log) + page_size - 1) // page_size)
        page = min(page, total_pages)
        start = (page - 1) * page_size
        end = start + page_size
        return self.wolf_chat_log[start:end], total_pages

    def get_role_catalog(self) -> List[RoleDefinition]:
        return list(self.ROLE_DEFINITIONS.values())

    def get_role_accuracy_report(self) -> Dict[RoleType, str]:
        report: Dict[RoleType, str] = {}
        for role, spec in ROLE_SPECS.items():
            if spec.implementation_level != "exact":
                report[role] = spec.implementation_note or "Logic mới ở mức triển khai một phần."
        return report
