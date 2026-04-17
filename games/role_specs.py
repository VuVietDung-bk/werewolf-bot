from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Dict, Optional, Tuple

from enums import RoleType, Side


@dataclass(frozen=True)
class SkillSpec:
    name: str
    phase: str  # day | night | any
    target_count: int
    max_targets: Optional[int] = None
    effects: Tuple[str, ...] = field(default_factory=tuple)
    vote_bonus: int = 1
    usage_limit: Optional[int] = None
    usage_limit_key: Optional[str] = None
    usage_cost_per_target: bool = False
    allowed_target_sides: Optional[Tuple[Side, ...]] = None


@dataclass(frozen=True)
class RoleSpec:
    role: RoleType
    side: Side
    description: str
    skills: Tuple[SkillSpec, ...] = field(default_factory=tuple)
    can_target_self: bool = False
    cooldown: int = 0
    priority: int = 0
    implementation_level: str = "partial"  # exact | partial
    implementation_note: str = ""


def _k(name: str, phase: str = "night", target_count: int = 1) -> SkillSpec:
    return SkillSpec(name=name, phase=phase, target_count=target_count, effects=("kill_target",))


def _i_role(name: str, phase: str = "night", target_count: int = 1) -> SkillSpec:
    return SkillSpec(name=name, phase=phase, target_count=target_count, effects=("info_role",))


def _i_side(name: str, phase: str = "night", target_count: int = 1) -> SkillSpec:
    return SkillSpec(name=name, phase=phase, target_count=target_count, effects=("info_side",))


def _protect(name: str, phase: str = "night", target_count: int = 1) -> SkillSpec:
    return SkillSpec(name=name, phase=phase, target_count=target_count, effects=("protect_target",))


def _vote_bonus(name: str, bonus: int = 1) -> SkillSpec:
    return SkillSpec(
        name=name,
        phase="day",
        target_count=1,
        effects=("vote_bonus",),
        vote_bonus=bonus,
    )


def _revive(name: str, phase: str = "any") -> SkillSpec:
    return SkillSpec(name=name, phase=phase, target_count=1, effects=("revive_target",))


