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
            role_defs[role] = RoleDefinition(
                role=role,
                side=spec.side,
                number_of_skill_cast=max(1, len(spec.skills)) if spec.skills else 0,
                priority=20 if spec.side == Side.DAN else 15 if spec.side == Side.SOI else 12,
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
        self.night_skills: Dict[int, List[int]] = {}
        self.pending_day_kills: Dict[int, int] = {}
        self.pending_night_kills: Dict[int, int] = {}
        self.vote_bonus: Dict[int, int] = {}
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
        player.is_alive = False
        self.log_event(f"Player {user_id} chết ({reason})")

        linked = player.cooldowns.get("linked")
        if isinstance(linked, set):
            for linked_id in list(linked):
                linked_player = self.players.get(linked_id)
                if linked_player and linked_player.is_alive:
                    self._kill(linked_id, f"chết dây chuyền từ liên kết với {user_id}")

    def check_win_condition(self) -> Optional[Side]:
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
        if target_id is not None:
            target = self.players.get(target_id)
            if not target or not target.is_alive:
                return False, "Mục tiêu không hợp lệ."
        self.day_votes[voter_id] = target_id
        voter.voted = target_id
        self.log_event(f"Vote ngày: {voter_id} -> {target_id if target_id else 'SKIP'}")
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
        if not caster or not caster.is_alive or not caster.role:
            return False, "Bạn không thể dùng kỹ năng.", []
        role = caster.role
        spec: Optional[RoleSpec] = ROLE_SPECS.get(role)
        if not spec or not spec.skills:
            return False, "Role này chưa có kỹ năng chủ động.", []

        chosen_skill = None
        if skill_name:
            for skill in spec.skills:
                if skill.name == skill_name:
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

        if len(targets) != chosen_skill.target_count:
            return False, f"Kỹ năng này cần đúng {chosen_skill.target_count} mục tiêu.", []

        target_ids = targets
        for target_id in target_ids:
            target = self.players.get(target_id)
            if not target or not target.is_alive:
                return False, "Mục tiêu không hợp lệ.", []
            if not spec.can_target_self and target_id == caster_id:
                return False, "Không thể tự nhắm mục tiêu.", []

        private_messages: List[str] = []

        if "protect_target" in chosen_skill.effects:
            self.night_skills[caster_id] = target_ids[:]
            self.log_event(f"{role.value} {caster_id} bảo vệ {target_ids}")

        if "info_role" in chosen_skill.effects:
            if chosen_skill.target_count == 1:
                target = self.players[target_ids[0]]
                role_name = target.role.value if target.role else "chưa rõ"
                private_messages.append(f"Vai trò của {target_ids[0]}: **{role_name}**")
            else:
                lines = []
                for target_id in target_ids:
                    target = self.players[target_id]
                    role_name = target.role.value if target.role else "chưa rõ"
                    lines.append(f"{target_id}: **{role_name}**")
                private_messages.append("Thông tin vai trò: " + ", ".join(lines))

        if "info_side" in chosen_skill.effects:
            lines = []
            for target_id in target_ids:
                side = self.side_of(target_id)
                lines.append(f"{target_id}: **{side.value if side else 'không rõ'}**")
            private_messages.append("Thông tin phe: " + ", ".join(lines))

        if "compare_side" in chosen_skill.effects:
            left, right = target_ids[0], target_ids[1]
            same_side = self.side_of(left) == self.side_of(right)
            private_messages.append(
                f"So sánh phe {left} và {right}: {'cùng phe' if same_side else 'khác phe'}."
            )

        if "vote_bonus" in chosen_skill.effects:
            target_id = target_ids[0]
            self.vote_bonus[target_id] = self.vote_bonus.get(target_id, 0) + chosen_skill.vote_bonus
            self.log_event(
                f"{role.value} {caster_id} cộng {chosen_skill.vote_bonus} phiếu cho {target_id}"
            )

        if "kill_target" in chosen_skill.effects:
            target_id = target_ids[0]
            if role == RoleType.CANH_SAT_TRUONG and self.phase == WerewolfPhase.NIGHT:
                self.night_skills[caster_id] = [target_id]
                self.log_event(f"{role.value} {caster_id} xử bắn {target_id} (ban đêm)")
            elif self.phase == WerewolfPhase.DAY:
                self.pending_day_kills[caster_id] = target_id
                self.log_event(f"{role.value} {caster_id} chuẩn bị giết {target_id} (ban ngày)")
            else:
                self.pending_night_kills[caster_id] = target_id
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

        alive_voters = [pid for pid in self.alive_players]
        counter: Dict[Optional[int], int] = {}
        for voter_id in alive_voters:
            vote = self.day_votes.get(voter_id)
            counter[vote] = counter.get(vote, 0) + 1
        for target_id, bonus in self.vote_bonus.items():
            if target_id in self.players and self.players[target_id].is_alive:
                counter[target_id] = counter.get(target_id, 0) + bonus

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
        if counter:
            top_votes = max(counter.values())
            top_targets = [target for target, c in counter.items() if c == top_votes]
            if len(top_targets) == 1 and top_targets[0] is not None:
                executed = top_targets[0]
                self._kill(executed, "bị treo cổ")

        day_skill_deaths: List[int] = []
        for killer_id, target_id in list(self.pending_day_kills.items()):
            killer = self.players.get(killer_id)
            target = self.players.get(target_id)
            if not killer or not killer.is_alive or not target or not target.is_alive:
                continue
            self._kill(target_id, f"bị {killer.role.value} kết liễu ban ngày")
            day_skill_deaths.append(target_id)
        self.pending_day_kills.clear()

        deaths_by_delay: List[int] = []
        for pid in self.alive_players:
            player = self.players[pid]
            if player.pending_death_day is not None and player.pending_death_day <= self.day_number:
                deaths_by_delay.append(pid)
        for pid in deaths_by_delay:
            self._kill(pid, "vết thương từ Kẻ hấp hối phát tác")

        self.day_votes.clear()
        self.night_skills.clear()
        self.wolf_votes.clear()
        self.vote_bonus.clear()
        self.phase = WerewolfPhase.NIGHT
        self.night_number += 1
        winner = self.check_win_condition()

        return {
            "ok": True,
            "executed": executed,
            "day_skill_deaths": sorted(list(set(day_skill_deaths))),
            "deaths_by_delay": deaths_by_delay,
            "spy_messages": spy_messages,
            "winner": winner.value if winner else None,
        }

    def end_night(self) -> dict:
        if self.phase != WerewolfPhase.NIGHT:
            return {"ok": False, "message": "Không ở pha ban đêm."}

        private_messages: Dict[int, List[str]] = {}

        guard_targets: Dict[int, int] = {}
        sheriff_actions: Dict[int, int] = {}
        for caster_id, targets in self.night_skills.items():
            caster = self.players.get(caster_id)
            if not caster or not caster.is_alive or not caster.role:
                continue
            role_def = self.ROLE_DEFINITIONS.get(caster.role)
            if role_def and role_def.protect_capable and targets:
                guard_targets[caster_id] = targets[0]
            if caster.role == RoleType.CANH_SAT_TRUONG:
                sheriff_actions[caster_id] = targets[0]

        wolf_target = self._resolve_wolf_target()
        deaths: List[int] = []

        if wolf_target is not None and self.players.get(wolf_target) and self.players[wolf_target].is_alive:
            protected_by = [pid for pid, tid in guard_targets.items() if tid == wolf_target]
            if protected_by:
                for protector_id in protected_by:
                    protector = self.players[protector_id]
                    if protector.role == RoleType.BAO_VE:
                        protector.lives_left -= 1
                        if protector.lives_left <= 0:
                            self._kill(protector_id, "Bảo vệ cạn mạng khi đỡ đòn")
                            deaths.append(protector_id)
            else:
                target_player = self.players[wolf_target]
                if target_player.role == RoleType.KE_HAP_HOI:
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
                else:
                    self._kill(wolf_target, "bị sói cắn")
                    deaths.append(wolf_target)

        for sheriff_id, target_id in sheriff_actions.items():
            sheriff = self.players.get(sheriff_id)
            target = self.players.get(target_id)
            if not sheriff or not sheriff.is_alive or not target or not target.is_alive:
                continue
            self._kill(target_id, "bị Cảnh sát trưởng xử bắn")
            deaths.append(target_id)
            if self.side_of(target_id) == Side.DAN:
                self._kill(sheriff_id, "Cảnh sát trưởng bắn nhầm dân")
                deaths.append(sheriff_id)

        for killer_id, target_id in list(self.pending_night_kills.items()):
            killer = self.players.get(killer_id)
            target = self.players.get(target_id)
            if not killer or not killer.is_alive or not target or not target.is_alive:
                continue
            if killer.role == RoleType.CANH_SAT_TRUONG:
                continue
            self._kill(target_id, f"bị {killer.role.value} kết liễu ban đêm")
            deaths.append(target_id)
        self.pending_night_kills.clear()

        self.night_skills.clear()
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
