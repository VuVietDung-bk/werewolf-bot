from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple

from enums import RoleType, Side


@dataclass(frozen=True)
class SkillSpec:
    name: str
    phase: str  # day | night | any
    target_count: int
    effects: Tuple[str, ...] = field(default_factory=tuple)
    vote_bonus: int = 1


@dataclass(frozen=True)
class RoleSpec:
    role: RoleType
    side: Side
    description: str
    skills: Tuple[SkillSpec, ...] = field(default_factory=tuple)
    can_target_self: bool = False
    cooldown: int = 0


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


ROLE_SPECS: Dict[RoleType, RoleSpec] = {
    RoleType.DAN_LANG: RoleSpec(RoleType.DAN_LANG, Side.DAN, "Dân làng cơ bản."),
    RoleType.SOI_THUONG: RoleSpec(RoleType.SOI_THUONG, Side.SOI, "Sói thường."),
    RoleType.BAO_VE: RoleSpec(RoleType.BAO_VE, Side.DAN, "Bảo vệ ban đêm.", (_protect("bao_ke"),), can_target_self=True),
    RoleType.KE_HAP_HOI: RoleSpec(RoleType.KE_HAP_HOI, Side.DAN, "Bảo vệ ban đêm, chết trễ khi bị cắn.", (_protect("bao_ke"),), can_target_self=True),
    RoleType.MUC_SU: RoleSpec(RoleType.MUC_SU, Side.DAN, "Vẩy nước thánh ban ngày.", (_k("vay_nuoc_thanh", phase="day"),)),
    RoleType.TIEN_TRI: RoleSpec(RoleType.TIEN_TRI, Side.DAN, "Soi vai trò ban đêm.", (_i_role("soi_role"),)),
    RoleType.THAY_BOI: RoleSpec(RoleType.THAY_BOI, Side.DAN, "Soi phe ban đêm.", (_i_side("soi_phe"),)),
    RoleType.KE_TINH_GIAC_GIUA_DEM: RoleSpec(RoleType.KE_TINH_GIAC_GIUA_DEM, Side.DAN, "Theo dõi một người ban đêm.", (_i_role("theo_doi"),)),
    RoleType.NHA_NGOAI_CAM: RoleSpec(RoleType.NHA_NGOAI_CAM, Side.DAN, "Theo dõi hai người ban đêm.", (_i_role("ngoai_cam", target_count=2),)),
    RoleType.CANH_SAT_TRUONG: RoleSpec(RoleType.CANH_SAT_TRUONG, Side.DAN, "Giết một người ban đêm.", (_k("xu_ban"),)),
    RoleType.PHAP_SU: RoleSpec(RoleType.PHAP_SU, Side.DAN, "Hồi sinh một lần.", (_i_role("hoi_sinh", phase="any"),)),
    RoleType.KE_BAO_THU: RoleSpec(RoleType.KE_BAO_THU, Side.DAN, "Gắn tâm giao ban đêm.", (_i_role("tam_giao"),)),
    RoleType.XA_THU: RoleSpec(RoleType.XA_THU, Side.DAN, "Bắn ban ngày.", (_k("ban", phase="day"),)),
    RoleType.NHA_BAO: RoleSpec(RoleType.NHA_BAO, Side.DAN, "Lấy thông tin tỷ lệ phe.", (_i_side("thong_ke", phase="day"),)),
    RoleType.LOLI: RoleSpec(RoleType.LOLI, Side.DAN, "Bị treo cổ có cơ hội sống.", (_i_role("tu_tiet_lo"),)),
    RoleType.NGUOI_BENH: RoleSpec(RoleType.NGUOI_BENH, Side.DAN, "Hiệu ứng phản ứng khi bị tấn công.", (_i_side("phan_ung_benh"),)),
    RoleType.NGUOI_GAC_DEM: RoleSpec(RoleType.NGUOI_GAC_DEM, Side.DAN, "Bảo vệ nhiều lượt.", (_protect("gac_dem"),)),
    RoleType.KE_HOANG_TUONG: RoleSpec(RoleType.KE_HOANG_TUONG, Side.DAN, "Nhận thông tin có nhiễu.", (_i_role("thong_tin_ngau_nhien"),)),
    RoleType.NGUOI_NOI_TIENG: RoleSpec(RoleType.NGUOI_NOI_TIENG, Side.DAN, "Lộ tin khi chết.", (_i_role("lo_tin_khi_chet"),)),
    RoleType.NGUOI_BI_TAY_CHAY: RoleSpec(RoleType.NGUOI_BI_TAY_CHAY, Side.DAN, "Miễn soi/cắn ban đêm.", (_protect("mien_nhiem_dem"),), can_target_self=True),
    RoleType.KE_SONG_SOT: RoleSpec(RoleType.KE_SONG_SOT, Side.DAN, "Điều kiện thắng mở rộng.", (_i_side("kiem_tra_song_sot"),)),
    RoleType.NGUOI_CAM_BOM: RoleSpec(RoleType.NGUOI_CAM_BOM, Side.DAN, "Trao bom mỗi đêm.", (_k("trao_bom"),)),
    RoleType.KE_HOI_LO: RoleSpec(RoleType.KE_HOI_LO, Side.DAN, "Dùng xu lấy thông tin chết.", (_i_role("hoi_lo", phase="day"),)),
    RoleType.KE_NGHIEN_CO_BAC: RoleSpec(RoleType.KE_NGHIEN_CO_BAC, Side.DAN, "Cược người chết đêm.", (_i_role("cuoc_dem"),)),
    RoleType.KE_DA_NGHI: RoleSpec(RoleType.KE_DA_NGHI, Side.DAN, "Đánh dấu và soi sau 3 đêm.", (_i_role("danh_dau"),)),
    RoleType.KE_THAM_DO: RoleSpec(RoleType.KE_THAM_DO, Side.DAN, "Soi role trong nhóm bị vote.", (_i_role("tham_do"),)),
    RoleType.KE_DIEU_HUONG_DU_LUAN: RoleSpec(RoleType.KE_DIEU_HUONG_DU_LUAN, Side.DAN, "Kích hoạt chết dây chuyền khi bị treo.", (_vote_bonus("du_luan"),)),
    RoleType.KE_KE_THUA: RoleSpec(RoleType.KE_KE_THUA, Side.DAN, "Kết hữu để kế thừa role.", (_i_role("ket_huu"),)),
    RoleType.NGUOI_VAN_DONG_HANH_LANG: RoleSpec(RoleType.NGUOI_VAN_DONG_HANH_LANG, Side.DAN, "Giết ban ngày nếu có tích lũy.", (_k("hanh_lang", phase="day"),)),
    RoleType.NGUOI_GAY: RoleSpec(RoleType.NGUOI_GAY, Side.DAN, "Ngủ cùng mục tiêu ban đêm.", (_protect("ngu_cung"),)),
    RoleType.YANDERE: RoleSpec(RoleType.YANDERE, Side.DAN, "Chọn người kéo chết theo.", (_k("keo_chet_theo"),)),
    RoleType.MEO_BEO: RoleSpec(RoleType.MEO_BEO, Side.DAN, "9 mạng, soi tốn mạng.", (_i_role("soi_ton_mang"),), can_target_self=True),
    RoleType.KE_TU_DAO: RoleSpec(RoleType.KE_TU_DAO, Side.DAN, "Hiến tế giết 1 người.", (_k("hien_te", phase="day"),)),
    RoleType.THAM_TU_TU: RoleSpec(RoleType.THAM_TU_TU, Side.DAN, "Soi 2 người cùng phe không.", (SkillSpec("doi_chieu_phe", "night", 2, ("compare_side",)),)),
    RoleType.THAM_PHAN: RoleSpec(RoleType.THAM_PHAN, Side.DAN, "Đặt bản án ban đêm.", (_vote_bonus("ban_an"),)),
    RoleType.SIMP: RoleSpec(RoleType.SIMP, Side.DAN, "Simp và phản kích.", (_k("phan_simp", phase="day"), _protect("nhan_hieu_ung", phase="any"))),
    RoleType.NGUOI_TIEN_PHONG: RoleSpec(RoleType.NGUOI_TIEN_PHONG, Side.DAN, "Vote đầu tiên x2.", (_vote_bonus("vote_dau_tien", bonus=2),)),
    RoleType.KE_CHAN_DON: RoleSpec(RoleType.KE_CHAN_DON, Side.DAN, "Hút kỹ năng về mình.", (_protect("chan_don"),), can_target_self=True),
    RoleType.KE_GHI_HAN: RoleSpec(RoleType.KE_GHI_HAN, Side.DAN, "Ghi hận và trả đũa.", (_k("tra_thu"),)),
    RoleType.DAO_PHU: RoleSpec(RoleType.DAO_PHU, Side.DAN, "Giết người có vote buổi sáng.", (_k("dao_phu", phase="day"),)),
    RoleType.NGUOI_NHAN_NHIN: RoleSpec(RoleType.NGUOI_NHAN_NHIN, Side.DAN, "2 mạng, đổi hướng vote 1 lần.", (_protect("nhan_vote", phase="day"),), can_target_self=True),
    RoleType.SOI_PHAP_SU: RoleSpec(RoleType.SOI_PHAP_SU, Side.SOI, "Yểm thông tin soi.", (_i_side("yem_soi"),)),
    RoleType.SOI_GIAN_DIEP: RoleSpec(RoleType.SOI_GIAN_DIEP, Side.SOI, "Đọc role khi vote đơn độc.", (_i_role("gian_diep", phase="day"),)),
    RoleType.SOI_SAT_THU: RoleSpec(RoleType.SOI_SAT_THU, Side.SOI, "Đoán role để giết.", (_k("sat_thu", phase="any"),)),
    RoleType.SOI_BANG: RoleSpec(RoleType.SOI_BANG, Side.SOI, "Khóa kỹ năng mục tiêu.", (_protect("dong_bang"),)),
    RoleType.SOI_GOKU: RoleSpec(RoleType.SOI_GOKU, Side.SOI, "Giết xuyên bảo vệ 1 lần.", (_k("kamehameha"),)),
    RoleType.SOI_HAC_AM: RoleSpec(RoleType.SOI_HAC_AM, Side.SOI, "Nhân đôi phiếu ngày sau.", (_vote_bonus("nhan_doi_vote", bonus=2),)),
    RoleType.SOI_TICH_LUY: RoleSpec(RoleType.SOI_TICH_LUY, Side.SOI, "Tích lũy lượt giết sói.", (_k("tich_luy_kill"),)),
    RoleType.SOI_CUOP_DANH_TINH: RoleSpec(RoleType.SOI_CUOP_DANH_TINH, Side.SOI, "Cướp role hiển thị.", (_i_role("cuop_danh_tinh"),)),
    RoleType.SOI_MACH_LEO: RoleSpec(RoleType.SOI_MACH_LEO, Side.SOI, "Nhốt mục tiêu mất skill/vote.", (_vote_bonus("mach_leo"),)),
    RoleType.SOI_PHAN_DONG: RoleSpec(RoleType.SOI_PHAN_DONG, Side.SOI, "Thêm lượt giết nếu hạ role đặc biệt.", (_k("phan_dong"),)),
    RoleType.SOI_HO_VE: RoleSpec(RoleType.SOI_HO_VE, Side.SOI, "Cứu khỏi treo cổ 1 lần.", (_protect("ho_ve", phase="day"),), can_target_self=True),
    RoleType.SOI_DAT_BAY: RoleSpec(RoleType.SOI_DAT_BAY, Side.SOI, "Đặt bẫy vào mục tiêu.", (_k("dat_bay"),)),
    RoleType.SOI_CAM_TU: RoleSpec(RoleType.SOI_CAM_TU, Side.SOI, "Bị treo kéo chết theo.", (_k("cam_tu", phase="day"),)),
    RoleType.SOI_GIAN_LAN: RoleSpec(RoleType.SOI_GIAN_LAN, Side.SOI, "Bỏ qua vote khi skip cao.", (_vote_bonus("gian_lan"),)),
    RoleType.SOI_CO_KHIEN: RoleSpec(RoleType.SOI_CO_KHIEN, Side.SOI, "Khiên bảo vệ sói.", (_protect("khien_soi"),), can_target_self=True),
    RoleType.SOI_KET_GIOI: RoleSpec(RoleType.SOI_KET_GIOI, Side.SOI, "Tạo kết giới miễn giết.", (_protect("ket_gioi"),), can_target_self=True),
    RoleType.SOI_TU_BAN: RoleSpec(RoleType.SOI_TU_BAN, Side.SOI, "Tiêu xu để bảo kê/giết.", (_k("tu_ban"), _protect("tu_ban_bao_ke"))),
    RoleType.SOI_TINH_BAN: RoleSpec(RoleType.SOI_TINH_BAN, Side.SOI, "Không chết khi còn >2 sói.", (_protect("tinh_ban"),), can_target_self=True),
    RoleType.KE_DAT_BOM: RoleSpec(RoleType.KE_DAT_BOM, Side.TRUNG_LAP, "Đặt bom nổ đêm sau.", (_k("dat_bom"),)),
    RoleType.KE_PHONG_HOA: RoleSpec(RoleType.KE_PHONG_HOA, Side.TRUNG_LAP, "Tẩm xăng/đốt.", (_k("phong_hoa"),)),
    RoleType.LOLICON: RoleSpec(RoleType.LOLICON, Side.TRUNG_LAP, "Rage kill khi Loli chết.", (_k("lolicon"), _i_role("soi_loli"))),
    RoleType.SOI_CO_DOC: RoleSpec(RoleType.SOI_CO_DOC, Side.TRUNG_LAP, "Giết độc lập mỗi 2 đêm.", (_k("soi_co_doc"),), cooldown=1),
    RoleType.KE_NOI_DOI: RoleSpec(RoleType.KE_NOI_DOI, Side.TRUNG_LAP, "Bị treo thắng ngay.", (_i_side("noi_doi"),)),
    RoleType.THICH_KHACH: RoleSpec(RoleType.THICH_KHACH, Side.TRUNG_LAP, "Giết theo tích lũy.", (_k("thich_khach"),)),
    RoleType.CON_QUA: RoleSpec(RoleType.CON_QUA, Side.TRUNG_LAP, "Gắn +2 vote.", (_vote_bonus("con_qua", bonus=2),)),
    RoleType.KE_TIM_SU_THAT: RoleSpec(RoleType.KE_TIM_SU_THAT, Side.TRUNG_LAP, "Công khai role đúng để thắng.", (_i_role("tim_su_that", phase="day"),)),
    RoleType.SAT_THU: RoleSpec(RoleType.SAT_THU, Side.TRUNG_LAP, "Đoán role để giết.", (_k("sat_thu", phase="any"),)),
    RoleType.KE_TANG_HINH: RoleSpec(RoleType.KE_TANG_HINH, Side.TRUNG_LAP, "Tàng hình và bắn ban ngày.", (_k("tang_hinh", phase="day"),)),
    RoleType.KE_DANH_BAC: RoleSpec(RoleType.KE_DANH_BAC, Side.TRUNG_LAP, "Đoán số người chết hoặc giết.", (_k("danh_bac"), _i_side("doan_so_nguoi_chet"))),
    RoleType.KE_PHAN_DON: RoleSpec(RoleType.KE_PHAN_DON, Side.TRUNG_LAP, "Phản đòn và giết định kỳ.", (_k("phan_don"), _protect("mien_hieu_ung", phase="any"))),
    RoleType.CAO_BOI: RoleSpec(RoleType.CAO_BOI, Side.TRUNG_LAP, "Đọ súng ban đêm.", (_k("do_sung"),)),
    RoleType.AYANOKOJI: RoleSpec(RoleType.AYANOKOJI, Side.TRUNG_LAP, "Chết theo điều kiện soi/sát thủ.", (_i_role("ayanokoji"),)),
    RoleType.KE_TAM_LY_YEU: RoleSpec(RoleType.KE_TAM_LY_YEU, Side.TRUNG_LAP, "Ban ngày chỉ vote, đủ điều kiện thì giết.", (_k("tam_ly_yeu"),)),
    RoleType.VUA_LI_DON: RoleSpec(RoleType.VUA_LI_DON, Side.TRUNG_LAP, "Chỉ chết do treo cổ.", (_protect("li_don"),), can_target_self=True),
    RoleType.KIM_JONG_UN: RoleSpec(RoleType.KIM_JONG_UN, Side.TRUNG_LAP, "Countdown 2 ngày, nổ tên lửa.", (_k("ten_lua", phase="day"),)),
    RoleType.GIAN_THUONG: RoleSpec(RoleType.GIAN_THUONG, Side.TRUNG_LAP, "Dùng xu để giết.", (_k("gian_thuong"),)),
    RoleType.MA_CA_RONG: RoleSpec(RoleType.MA_CA_RONG, Side.TRUNG_LAP, "Không vote, tích lũy để giết.", (_k("ma_ca_rong"),), can_target_self=True),
    RoleType.KE_CAT_DIEN: RoleSpec(RoleType.KE_CAT_DIEN, Side.TRUNG_LAP, "Cắt điện và giết.", (_k("cat_dien", phase="any"), _vote_bonus("chi_skip"))),
    RoleType.KE_NOI_HON: RoleSpec(RoleType.KE_NOI_HON, Side.TRUNG_LAP, "Nối hồn hoặc giết.", (SkillSpec("noi_hon", "night", 2, ("link_targets",)), _k("noi_hon_giet"))),
}