ROLE_SPECS: Dict[RoleType, RoleSpec] = {
    RoleType.DAN_LANG: RoleSpec(RoleType.DAN_LANG, Side.DAN, "Dân làng cơ bản.", implementation_level="exact"),
    RoleType.SOI_THUONG: RoleSpec(RoleType.SOI_THUONG, Side.SOI, "Sói thường.", implementation_level="exact"),
    RoleType.BAO_VE: RoleSpec(
        RoleType.BAO_VE,
        Side.DAN,
        "Bảo vệ ban đêm.",
        (_protect("bao_ke"),),
        can_target_self=True,
        implementation_level="exact",
    ),
    RoleType.KE_HAP_HOI: RoleSpec(
        RoleType.KE_HAP_HOI,
        Side.DAN,
        "Bảo vệ ban đêm, chết trễ khi bị cắn.",
        (_protect("bao_ke"),),
        can_target_self=True,
        implementation_level="exact",
    ),
    RoleType.MUC_SU: RoleSpec(RoleType.MUC_SU, Side.DAN, "Vẩy nước thánh ban ngày.", (_k("vay_nuoc_thanh", phase="day"),)),
    RoleType.TIEN_TRI: RoleSpec(
        RoleType.TIEN_TRI,
        Side.DAN,
        "Soi vai trò ban đêm.",
        (_i_role("soi_role"),),
        implementation_level="exact",
    ),
    RoleType.THAY_BOI: RoleSpec(
        RoleType.THAY_BOI,
        Side.DAN,
        "Soi phe ban đêm.",
        (_i_side("soi_phe"),),
        implementation_level="exact",
    ),
    RoleType.KE_TINH_GIAC_GIUA_DEM: RoleSpec(RoleType.KE_TINH_GIAC_GIUA_DEM, Side.DAN, "Theo dõi một người ban đêm.", (_i_role("theo_doi"),)),
    RoleType.NHA_NGOAI_CAM: RoleSpec(RoleType.NHA_NGOAI_CAM, Side.DAN, "Theo dõi hai người ban đêm.", (_i_role("ngoai_cam", target_count=2),)),
    RoleType.CANH_SAT_TRUONG: RoleSpec(
        RoleType.CANH_SAT_TRUONG,
        Side.DAN,
        "Giết một người ban đêm.",
        (_k("xu_ban"),),
        implementation_level="exact",
    ),
    RoleType.PHAP_SU: RoleSpec(
        RoleType.PHAP_SU,
        Side.DAN,
        "Hồi sinh một lần, kể cả khi đã chết.",
        (
            SkillSpec(
                name="hoi_sinh",
                phase="any",
                target_count=1,
                effects=("revive_target",),
                usage_limit=1,
                usage_limit_key="phap_su_revive_left",
            ),
        ),
        implementation_level="exact",
    ),
    RoleType.KE_BAO_THU: RoleSpec(
        RoleType.KE_BAO_THU,
        Side.DAN,
        "Gắn tâm giao ban đêm, trả thù ban ngày nếu tâm giao chết.",
        (_i_role("tam_giao"), _k("bao_thu", phase="day")),
    ),
    RoleType.XA_THU: RoleSpec(RoleType.XA_THU, Side.DAN, "Bắn ban ngày.", (_k("ban", phase="day"),)),
    RoleType.NHA_BAO: RoleSpec(
        RoleType.NHA_BAO,
        Side.DAN,
        "Biết Người Nổi Tiếng và thống kê phe còn sống ban ngày.",
        (SkillSpec(name="thong_ke", phase="day", target_count=0, effects=("info_counts",)),),
        implementation_level="exact",
    ),
    RoleType.LOLI: RoleSpec(RoleType.LOLI, Side.DAN, "Bị treo cổ có cơ hội sống.", (_i_role("tu_tiet_lo"),)),
    RoleType.NGUOI_BENH: RoleSpec(
        RoleType.NGUOI_BENH,
        Side.DAN,
        "Hiệu ứng phản ứng khi bị tấn công.",
        (_i_side("phan_ung_benh"),),
        implementation_level="exact",
    ),
    RoleType.NGUOI_GAC_DEM: RoleSpec(
        RoleType.NGUOI_GAC_DEM,
        Side.DAN,
        "Bảo vệ tối đa 3 lượt mỗi ván, có thể bảo vệ nhiều người trong một đêm.",
        (
            SkillSpec(
                name="gac_dem",
                phase="night",
                target_count=1,
                max_targets=3,
                effects=("protect_target",),
                usage_limit=3,
                usage_limit_key="nguoi_gac_dem_protect_left",
                usage_cost_per_target=True,
            ),
        ),
        implementation_level="exact",
    ),
    RoleType.KE_HOANG_TUONG: RoleSpec(RoleType.KE_HOANG_TUONG, Side.DAN, "Nhận thông tin có nhiễu.", (_i_role("thong_tin_ngau_nhien"),)),
    RoleType.NGUOI_NOI_TIENG: RoleSpec(
        RoleType.NGUOI_NOI_TIENG,
        Side.DAN,
        "Lộ tin khi chết.",
        (_i_role("lo_tin_khi_chet"),),
        implementation_level="exact",
    ),
    RoleType.NGUOI_BI_TAY_CHAY: RoleSpec(
        RoleType.NGUOI_BI_TAY_CHAY,
        Side.DAN,
        "Miễn soi/cắn ban đêm.",
        (_protect("mien_nhiem_dem"),),
        can_target_self=True,
        implementation_level="exact",
    ),
    RoleType.KE_SONG_SOT: RoleSpec(RoleType.KE_SONG_SOT, Side.DAN, "Điều kiện thắng mở rộng.", (_i_side("kiem_tra_song_sot"),)),
    RoleType.NGUOI_CAM_BOM: RoleSpec(RoleType.NGUOI_CAM_BOM, Side.DAN, "Trao bom mỗi đêm.", (_k("trao_bom"),)),
    RoleType.KE_HOI_LO: RoleSpec(
        RoleType.KE_HOI_LO,
        Side.DAN,
        "Dùng xu lấy thông tin chết gần nhất.",
        (SkillSpec(name="hoi_lo", phase="day", target_count=0, effects=("info_role",)),),
    ),
    RoleType.KE_NGHIEN_CO_BAC: RoleSpec(
        RoleType.KE_NGHIEN_CO_BAC,
        Side.DAN,
        "Cược xu vào tối đa 3 người sẽ chết trong đêm.",
        (SkillSpec(name="cuoc_dem", phase="night", target_count=1, max_targets=3, effects=("info_role",)),),
    ),
    RoleType.KE_DA_NGHI: RoleSpec(
        RoleType.KE_DA_NGHI,
        Side.DAN,
        "Đánh dấu trong 3 đêm đầu, đêm 4 nhận kết quả hoặc có thể từ chối.",
        (
            _i_role("danh_dau"),
            SkillSpec(name="tu_choi_tiet_lo", phase="night", target_count=0, effects=("info_role",)),
        ),
    ),
    RoleType.KE_THAM_DO: RoleSpec(RoleType.KE_THAM_DO, Side.DAN, "Soi role trong nhóm bị vote.", (_i_role("tham_do"),)),
    RoleType.KE_DIEU_HUONG_DU_LUAN: RoleSpec(RoleType.KE_DIEU_HUONG_DU_LUAN, Side.DAN, "Kích hoạt chết dây chuyền khi bị treo.", (_vote_bonus("du_luan"),)),
    RoleType.KE_KE_THUA: RoleSpec(RoleType.KE_KE_THUA, Side.DAN, "Kết hữu để kế thừa role.", (_i_role("ket_huu"),)),
    RoleType.NGUOI_VAN_DONG_HANH_LANG: RoleSpec(RoleType.NGUOI_VAN_DONG_HANH_LANG, Side.DAN, "Giết ban ngày nếu có tích lũy.", (_k("hanh_lang", phase="day"),)),
    RoleType.NGUOI_GAY: RoleSpec(RoleType.NGUOI_GAY, Side.DAN, "Ngủ cùng mục tiêu ban đêm.", (_protect("ngu_cung"),)),
    RoleType.YANDERE: RoleSpec(
        RoleType.YANDERE,
        Side.DAN,
        "Chọn một mục tiêu định mệnh, chết sẽ kéo theo.",
        (_i_role("keo_chet_theo"),),
    ),
    RoleType.MEO_BEO: RoleSpec(RoleType.MEO_BEO, Side.DAN, "9 mạng, soi tốn mạng.", (_i_role("soi_ton_mang"),), can_target_self=True),
    RoleType.KE_TU_DAO: RoleSpec(RoleType.KE_TU_DAO, Side.DAN, "Hiến tế giết 1 người.", (_k("hien_te", phase="day"),)),
    RoleType.THAM_TU_TU: RoleSpec(
        RoleType.THAM_TU_TU,
        Side.DAN,
        "Soi 2 người cùng phe không.",
        (SkillSpec(name="doi_chieu_phe", phase="night", target_count=2, effects=("compare_side",)),),
    ),
    RoleType.THAM_PHAN: RoleSpec(RoleType.THAM_PHAN, Side.DAN, "Đặt bản án ban đêm.", (_vote_bonus("ban_an"),)),
    RoleType.SIMP: RoleSpec(RoleType.SIMP, Side.DAN, "Simp và phản kích.", (_k("phan_simp", phase="day"), _protect("nhan_hieu_ung", phase="any"))),
    RoleType.NGUOI_TIEN_PHONG: RoleSpec(RoleType.NGUOI_TIEN_PHONG, Side.DAN, "Vote đầu tiên x2.", (_vote_bonus("vote_dau_tien", bonus=2),)),
    RoleType.KE_CHAN_DON: RoleSpec(RoleType.KE_CHAN_DON, Side.DAN, "Hút kỹ năng về mình.", (_protect("chan_don"),), can_target_self=True),
    RoleType.KE_GHI_HAN: RoleSpec(RoleType.KE_GHI_HAN, Side.DAN, "Ghi hận và trả đũa.", (_k("tra_thu"),)),
    RoleType.DAO_PHU: RoleSpec(RoleType.DAO_PHU, Side.DAN, "Giết người có vote buổi sáng.", (_k("dao_phu", phase="day"),)),
    RoleType.NGUOI_NHAN_NHIN: RoleSpec(RoleType.NGUOI_NHAN_NHIN, Side.DAN, "2 mạng, đổi hướng vote 1 lần.", (_protect("nhan_vote", phase="day"),), can_target_self=True),
    RoleType.SOI_PHAP_SU: RoleSpec(
        RoleType.SOI_PHAP_SU,
        Side.SOI,
        "Yểm thông tin soi.",
        (_i_side("yem_soi"),),
        implementation_level="exact",
    ),
    RoleType.SOI_GIAN_DIEP: RoleSpec(
        RoleType.SOI_GIAN_DIEP,
        Side.SOI,
        "Đọc role khi vote đơn độc.",
        (_i_role("gian_diep", phase="day"),),
        implementation_level="exact",
    ),
    RoleType.SOI_SAT_THU: RoleSpec(
        RoleType.SOI_SAT_THU,
        Side.SOI,
        "Đoán role để giết (2 lần).",
        (
            SkillSpec(
                name="sat_thu",
                phase="any",
                target_count=1,
                effects=("kill_target",),
                usage_limit=2,
                usage_limit_key="soi_sat_thu_uses_left",
            ),
        ),
    ),
    RoleType.SOI_BANG: RoleSpec(RoleType.SOI_BANG, Side.SOI, "Khóa kỹ năng mục tiêu.", (_protect("dong_bang"),)),
    RoleType.SOI_GOKU: RoleSpec(
        RoleType.SOI_GOKU,
        Side.SOI,
        "Giết xuyên bảo vệ 1 lần mỗi ván.",
        (
            SkillSpec(
                name="kamehameha",
                phase="night",
                target_count=1,
                effects=("kill_target",),
                usage_limit=1,
                usage_limit_key="soi_goku_uses_left",
            ),
        ),
    ),
    RoleType.SOI_HAC_AM: RoleSpec(
        RoleType.SOI_HAC_AM,
        Side.SOI,
        "Nhân đôi số phiếu nhận vào ngày sau (1 lần).",
        (
            SkillSpec(
                name="nhan_doi_vote",
                phase="night",
                target_count=1,
                effects=("vote_bonus",),
                vote_bonus=0,
                usage_limit=1,
                usage_limit_key="soi_hac_am_uses_left",
            ),
        ),
    ),
    RoleType.SOI_TICH_LUY: RoleSpec(RoleType.SOI_TICH_LUY, Side.SOI, "Nội tại tích lũy lượt giết bổ sung cho phe Sói.", ()),
    RoleType.SOI_CUOP_DANH_TINH: RoleSpec(
        RoleType.SOI_CUOP_DANH_TINH,
        Side.SOI,
        "Cướp role hiển thị.",
        (_i_role("cuop_danh_tinh"),),
        implementation_level="exact",
    ),
    RoleType.SOI_MACH_LEO: RoleSpec(
        RoleType.SOI_MACH_LEO,
        Side.SOI,
        "Nhốt mục tiêu mất skill/vote.",
        (SkillSpec(name="mach_leo", phase="night", target_count=1, effects=("protect_target",)),),
    ),
    RoleType.SOI_PHAN_DONG: RoleSpec(RoleType.SOI_PHAN_DONG, Side.SOI, "Thêm lượt giết nếu hạ role đặc biệt.", (_k("phan_dong"),)),
    RoleType.SOI_HO_VE: RoleSpec(RoleType.SOI_HO_VE, Side.SOI, "Cứu khỏi treo cổ 1 lần.", (_protect("ho_ve", phase="day"),), can_target_self=True),
    RoleType.SOI_DAT_BAY: RoleSpec(RoleType.SOI_DAT_BAY, Side.SOI, "Đặt bẫy vào mục tiêu.", (_k("dat_bay"),)),
    RoleType.SOI_CAM_TU: RoleSpec(RoleType.SOI_CAM_TU, Side.SOI, "Bị treo kéo chết theo.", (_k("cam_tu", phase="day"),)),
    RoleType.SOI_GIAN_LAN: RoleSpec(
        RoleType.SOI_GIAN_LAN,
        Side.SOI,
        "Một lần bỏ qua buổi vote nếu skip đủ cao.",
        (
            SkillSpec(
                name="gian_lan",
                phase="day",
                target_count=0,
                effects=("info_side",),
                usage_limit=1,
                usage_limit_key="soi_gian_lan_uses_left",
            ),
        ),
    ),
    RoleType.SOI_CO_KHIEN: RoleSpec(
        RoleType.SOI_CO_KHIEN,
        Side.SOI,
        "Khiên bảo vệ sói.",
        (
            SkillSpec(
                name="khien_soi",
                phase="night",
                target_count=1,
                max_targets=2,
                effects=("protect_target",),
                allowed_target_sides=(Side.SOI,),
            ),
        ),
        can_target_self=True,
    ),
    RoleType.SOI_KET_GIOI: RoleSpec(
        RoleType.SOI_KET_GIOI,
        Side.SOI,
        "Tạo kết giới miễn giết.",
        (
            SkillSpec(
                name="ket_gioi",
                phase="night",
                target_count=1,
                effects=("protect_target",),
                allowed_target_sides=(Side.SOI,),
            ),
        ),
        can_target_self=True,
    ),
    RoleType.SOI_TU_BAN: RoleSpec(
        RoleType.SOI_TU_BAN,
        Side.SOI,
        "Tiêu xu để bảo kê/giết.",
        (
            _k("tu_ban"),
            SkillSpec(
                name="tu_ban_bao_ke",
                phase="night",
                target_count=1,
                effects=("protect_target",),
                allowed_target_sides=(Side.SOI,),
            ),
        ),
    ),
    RoleType.SOI_TINH_BAN: RoleSpec(RoleType.SOI_TINH_BAN, Side.SOI, "Không chết khi còn >2 sói.", (_protect("tinh_ban"),), can_target_self=True),
    RoleType.KE_DAT_BOM: RoleSpec(
        RoleType.KE_DAT_BOM,
        Side.TRUNG_LAP,
        "Đặt bom nổ đêm sau.",
        (SkillSpec(name="dat_bom", phase="night", target_count=1, effects=("kill_target",)),),
    ),
    RoleType.KE_PHONG_HOA: RoleSpec(
        RoleType.KE_PHONG_HOA,
        Side.TRUNG_LAP,
        "Tẩm xăng mục tiêu hoặc châm lửa toàn bộ mục tiêu đã tẩm.",
        (SkillSpec(name="phong_hoa", phase="night", target_count=0, max_targets=2, effects=("kill_target",)),),
    ),
    RoleType.LOLICON: RoleSpec(RoleType.LOLICON, Side.TRUNG_LAP, "Rage kill khi Loli chết.", (_k("lolicon"), _i_role("soi_loli"))),
    RoleType.SOI_CO_DOC: RoleSpec(
        RoleType.SOI_CO_DOC,
        Side.TRUNG_LAP,
        "Giết độc lập mỗi 2 đêm.",
        (_k("soi_co_doc"),),
        cooldown=1,
    ),
    RoleType.KE_NOI_DOI: RoleSpec(RoleType.KE_NOI_DOI, Side.TRUNG_LAP, "Bị treo thắng ngay.", (_i_side("noi_doi"),)),
    RoleType.THICH_KHACH: RoleSpec(RoleType.THICH_KHACH, Side.TRUNG_LAP, "Giết theo tích lũy.", (_k("thich_khach"),)),
    RoleType.CON_QUA: RoleSpec(
        RoleType.CON_QUA,
        Side.TRUNG_LAP,
        "Gắn +2 vote.",
        (SkillSpec(name="con_qua", phase="night", target_count=1, effects=("vote_bonus",), vote_bonus=2),),
    ),
    RoleType.KE_TIM_SU_THAT: RoleSpec(RoleType.KE_TIM_SU_THAT, Side.TRUNG_LAP, "Công khai role đúng để thắng.", (_i_role("tim_su_that", phase="day"),)),
    RoleType.SAT_THU: RoleSpec(RoleType.SAT_THU, Side.TRUNG_LAP, "Đoán role để giết.", (_k("sat_thu", phase="any"),)),
    RoleType.KE_TANG_HINH: RoleSpec(RoleType.KE_TANG_HINH, Side.TRUNG_LAP, "Tàng hình và bắn ban ngày.", (_k("tang_hinh", phase="day"),)),
    RoleType.KE_DANH_BAC: RoleSpec(
        RoleType.KE_DANH_BAC,
        Side.TRUNG_LAP,
        "Đoán số người chết để tích lũy lượt giết.",
        (
            _k("danh_bac"),
            SkillSpec(name="doan_so_nguoi_chet", phase="night", target_count=0, effects=("info_side",)),
        ),
    ),
    RoleType.KE_PHAN_DON: RoleSpec(RoleType.KE_PHAN_DON, Side.TRUNG_LAP, "Phản đòn và giết định kỳ.", (_k("phan_don"), _protect("mien_hieu_ung", phase="any"))),
    RoleType.CAO_BOI: RoleSpec(RoleType.CAO_BOI, Side.TRUNG_LAP, "Đọ súng ban đêm.", (_k("do_sung"),)),
    RoleType.AYANOKOJI: RoleSpec(RoleType.AYANOKOJI, Side.TRUNG_LAP, "Chết theo điều kiện soi/sát thủ.", (_i_role("ayanokoji"),)),
    RoleType.KE_TAM_LY_YEU: RoleSpec(RoleType.KE_TAM_LY_YEU, Side.TRUNG_LAP, "Ban ngày chỉ vote, đủ điều kiện thì giết.", (_k("tam_ly_yeu"),)),
    RoleType.VUA_LI_DON: RoleSpec(RoleType.VUA_LI_DON, Side.TRUNG_LAP, "Chỉ chết do treo cổ.", (_protect("li_don"),), can_target_self=True),
    RoleType.KIM_JONG_UN: RoleSpec(RoleType.KIM_JONG_UN, Side.TRUNG_LAP, "Countdown 2 ngày, nổ tên lửa.", (_k("ten_lua", phase="day"),)),
    RoleType.GIAN_THUONG: RoleSpec(RoleType.GIAN_THUONG, Side.TRUNG_LAP, "Dùng xu để giết.", (_k("gian_thuong"),)),
    RoleType.MA_CA_RONG: RoleSpec(RoleType.MA_CA_RONG, Side.TRUNG_LAP, "Không vote, tích lũy để giết.", (_k("ma_ca_rong"),), can_target_self=True),
    RoleType.KE_CAT_DIEN: RoleSpec(
        RoleType.KE_CAT_DIEN,
        Side.TRUNG_LAP,
        "Cắt điện và giết khi đã mất điện.",
        (
            SkillSpec(name="cat_dien", phase="any", target_count=0, effects=("info_side",)),
            _k("cat_dien_giet", phase="night"),
        ),
    ),
    RoleType.KE_NOI_HON: RoleSpec(
        RoleType.KE_NOI_HON,
        Side.TRUNG_LAP,
        "Nối hồn hoặc giết.",
        (
            SkillSpec(name="noi_hon", phase="night", target_count=2, effects=("link_targets",)),
            _k("noi_hon_giet"),
        ),
    ),
}

def _infer_night_priority(spec: RoleSpec) -> int:
    night_skills = [skill for skill in spec.skills if skill.phase in ("night", "any")]
    if not night_skills:
        return 0

    effects = {effect for skill in night_skills for effect in skill.effects}
    # Nhỏ -> xử lý sớm hơn, lớn -> xử lý muộn hơn trong pha đêm.
    if "protect_target" in effects:
        base = 300
    elif "kill_target" in effects:
        base = 220
    elif "link_targets" in effects:
        base = 180
    elif "vote_bonus" in effects:
        base = 160
    elif effects.intersection({"info_role", "info_side", "compare_side"}):
        base = 120
    else:
        base = 100

    side_offset = {Side.DAN: 0, Side.SOI: 10, Side.TRUNG_LAP: 20}[spec.side]
    return base + side_offset


ROLE_DESCRIPTION_OVERRIDES: Dict[RoleType, str] = {
    RoleType.DAN_LANG: "Dân làng cơ bản, không có kỹ năng chủ động. Tập trung thảo luận và dùng /vote ban ngày.",
    RoleType.SOI_THUONG: "Sói cơ bản, phối hợp phe Sói để cắn mục tiêu mỗi đêm bằng /votesoi và trao đổi bằng /chatsoi.",
    RoleType.BAO_VE: "Có 2 mạng, mỗi đêm chọn 1 người để bảo vệ; khi đỡ đòn sẽ mất mạng. Dùng /castskill target.",
    RoleType.KE_HAP_HOI: "Mỗi đêm có thể bảo vệ 1 người. Khi bị tấn công sẽ không chết ngay, biết kẻ tấn công và chết vào cuối ngày sau. Dùng /castskill target.",
    RoleType.MUC_SU: "Ban ngày có thể vẩy nước thánh 1 người: nếu là Sói thì mục tiêu chết, nếu không phải Sói thì bạn chết. Dùng /castskill target.",
    RoleType.TIEN_TRI: "Mỗi đêm soi chính xác vai trò 1 người chơi. Dùng /castskill target.",
    RoleType.THAY_BOI: "Mỗi đêm soi phe của 1 người chơi. Dùng /castskill target.",
    RoleType.KE_TINH_GIAC_GIUA_DEM: "Mỗi đêm theo dõi 1 người để biết họ có hoạt động đêm không. Dùng /castskill target.",
    RoleType.NHA_NGOAI_CAM: "Mỗi đêm chọn 2 người; sáng hôm sau nhận báo cáo có ai trong 2 người đã giết người hay không. Dùng /castskill target target2.",
    RoleType.CANH_SAT_TRUONG: "Mỗi đêm bắn 1 người; nếu bắn nhầm phe Dân thì bạn chết ngay. Dùng /castskill target.",
    RoleType.PHAP_SU: "Có 1 lần hồi sinh trong cả ván, dùng được cả khi đã chết. Dùng /castskill target (chọn người đã chết).",
    RoleType.KE_BAO_THU: "Đêm chọn tâm giao, nếu tâm giao chết thì sáng hôm sau có thể trả thù 1 người. Dùng /castskill target skill_name=tam_giao rồi /castskill target skill_name=bao_thu.",
    RoleType.XA_THU: "Có 2 viên đạn để bắn ban ngày. Dùng /castskill target skill_name=ban.",
    RoleType.NHA_BAO: "Biết Người Nổi Tiếng và có thể xem thống kê số Dân/Sói/Trung lập còn sống ban ngày. Dùng /castskill skill_name=thong_ke.",
    RoleType.LOLI: "Nếu bị treo cổ lần đầu sẽ lộ vai trò và được tha trong ngày đó; lần sau sẽ chết bình thường. Không có lệnh riêng.",
    RoleType.NGUOI_BENH: "Nếu bị Sói cắn thì đêm sau Sói không cắn được; nếu bị Trung lập giết thì kẻ đó bị khóa kỹ năng đêm. Không có lệnh riêng.",
    RoleType.NGUOI_GAC_DEM: "Có đúng 3 lượt bảo vệ cho cả ván, có thể chia nhiều mục tiêu trong cùng đêm. Dùng /castskill target [target2] [target3].",
    RoleType.KE_HOANG_TUONG: "Mỗi đêm nhận thông tin vai trò nhưng có 50% sai lệch. Dùng /castskill target.",
    RoleType.NGUOI_NOI_TIENG: "Khi chết sẽ gửi tin nhắn DM cho toàn bộ phe Dân còn sống. Không có lệnh riêng.",
    RoleType.NGUOI_BI_TAY_CHAY: "Ban đêm miễn nhiễm soi/theo dõi/cắn khi chưa có đủ 1/3 người chơi chết. Không có lệnh riêng.",
    RoleType.KE_SONG_SOT: "Nếu là một trong 4 người cuối cùng còn sống thì phe Dân thắng ngay. Không có lệnh riêng.",
    RoleType.NGUOI_CAM_BOM: "Người cầm bom phải chuyển bom mỗi đêm; bom nổ khi tới tay Sói đầu tiên hoặc đêm 5. Dùng /passbomb target.",
    RoleType.KE_HOI_LO: "Mỗi ngày nhận 1 xu (tối đa giữ 2), dùng 1 xu để biết vai trò người chết gần nhất và có thể chuyển xu. Dùng /castskill skill_name=hoi_lo và /transfercoins.",
    RoleType.KE_NGHIEN_CO_BAC: "Có xu khởi đầu, mỗi đêm cược xu vào tối đa 3 người có thể chết; trúng thì nhận gấp đôi, có thể chuyển xu kể cả khi chết. Dùng /castskill target [target2] [target3] skill_name=cuoc_dem:<so_xu> và /transfercoins.",
    RoleType.KE_DA_NGHI: "Trong 3 đêm đầu đánh dấu người; đêm 4 được tiết lộ vai trò các dấu, nếu không có Sói thì chết. Có thể từ chối để không chết. Dùng /castskill target skill_name=danh_dau hoặc /castskill skill_name=tu_choi_tiet_lo.",
    RoleType.KE_THAM_DO: "Mỗi đêm chỉ soi được 1 người đã có phiếu vote ở buổi sáng trước đó. Dùng /castskill target skill_name=tham_do.",
    RoleType.KE_DIEU_HUONG_DU_LUAN: "Nếu bị treo cổ (1 lần), người có số phiếu cao thứ hai cũng chết theo. Không có lệnh riêng.",
    RoleType.KE_KE_THUA: "Đêm chọn 1 người kết hữu; khi người đó chết bạn thừa kế role, nhưng nếu role đó là Sói thì bạn chết. Dùng /castskill target skill_name=ket_huu.",
    RoleType.NGUOI_VAN_DONG_HANH_LANG: "Ban ngày có thể giết nếu có tích lũy; sau khi giết thì người đã vote không đổi phiếu được. Tích lũy tăng theo số phiếu nhận. Dùng /castskill target skill_name=hanh_lang.",
    RoleType.NGUOI_GAY: "Mỗi đêm chọn 1 người ngủ cùng (không lặp liên tiếp). Chọn Sói thì chết chắc; nếu người ngủ cùng bị tấn công thì cả hai cùng chết. Dùng /castskill target skill_name=ngu_cung.",
    RoleType.YANDERE: "Chọn 1 mục tiêu định mệnh từ đầu ván; nếu bạn chết thì kéo mục tiêu chết theo, và khi mục tiêu bị giết đêm thì kẻ giết cũng có thể chết theo. Dùng /castskill target skill_name=keo_chet_theo.",
    RoleType.MEO_BEO: "Có 9 mạng, mỗi đêm tự mất 1 mạng; khi bị tấn công mất 2 mạng. Có thể đổi 1 mạng để soi vai trò mỗi đêm. Dùng /castskill target skill_name=soi_ton_mang.",
    RoleType.KE_TU_DAO: "Từ ngày 3 trở đi có thể hiến tế bản thân để giết ngay 1 người. Dùng /castskill target skill_name=hien_te.",
    RoleType.THAM_TU_TU: "Mỗi đêm so sánh 2 người có cùng phe không; nếu khác phe nhận 1 xu để dùng /detectivevote cộng phiếu ban ngày. Dùng /castskill target target2 skill_name=doi_chieu_phe và /detectivevote.",
    RoleType.THAM_PHAN: "Mỗi đêm chỉ định bị can; ngày sau mặc định vote người đó. Nếu bị can không phải Dân và đạt ngưỡng 2/7 số người chơi thì bị treo ngay. Dùng /castskill target skill_name=ban_an.",
    RoleType.SIMP: "Chọn 1 người để simp, sau đó có 1 lần giết người nào vote mục tiêu đó; đồng thời gánh hiệu ứng thay mục tiêu simp. Dùng /castskill target skill_name=nhan_hieu_ung và /castskill target skill_name=phan_simp.",
    RoleType.NGUOI_TIEN_PHONG: "Nếu là người vote đầu tiên trong ngày, lá phiếu đó được tính gấp đôi. Không có lệnh riêng.",
    RoleType.KE_CHAN_DON: "Mỗi đêm chọn 1 người để hút các kỹ năng của người đó về mình trong vòng 1 ngày; có 2 mạng. Dùng /castskill target skill_name=chan_don.",
    RoleType.KE_GHI_HAN: "Mỗi dân bị treo cổ giúp bạn tích hận; khi chết sẽ trả đũa theo số tích lũy hiện có. Không có lệnh chủ động bắt buộc.",
    RoleType.DAO_PHU: "Mỗi sáng có thể giết 1 người đang có ít nhất 1 phiếu; nếu giết nhầm Dân thì mất năng lực vĩnh viễn. Dùng /castskill target skill_name=dao_phu.",
    RoleType.NGUOI_NHAN_NHIN: "Có 2 mạng, 1 lần trong ván có thể hút toàn bộ cụm phiếu cao nhất về mình và chịu mất mạng; không bị Sói cắn chết trực tiếp. Dùng /castskill skill_name=nhan_vote.",
    RoleType.SOI_PHAP_SU: "Mỗi đêm yểm 1 người để Tiên Tri/Thầy Bói nhìn thành phe Sói trong đêm đó. Dùng /castskill target skill_name=yem_soi.",
    RoleType.SOI_GIAN_DIEP: "Nếu bạn là người duy nhất vote một mục tiêu vào ban ngày thì sẽ biết vai trò mục tiêu qua DM. Dùng /vote.",
    RoleType.SOI_SAT_THU: "Có 2 lần đoán vai trò để giết bất cứ lúc nào; đoán sai thì chết. Dùng /castskill target skill_name=sat_thu:<role_doan>.",
    RoleType.SOI_BANG: "Mỗi đêm khóa kỹ năng của 1 người, không được chọn cùng mục tiêu 2 đêm liên tiếp. Dùng /castskill target skill_name=dong_bang.",
    RoleType.SOI_GOKU: "Có 1 lần Kamehameha xuyên bảo vệ vào ban đêm. Dùng /castskill target skill_name=kamehameha.",
    RoleType.SOI_HAC_AM: "Một lần/ ván đánh dấu mục tiêu bị nhân đôi phiếu ngày sau (và ẩn phiếu theo thiết kế nâng cao). Dùng /castskill target skill_name=nhan_doi_vote.",
    RoleType.SOI_TICH_LUY: "Nếu phe Sói không giết ai trong đêm sẽ tích lượt giết bổ sung cho các đêm sau; mất hiệu lực khi bạn chết. Dùng /castskill target skill_name=tich_luy_kill khi có tích.",
    RoleType.SOI_CUOP_DANH_TINH: "Mỗi đêm cướp danh tính 1 người để kết quả soi thấy bạn mang role/phe của họ; không lặp mục tiêu liên tiếp. Dùng /castskill target skill_name=cuop_danh_tinh.",
    RoleType.SOI_MACH_LEO: "Mỗi đêm chọn 1 người để hôm sau bị nhốt, mất vote và mất kỹ năng ngày; không lặp mục tiêu liên tiếp. Dùng /castskill target skill_name=mach_leo.",
    RoleType.SOI_PHAN_DONG: "Nếu Sói hạ Cảnh Sát Trưởng hoặc Người Vận Động Hành Lang ban đêm, bạn được mở 1 lượt giết đêm sau. Dùng /castskill target skill_name=phan_dong khi đã được kích hoạt.",
    RoleType.SOI_HO_VE: "Một lần/ ván bảo vệ 1 người khỏi treo cổ trong ngày (kể cả bản thân). Dùng /castskill target skill_name=ho_ve.",
    RoleType.SOI_DAT_BAY: "Mỗi đêm đặt bẫy 1 người; nếu có người bảo vệ họ thì người bảo vệ mất mạng. Sói không cắn người đang bị đặt bẫy. Dùng /castskill target skill_name=dat_bay.",
    RoleType.SOI_CAM_TU: "Khi bị treo cổ có thể kéo chết theo 1 người đã vote mình. Không có lệnh chủ động trước khi chết.",
    RoleType.SOI_GIAN_LAN: "Một lần/ ván nếu phiếu skip vượt 1/4 số người còn sống thì có thể bỏ qua buổi vote. Dùng /castskill skill_name=gian_lan trước khi kết ngày.",
    RoleType.SOI_CO_KHIEN: "Mỗi đêm dùng khiên bảo kê tối đa 2 Sói; khi một mục tiêu bị đánh trúng sẽ hao khiên. Có thể /revealshield để miễn nhiễm vote ngày đó và nhận thêm khiên.",
    RoleType.SOI_KET_GIOI: "Một lần/ ván tạo kết giới ban đêm giúp toàn bộ Sói miễn nhiễm sát thương đêm. Dùng /castskill target skill_name=ket_gioi.",
    RoleType.SOI_TU_BAN: "Làm tăng giá tiêu xu toàn ván, nhận hoàn xu từ người khác; có thể tốn xu để bảo kê Sói hoặc thêm lượt giết đêm. Dùng /castskill target skill_name=tu_ban_bao_ke hoặc /castskill target skill_name=tu_ban.",
    RoleType.SOI_TINH_BAN: "Không thể chết khi phe Sói còn trên 2 người. Không có lệnh riêng.",
    RoleType.KE_DAT_BOM: "Mỗi đêm đặt bom lên 1 mục tiêu, bom nổ ở đêm kế tiếp. Dùng /castskill target skill_name=dat_bom.",
    RoleType.KE_PHONG_HOA: "Mỗi đêm có thể tẩm xăng tối đa 2 người hoặc đốt toàn bộ người đã tẩm. Dùng /castskill target [target2] skill_name=phong_hoa để tẩm, hoặc /castskill skill_name=phong_hoa:dot để đốt.",
    RoleType.LOLICON: "Biết danh tính Loli; khi Loli chết sẽ nổi điên và được giết đêm, đồng thời có 1 lần hồi sinh nếu bị Sói cắn. Dùng /castskill skill_name=soi_loli và /castskill target skill_name=lolicon khi đã nổi điên.",
    RoleType.SOI_CO_DOC: "Giết độc lập 1 mục tiêu mỗi 2 đêm. Dùng /castskill target skill_name=soi_co_doc.",
    RoleType.KE_NOI_DOI: "Nếu bị treo cổ thì thắng ngay lập tức. Không có lệnh riêng.",
    RoleType.THICH_KHACH: "Giết đêm theo số tích lũy (khởi đầu 1, tăng 1 mỗi 2 phiếu nhận ban ngày), không thể vote bản thân. Dùng /castskill target skill_name=thich_khach.",
    RoleType.CON_QUA: "Mỗi đêm gắn +2 phiếu cho 1 người; nếu người đó bị treo thì đêm sau được thêm 1 lượt giết. Dùng /castskill target skill_name=con_qua.",
    RoleType.KE_TIM_SU_THAT: "Thắng khi công bố đúng vai trò của ít nhất 3 người còn sống vào ban ngày. Dùng /castskill target skill_name=tim_su_that:<role_doan>.",
    RoleType.SAT_THU: "Đoán đúng vai trò để giết bất cứ lúc nào, đoán sai thì chết. Dùng /castskill target skill_name=sat_thu:<role_doan>.",
    RoleType.KE_TANG_HINH: "Ban ngày có thể bắn 1 người nếu chưa chat ngày đó; có 1 lần hồi sinh nếu bị Sói cắn. Dùng /daychat để chat công khai và /castskill target skill_name=tang_hinh để bắn.",
    RoleType.KE_DANH_BAC: "Đêm có thể đoán số người chết để tích lượt giết, hoặc tiêu tích để giết. Dùng /castskill skill_name=doan_so_nguoi_chet:<so> và /castskill target skill_name=danh_bac.",
    RoleType.KE_PHAN_DON: "Ban đêm nếu bị tác động hiệu ứng (không phải đòn giết) sẽ phản đòn hạ người dùng hiệu ứng; đồng thời có lượt giết 1 lần mỗi 2 đêm. Dùng /castskill target skill_name=phan_don.",
    RoleType.CAO_BOI: "Mỗi đêm chọn 1 người đọ súng: nếu mục tiêu có khả năng giết người thì bạn chết, ngược lại mục tiêu chết. Dùng /castskill target skill_name=do_sung.",
    RoleType.AYANOKOJI: "Chỉ chết khi bị soi trúng 2 lần hoặc trúng 2 đòn từ nhóm Sát Thủ; lần soi đầu trả role giả phe Dân. Thắng khi Sói chết hết và phe Dân không còn khả năng soi role.",
    RoleType.KE_TAM_LY_YEU: "Ban đêm miễn tác động từ người khác, ban ngày chỉ nên vote; đủ ngưỡng 3 phiếu sẽ chết. Khi chỉ còn 2/5 người chơi trở xuống thì mở kỹ năng giết đêm. Dùng /castskill target skill_name=tam_ly_yeu khi đủ điều kiện.",
    RoleType.VUA_LI_DON: "Chỉ có thể chết do treo cổ. Thắng khi còn đúng 5 người sống.",
    RoleType.KIM_JONG_UN: "Khi còn 4/7 người chơi sẽ bắt đầu đếm 2 ngày; nếu hết hạn vẫn sống thì thắng ngay (tên lửa nổ). Dùng /castskill target skill_name=ten_lua cho kỹ năng chủ động ban ngày.",
    RoleType.GIAN_THUONG: "Có thể tốn 2 xu để giết, tối đa 3 mạng mỗi đêm; nhận thêm xu từ thu nhập dân và theo số người chết. Dùng /castskill target skill_name=gian_thuong.",
    RoleType.MA_CA_RONG: "Không thể vote và miễn nhiễm các đòn giết ban ngày; nếu không bị vote sẽ tích điểm để giết ban đêm. Thắng khi còn 3 người sống. Dùng /castskill target skill_name=ma_ca_rong.",
    RoleType.KE_CAT_DIEN: "Chỉ được vote skip. Có thể bật mất điện để vô hiệu hóa kỹ năng đặc biệt toàn bàn cho tới khi bạn chết; sau đó được giết 1 lần mỗi đêm. Dùng /castskill skill_name=cat_dien và /castskill target skill_name=cat_dien_giet.",
    RoleType.KE_NOI_HON: "Mỗi đêm nối 2 người để tạo chết dây chuyền (liên kết có thể lan chuỗi); có 1 lần giết trong ván và không bị Sói cắn chết trực tiếp. Dùng /castskill target target2 skill_name=noi_hon hoặc /castskill target skill_name=noi_hon_giet.",
}

PARTIAL_ROLES = set()


def _extract_command_hint(override_text: str) -> str:
    markers = [
        "Dùng ",
        "Có thể /",
        "Không có lệnh riêng.",
        "Không có lệnh chủ động",
        "Không có lệnh skill chủ động.",
    ]
    for marker in markers:
        idx = override_text.find(marker)
        if idx >= 0:
            return override_text[idx:].strip()
    return ""


def _load_roles_md_descriptions() -> Dict[RoleType, str]:
    roles_md_path = Path(__file__).resolve().parent.parent / "roles.md"
    if not roles_md_path.exists():
        return {}

    section_lines: Dict[str, list[str]] = {"dan": [], "soi": [], "trung_lap": []}
    section: Optional[str] = None
    for raw_line in roles_md_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("# Dân"):
            section = "dan"
            continue
        if line.startswith("# Sói"):
            section = "soi"
            continue
        if line.startswith("# Trung lập"):
            section = "trung_lap"
            continue
        if not line.startswith("+ ") or section is None:
            continue
        content = line[2:].strip()
        if ":" in content:
            _, desc = content.split(":", 1)
            section_lines[section].append(desc.strip())
        else:
            section_lines[section].append(content.strip())

    dan_roles = [role for role, spec in ROLE_SPECS.items() if spec.side == Side.DAN and role != RoleType.DAN_LANG]
    soi_roles = [role for role, spec in ROLE_SPECS.items() if spec.side == Side.SOI and role != RoleType.SOI_THUONG]
    neutral_roles = [role for role, spec in ROLE_SPECS.items() if spec.side == Side.TRUNG_LAP]

    if (
        len(section_lines["dan"]) != len(dan_roles)
        or len(section_lines["soi"]) != len(soi_roles)
        or len(section_lines["trung_lap"]) != len(neutral_roles)
    ):
        return {}

    result: Dict[RoleType, str] = {}
    result.update({role: desc for role, desc in zip(dan_roles, section_lines["dan"])})
    result.update({role: desc for role, desc in zip(soi_roles, section_lines["soi"])})
    result.update({role: desc for role, desc in zip(neutral_roles, section_lines["trung_lap"])})
    return result


ROLE_MD_DESCRIPTIONS = _load_roles_md_descriptions()


def _compose_role_description(role: RoleType, spec: RoleSpec) -> str:
    base = ROLE_MD_DESCRIPTIONS.get(role, ROLE_DESCRIPTION_OVERRIDES.get(role, spec.description))
    command_hint = _extract_command_hint(ROLE_DESCRIPTION_OVERRIDES.get(role, ""))
    if command_hint and command_hint not in base:
        return f"{base} {command_hint}"
    return base


ROLE_SPECS = {
    role: replace(
        spec,
        priority=_infer_night_priority(spec),
        description=_compose_role_description(role, spec),
        implementation_level=("partial" if role in PARTIAL_ROLES else "exact"),
    )
    for role, spec in ROLE_SPECS.items()
}
