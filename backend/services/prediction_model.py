"""
美加墨世界杯AI预测模型 26.5 - deterministic World Cup match predictor.

The model keeps the app lightweight, but follows the common open-source
football forecasting pattern: team strength/Elo -> expected goals ->
Dixon-Coles adjusted Poisson score matrix. No per-request randomness is used,
so the same match and scenario settings always return the same score.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from services.odds_market import fetch_market_odds
from services.public_data_sources import build_public_data_sources
from services.team_squads import get_team_squad, squad_lineup, squad_player_projections


@dataclass(frozen=True)
class TeamProfile:
    name: str
    code: str
    fifa_rank: int
    elo_rating: int
    confederation: str
    titles: int = 0
    is_host: bool = False
    is_debut: bool = False


@dataclass(frozen=True)
class PlayerProjection:
    name: str
    position: str
    role: str
    attack_share: float
    key_metric: str


@dataclass(frozen=True)
class TacticalTemplate:
    formation: str
    style: str
    attacking_pattern: str
    defensive_shape: str
    set_piece: str
    risk: str
    starters: Tuple[str, ...]
    bench_options: Tuple[str, ...]


@dataclass(frozen=True)
class TeamDepthHint:
    formation: str
    style: str
    starters: Tuple[str, ...]
    bench_options: Tuple[str, ...]
    scorers: Tuple[PlayerProjection, ...]


@dataclass(frozen=True)
class DisciplineStatus:
    yellow_cards: int = 0
    red_cards: int = 0
    suspended_players: Tuple[str, ...] = ()
    card_risk_players: Tuple[str, ...] = ()


@dataclass(frozen=True)
class TeamPropBaseline:
    corners_for: float
    corners_against: float
    yellow_cards_for: float
    yellow_cards_against: float
    sample_matches: int = 5
    source: str = "recent_official_matches_profile"


@dataclass(frozen=True)
class TacticalEvidence:
    tactic: TacticalTemplate
    source: str
    source_label: str
    note: str
    confidence: float


TEAM_PROFILES: Dict[str, TeamProfile] = {
    "墨西哥": TeamProfile("墨西哥", "MEX", 15, 1830, "CONCACAF", is_host=True),
    "南非": TeamProfile("南非", "RSA", 60, 1520, "CAF"),
    "韩国": TeamProfile("韩国", "KOR", 25, 1720, "AFC"),
    "捷克": TeamProfile("捷克", "CZE", 41, 1650, "UEFA"),
    "加拿大": TeamProfile("加拿大", "CAN", 30, 1700, "CONCACAF", is_host=True),
    "波黑": TeamProfile("波黑", "BIH", 52, 1580, "UEFA"),
    "卡塔尔": TeamProfile("卡塔尔", "QAT", 35, 1610, "AFC"),
    "瑞士": TeamProfile("瑞士", "SUI", 19, 1770, "UEFA"),
    "巴西": TeamProfile("巴西", "BRA", 6, 2080, "CONMEBOL", titles=5),
    "摩洛哥": TeamProfile("摩洛哥", "MAR", 8, 1940, "CAF"),
    "海地": TeamProfile("海地", "HAI", 83, 1440, "CONCACAF"),
    "苏格兰": TeamProfile("苏格兰", "SCO", 47, 1620, "UEFA"),
    "美国": TeamProfile("美国", "USA", 16, 1800, "CONCACAF", is_host=True),
    "巴拉圭": TeamProfile("巴拉圭", "PAR", 64, 1550, "CONMEBOL"),
    "澳大利亚": TeamProfile("澳大利亚", "AUS", 26, 1710, "AFC"),
    "土耳其": TeamProfile("土耳其", "TUR", 42, 1660, "UEFA"),
    "德国": TeamProfile("德国", "GER", 10, 1960, "UEFA", titles=4),
    "库拉索": TeamProfile("库拉索", "CUW", 81, 1430, "CONCACAF"),
    "科特迪瓦": TeamProfile("科特迪瓦", "CIV", 33, 1680, "CAF"),
    "厄瓜多尔": TeamProfile("厄瓜多尔", "ECU", 24, 1720, "CONMEBOL"),
    "荷兰": TeamProfile("荷兰", "NED", 7, 1980, "UEFA"),
    "日本": TeamProfile("日本", "JPN", 18, 1760, "AFC"),
    "瑞典": TeamProfile("瑞典", "SWE", 39, 1630, "UEFA"),
    "突尼斯": TeamProfile("突尼斯", "TUN", 40, 1620, "CAF"),
    "比利时": TeamProfile("比利时", "BEL", 9, 1950, "UEFA"),
    "埃及": TeamProfile("埃及", "EGY", 29, 1690, "CAF"),
    "伊朗": TeamProfile("伊朗", "IRN", 21, 1730, "AFC"),
    "新西兰": TeamProfile("新西兰", "NZL", 95, 1400, "OFC"),
    "西班牙": TeamProfile("西班牙", "ESP", 2, 2100, "UEFA", titles=1),
    "佛得角": TeamProfile("佛得角", "CPV", 70, 1490, "CAF", is_debut=True),
    "沙特阿拉伯": TeamProfile("沙特阿拉伯", "KSA", 57, 1560, "AFC"),
    "乌拉圭": TeamProfile("乌拉圭", "URU", 17, 1790, "CONMEBOL", titles=2),
    "法国": TeamProfile("法国", "FRA", 1, 2120, "UEFA", titles=2),
    "塞内加尔": TeamProfile("塞内加尔", "SEN", 14, 1780, "CAF"),
    "伊拉克": TeamProfile("伊拉克", "IRQ", 61, 1530, "AFC"),
    "挪威": TeamProfile("挪威", "NOR", 44, 1640, "UEFA"),
    "阿根廷": TeamProfile("阿根廷", "ARG", 3, 2100, "CONMEBOL", titles=3),
    "阿尔及利亚": TeamProfile("阿尔及利亚", "ALG", 36, 1600, "CAF"),
    "奥地利": TeamProfile("奥地利", "AUT", 23, 1700, "UEFA"),
    "约旦": TeamProfile("约旦", "JOR", 68, 1490, "AFC", is_debut=True),
    "葡萄牙": TeamProfile("葡萄牙", "POR", 5, 2020, "UEFA"),
    "民主刚果": TeamProfile("民主刚果", "COD", 51, 1580, "CAF"),
    "乌兹别克斯坦": TeamProfile("乌兹别克斯坦", "UZB", 62, 1520, "AFC", is_debut=True),
    "哥伦比亚": TeamProfile("哥伦比亚", "COL", 13, 1800, "CONMEBOL"),
    "英格兰": TeamProfile("英格兰", "ENG", 4, 2050, "UEFA", titles=1),
    "克罗地亚": TeamProfile("克罗地亚", "CRO", 11, 1880, "UEFA"),
    "加纳": TeamProfile("加纳", "GHA", 65, 1540, "CAF"),
    "巴拿马": TeamProfile("巴拿马", "PAN", 53, 1530, "CONCACAF"),
}

FIFA_RANKING_SOURCE = {
    "source": "FIFA/Coca-Cola Men's World Ranking",
    "last_updated": "2026-06-11",
    "next_update": "2026-07-20",
    "message": "FIFA official ranking snapshot updated on 2026-06-11; next official update is 2026-07-20.",
}

FIFA_RANKING_SNAPSHOT: Dict[str, int] = {
    "ALG": 28,
    "ARG": 1,
    "AUS": 27,
    "AUT": 24,
    "BEL": 9,
    "BIH": 64,
    "BRA": 6,
    "CAN": 30,
    "CIV": 33,
    "COD": 46,
    "COL": 13,
    "CPV": 67,
    "CRO": 11,
    "CUW": 82,
    "CZE": 40,
    "ECU": 23,
    "EGY": 29,
    "ENG": 4,
    "ESP": 2,
    "FRA": 3,
    "GER": 10,
    "GHA": 73,
    "HAI": 83,
    "IRN": 20,
    "IRQ": 57,
    "JOR": 63,
    "JPN": 18,
    "KOR": 25,
    "KSA": 61,
    "MAR": 7,
    "MEX": 14,
    "NED": 8,
    "NOR": 31,
    "NZL": 85,
    "PAN": 34,
    "PAR": 41,
    "POR": 5,
    "QAT": 56,
    "RSA": 60,
    "SCO": 42,
    "SEN": 15,
    "SUI": 19,
    "SWE": 38,
    "TUN": 45,
    "TUR": 22,
    "URU": 16,
    "USA": 17,
    "UZB": 50,
}

TEAM_PROFILES = {
    name: replace(profile, fifa_rank=FIFA_RANKING_SNAPSHOT.get(profile.code, profile.fifa_rank))
    for name, profile in TEAM_PROFILES.items()
}

DEFAULT_TACTIC = TacticalTemplate(
    formation="4-2-3-1",
    style="中低位防守 + 快速推进",
    attacking_pattern="边路推进后寻找中路包抄，定位球是重要增益项",
    defensive_shape="4-4-2/4-5-1回收，优先压缩禁区前沿空间",
    set_piece="角球和前场任意球占进攻xG的稳定来源",
    risk="被迫压上时，身后空间容易被反击利用",
    starters=("候选一号", "候选二号", "候选三号", "候选四号", "候选五号", "候选六号", "候选七号", "候选八号", "候选九号", "候选十号", "候选十一号"),
    bench_options=("替补攻击手", "替补中场", "替补后卫"),
)

TEAM_TACTICS: Dict[str, TacticalTemplate] = {
    "巴西": TacticalTemplate("4-2-3-1", "高天赋前场轮转 + 边路爆点", "左路个人突破和肋部二过一制造高质量射门", "中前场反抢，边后卫压上后由后腰保护", "前场任意球和二点球冲击强", "边后卫身后空间较大", ("阿利松", "达尼洛", "马尔基尼奥斯", "加布里埃尔", "温德尔", "卡塞米罗", "吉马良斯", "罗德里戈", "帕奎塔", "维尼修斯", "理查利森"), ("恩德里克", "拉菲尼亚", "马丁内利")),
    "法国": TacticalTemplate("4-3-3", "纵深冲击 + 转换提速", "姆巴佩一侧纵深牵制，弱侧边锋后点冲击", "中场三人保护二点，丢球后快速压迫", "中卫身高优势带来定位球威胁", "阵地战遇低位密集时依赖个人爆点", ("迈尼昂", "孔德", "萨利巴", "于帕梅卡诺", "特奥", "琼阿梅尼", "拉比奥", "格列兹曼", "登贝莱", "姆巴佩", "吉鲁"), ("穆阿尼", "卡马文加", "科曼")),
    "阿根廷": TacticalTemplate("4-3-3", "控球组织 + 前场小范围配合", "右肋组织后转移左路，禁区前沿二次进攻强", "中场围抢和边路协防纪律较好", "梅西主罚定位球带来直接威胁", "节奏被拉快时中后场回追压力上升", ("马丁内斯", "莫利纳", "罗梅罗", "奥塔门迪", "塔利亚菲科", "德保罗", "恩佐", "麦卡利斯特", "梅西", "劳塔罗", "阿尔瓦雷斯"), ("迪马利亚", "洛塞尔索", "帕雷德斯")),
    "英格兰": TacticalTemplate("4-2-3-1", "强点支点 + 二线前插", "凯恩回撤串联，贝林厄姆和边锋攻击禁区", "双后腰保护中卫，边路压迫触发反击", "角球和远门柱二点威胁明显", "阵地推进过慢时容易陷入外围传导", ("皮克福德", "沃克", "斯通斯", "格伊", "肖", "赖斯", "阿诺德", "萨卡", "贝林厄姆", "福登", "凯恩"), ("帕尔默", "沃特金斯", "戈登")),
    "葡萄牙": TacticalTemplate("4-3-3", "技术控球 + 边中结合", "B费和B席在肋部制造最后一传，边路传中找禁区终结点", "中场控球防守，边后卫前插后由中卫外扩保护", "C罗/中卫头球带来强定位球价值", "前场压迫被穿透后回防距离较长", ("迪奥戈·科斯塔", "坎塞洛", "鲁本·迪亚斯", "伊纳西奥", "努诺·门德斯", "帕利尼亚", "B费", "B席", "莱奥", "C罗", "菲利克斯"), ("贡萨洛·拉莫斯", "若塔", "内维斯")),
    "西班牙": TacticalTemplate("4-3-3", "高控球 + 高位压迫", "边锋拉宽后由中场三角渗透，禁区前沿连续传切", "高位压迫和中卫前顶，尽量把对手压在半场", "短角球和二次组织质量高", "高位防线身后需要门将和中卫覆盖", ("西蒙", "卡瓦哈尔", "勒诺尔芒", "拉波尔特", "库库雷利亚", "罗德里", "佩德里", "法比安", "亚马尔", "莫拉塔", "尼科·威廉姆斯"), ("奥尔莫", "奥亚萨瓦尔", "祖比门迪")),
    "德国": TacticalTemplate("4-2-3-1", "中路技术组织 + 边路套上", "维尔茨/穆西亚拉在中路接应后打肋部穿插", "前场压迫强，后腰负责控制二点球", "中卫和高中锋定位球威胁稳定", "压上后转换防守需要控制犯规", ("诺伊尔", "基米希", "吕迪格", "塔", "米特尔施泰特", "克罗斯", "安德里希", "萨内", "穆西亚拉", "维尔茨", "哈弗茨"), ("菲尔克鲁格", "格纳布里", "格雷茨卡")),
    "荷兰": TacticalTemplate("3-4-2-1", "三中卫出球 + 边翼卫推进", "边翼卫拉开宽度，前腰在肋部连接加克波", "五后卫回收，范戴克主导防空和二点保护", "中卫群定位球压制力强", "中场人数被压制时推进会断层", ("维尔布鲁根", "德弗赖", "范戴克", "阿克", "邓弗里斯", "德容", "赖因德斯", "布林德", "西蒙斯", "加克波", "德佩"), ("马伦", "韦霍斯特", "弗林蓬")),
    "美国": TacticalTemplate("4-3-3", "高机动中场 + 边路冲击", "普利西奇和右路边锋快速推进，巴洛贡攻击中卫身后", "中场三人覆盖大，丢球后就地反抢", "麦肯尼后插上和定位球争顶有威胁", "阵地战面对低位时创造力波动", ("特纳", "德斯特", "理查兹", "里姆", "罗宾逊", "亚当斯", "麦肯尼", "穆萨", "雷纳", "普利西奇", "巴洛贡"), ("阿伦森", "佩皮", "蒂尔曼")),
    "墨西哥": TacticalTemplate("4-3-3", "主场压迫 + 边路传中", "边路推进后找中锋和后排中场，二点球跟进积极", "中场压迫触发快，领先后回到4-5-1", "劳尔·希门尼斯和中卫有高空点", "高位压迫后腰身后空间需要保护", ("马拉贡", "桑切斯", "蒙特斯", "巴斯克斯", "加利亚多", "埃德松·阿尔瓦雷斯", "路易斯·查韦斯", "皮内达", "洛萨诺", "劳尔·希门尼斯", "希门尼斯"), ("奎尼奥内斯", "安图纳", "罗莫")),
    "韩国": TacticalTemplate("4-2-3-1", "快速反击 + 二线远射", "孙兴慜左路内切，李刚仁负责肋部传球和定位球", "双后腰保护中路，边路回防纪律强", "李刚仁定位球和远射二点有威胁", "被迫控球时中锋支点稳定性一般", ("赵贤祐", "金纹奂", "金玟哉", "郑昇炫", "金珍洙", "黄仁范", "郑又荣", "李刚仁", "孙兴慜", "黄喜灿", "吴贤揆"), ("曹圭成", "洪贤锡", "严原上")),
    "日本": TacticalTemplate("4-2-3-1", "高节奏传控 + 边路小快灵", "三笘薰/久保建英边路一对一后倒三角", "前场压迫和快速回收切换成熟", "短角球和禁区前沿二点质量高", "身体对抗强度提升时中路保护压力增大", ("铃木彩艳", "菅原由势", "板仓滉", "富安健洋", "伊藤洋辉", "远藤航", "守田英正", "久保建英", "南野拓实", "三笘薰", "上田绮世"), ("堂安律", "浅野拓磨", "镰田大地")),
}

TEAM_PLAYERS: Dict[str, Tuple[PlayerProjection, ...]] = {
    "巴西": (PlayerProjection("维尼修斯", "左边锋", "爆点/终结", 0.30, "场均突破和禁区触球高"), PlayerProjection("罗德里戈", "右边锋", "内切射门", 0.22, "弱侧内切射门质量高"), PlayerProjection("理查利森", "中锋", "禁区终结", 0.24, "小禁区抢点和二点球"), PlayerProjection("帕奎塔", "前腰", "最后一传", 0.10, "肋部传球和后插上")),
    "法国": (PlayerProjection("姆巴佩", "左边锋", "核心终结", 0.34, "冲刺纵深和禁区左侧射门"), PlayerProjection("吉鲁", "中锋", "支点/头球", 0.22, "背身做球和远门柱争顶"), PlayerProjection("格列兹曼", "前腰", "组织/定位球", 0.15, "关键传球和定位球"), PlayerProjection("登贝莱", "右边锋", "突破制造", 0.14, "一对一突破和倒三角")),
    "阿根廷": (PlayerProjection("梅西", "右前场", "组织/终结", 0.28, "禁区前沿射门和直塞"), PlayerProjection("劳塔罗", "中锋", "禁区终结", 0.25, "抢点和反越位"), PlayerProjection("阿尔瓦雷斯", "前锋", "压迫/终结", 0.20, "前场反抢后射门"), PlayerProjection("恩佐", "中场", "推进/远射", 0.08, "纵向传球和二点远射")),
    "英格兰": (PlayerProjection("凯恩", "中锋", "支点/终结", 0.32, "回撤串联和禁区射门"), PlayerProjection("贝林厄姆", "前腰", "后插上", 0.22, "禁区前沿前插"), PlayerProjection("萨卡", "右边锋", "突破/传射", 0.18, "右路一对一和内切"), PlayerProjection("福登", "左前场", "肋部连接", 0.13, "小范围配合和远射")),
    "葡萄牙": (PlayerProjection("C罗", "中锋", "禁区终结", 0.30, "头球和抢点"), PlayerProjection("B费", "前腰", "传射核心", 0.18, "关键传球和远射"), PlayerProjection("莱奥", "左边锋", "爆点", 0.18, "左路推进和倒三角"), PlayerProjection("B席", "右前场", "控球连接", 0.12, "肋部控球和最后一传")),
    "西班牙": (PlayerProjection("亚马尔", "右边锋", "突破/创造", 0.20, "右路内切和传中"), PlayerProjection("莫拉塔", "中锋", "禁区终结", 0.25, "中路抢点"), PlayerProjection("尼科·威廉姆斯", "左边锋", "边路爆点", 0.18, "左路突破"), PlayerProjection("佩德里", "中场", "组织", 0.10, "肋部直塞")),
    "德国": (PlayerProjection("穆西亚拉", "前腰", "盘带创造", 0.21, "中路摆脱后射门"), PlayerProjection("维尔茨", "前腰", "最后一传", 0.18, "肋部传球和前插"), PlayerProjection("哈弗茨", "中锋", "支点/终结", 0.22, "禁区接应"), PlayerProjection("萨内", "边锋", "速度冲击", 0.14, "右路内切")),
    "荷兰": (PlayerProjection("加克波", "前锋", "终结/推进", 0.26, "左肋射门"), PlayerProjection("德佩", "中锋", "支点/定位球", 0.22, "禁区前沿射门"), PlayerProjection("西蒙斯", "前腰", "创造", 0.16, "关键传球"), PlayerProjection("邓弗里斯", "翼卫", "后点冲击", 0.10, "后点包抄")),
    "美国": (PlayerProjection("普利西奇", "左边锋", "核心传射", 0.28, "左路内切和定位球"), PlayerProjection("巴洛贡", "中锋", "纵深终结", 0.24, "反越位和禁区射门"), PlayerProjection("雷纳", "前腰", "创造", 0.14, "肋部最后一传"), PlayerProjection("麦肯尼", "中场", "后插上", 0.12, "后点争顶")),
    "墨西哥": (PlayerProjection("劳尔·希门尼斯", "中锋", "支点/点球", 0.27, "禁区抢点和点球"), PlayerProjection("希门尼斯", "前锋", "纵深终结", 0.22, "反越位跑动"), PlayerProjection("洛萨诺", "边锋", "速度冲击", 0.18, "边路突破"), PlayerProjection("路易斯·查韦斯", "中场", "远射/定位球", 0.10, "远射和任意球")),
    "韩国": (PlayerProjection("孙兴慜", "左边锋", "核心终结", 0.31, "左路内切和反击单刀"), PlayerProjection("吴贤揆", "中锋", "禁区终结", 0.22, "禁区抢点"), PlayerProjection("李刚仁", "前腰", "创造/定位球", 0.15, "关键传球和定位球"), PlayerProjection("黄喜灿", "右边锋", "冲刺", 0.16, "转换冲刺")),
    "日本": (PlayerProjection("三笘薰", "左边锋", "爆点", 0.23, "左路突破和倒三角"), PlayerProjection("久保建英", "右前场", "传射", 0.20, "右肋内切"), PlayerProjection("上田绮世", "中锋", "禁区终结", 0.22, "抢点"), PlayerProjection("南野拓实", "前腰", "二线终结", 0.14, "二线前插")),
}

TEAM_DEPTH_HINTS: Dict[str, TeamDepthHint] = {
    "南非": TeamDepthHint("4-2-3-1", "身体对抗 + 反击推进", ("威廉姆斯", "莫迪巴", "莫科埃纳", "西索勒", "马塞科", "莫科纳", "西索勒", "兹瓦内", "佩西·陶", "马耶拉", "福斯特"), ("马卡鲁", "马约", "莱帕萨"), (PlayerProjection("佩西·陶", "右边锋", "反击核心", 0.24, "转换推进和禁区前沿射门"), PlayerProjection("拉尔斯·福斯特", "中锋", "支点终结", 0.22, "背身接应和抢点"), PlayerProjection("兹瓦内", "前腰", "最后一传", 0.15, "肋部传球"))),
    "捷克": TeamDepthHint("3-4-2-1", "三中卫防空 + 二点冲击", ("斯塔涅克", "曹法尔", "霍莱什", "克雷伊奇", "兹马", "绍切克", "萨迪莱克", "普罗沃德", "赫洛热克", "切尔尼", "希克"), ("库赫塔", "林格尔", "尤拉塞克"), (PlayerProjection("帕特里克·希克", "中锋", "禁区终结", 0.30, "头球和禁区射门"), PlayerProjection("绍切克", "中场", "后插上", 0.18, "二点球和定位球"), PlayerProjection("切尔尼", "右前场", "远射制造", 0.15, "内切射门"))),
    "加拿大": TeamDepthHint("4-4-2", "速度边路 + 高位逼抢", ("克雷波", "约翰斯顿", "科内柳斯", "米勒", "阿方索·戴维斯", "埃斯塔基奥", "科内", "布坎南", "戴维", "拉林", "沙费尔伯格"), ("奥索里奥", "米拉尔", "乌格博"), (PlayerProjection("乔纳森·戴维", "前锋", "核心终结", 0.30, "反越位和点球"), PlayerProjection("拉林", "中锋", "禁区抢点", 0.24, "高球和门前包抄"), PlayerProjection("阿方索·戴维斯", "左路", "推进爆点", 0.16, "左路推进和传中"))),
    "波黑": TeamDepthHint("4-2-3-1", "中锋支点 + 中路推进", ("瓦西里", "德迪奇", "艾哈迈德霍季奇", "哈济卡杜尼奇", "科拉希纳茨", "皮亚尼奇", "塔希罗维奇", "克鲁尼奇", "德米罗维奇", "哈伊拉迪诺维奇", "哲科"), ("普雷夫利亚克", "戈亚克", "斯泰瓦诺维奇"), (PlayerProjection("哲科", "中锋", "支点终结", 0.31, "背身做球和头球"), PlayerProjection("德米罗维奇", "前锋", "冲击终结", 0.22, "禁区跑动"), PlayerProjection("皮亚尼奇", "中场", "定位球", 0.12, "任意球和关键传球"))),
    "卡塔尔": TeamDepthHint("5-3-2", "低位防守 + 双前锋反击", ("巴沙姆", "佩德罗·米格尔", "萨勒曼", "胡希", "门德斯", "阿卜杜勒萨拉姆", "海多斯", "阿萨德", "哈特姆", "阿菲夫", "阿里"), ("蒙塔里", "瓦德", "阿卜杜里萨格"), (PlayerProjection("阿克拉姆·阿菲夫", "前锋", "创造核心", 0.28, "盘带和点球"), PlayerProjection("阿尔莫埃兹·阿里", "前锋", "禁区终结", 0.25, "反击终结"), PlayerProjection("哈桑·海多斯", "中场", "组织", 0.12, "定位球和直塞"))),
    "瑞士": TeamDepthHint("3-4-2-1", "紧凑防守 + 中路二点", ("科贝尔", "阿坎吉", "舍尔", "罗德里格斯", "威德默", "扎卡", "弗罗伊勒", "埃比舍尔", "沙奇里", "恩多耶", "恩博洛"), ("奥卡福", "塞费罗维奇", "扎卡里亚"), (PlayerProjection("恩博洛", "中锋", "禁区冲击", 0.25, "身体对抗和抢点"), PlayerProjection("沙奇里", "前腰", "远射/定位球", 0.18, "左脚内切"), PlayerProjection("恩多耶", "边锋", "推进制造", 0.16, "边路一对一"))),
    "摩洛哥": TeamDepthHint("4-3-3", "边路推进 + 高强度转换", ("布努", "阿什拉夫", "阿格尔德", "赛斯", "马兹拉维", "阿姆拉巴特", "乌纳希", "阿里特", "齐耶赫", "恩内斯里", "迪亚斯"), ("阿布赫拉尔", "切迪拉", "阿布卡尔"), (PlayerProjection("恩内斯里", "中锋", "高空终结", 0.27, "头球和门前抢点"), PlayerProjection("齐耶赫", "右边锋", "传射核心", 0.19, "内切和定位球"), PlayerProjection("迪亚斯", "前场", "肋部创造", 0.18, "盘带和最后一传"))),
    "海地": TeamDepthHint("4-4-2", "快速反击 + 边路冲刺", ("普拉西德", "阿德", "梅切", "杰罗姆", "阿尔塞乌斯", "皮埃罗", "贝尔福特", "纳松", "杜肯斯", "达克斯", "埃利安"), ("安布鲁瓦", "巴泽", "圣路易斯"), (PlayerProjection("弗朗茨迪·皮埃罗", "前锋", "纵深终结", 0.29, "反击跑动"), PlayerProjection("纳松", "边锋", "速度冲击", 0.20, "边路突破"), PlayerProjection("杜肯斯", "中场", "二线射门", 0.12, "二点球"))),
    "苏格兰": TeamDepthHint("3-4-2-1", "三中卫 + 传中压迫", ("冈恩", "亨德里", "蒂尔尼", "麦肯纳", "希基", "麦克托米奈", "麦金", "罗伯逊", "克里斯蒂", "麦克金", "切·亚当斯"), ("戴克斯", "吉尔摩", "福雷斯特"), (PlayerProjection("麦克托米奈", "中场", "后插上", 0.24, "禁区前插"), PlayerProjection("切·亚当斯", "中锋", "支点终结", 0.22, "背身接应"), PlayerProjection("罗伯逊", "左翼卫", "传中创造", 0.12, "左路传中"))),
    "巴拉圭": TeamDepthHint("4-2-3-1", "强对抗 + 定位球", ("科罗内尔", "埃斯皮诺萨", "巴尔布埃纳", "阿尔德雷特", "阿隆索", "库巴斯", "维拉桑蒂", "阿尔米隆", "罗梅罗", "索萨", "萨纳夫里亚"), ("阿瓦洛斯", "恩西索", "梅迪纳"), (PlayerProjection("阿尔米隆", "右边锋", "推进核心", 0.24, "快速推进和内切"), PlayerProjection("萨纳夫里亚", "中锋", "禁区终结", 0.23, "门前抢点"), PlayerProjection("罗梅罗", "前腰", "二线射门", 0.15, "远射和定位球"))),
    "澳大利亚": TeamDepthHint("4-2-3-1", "身体对抗 + 定位球", ("瑞安", "阿特金森", "苏塔", "罗尔斯", "贝希奇", "欧文", "巴库斯", "博伊尔", "赫鲁斯蒂奇", "古德温", "杜克"), ("延吉", "麦格里", "蒂利奥"), (PlayerProjection("米切尔·杜克", "中锋", "禁区抢点", 0.24, "高空球和二点"), PlayerProjection("古德温", "左边锋", "传射", 0.18, "定位球和传中"), PlayerProjection("赫鲁斯蒂奇", "前腰", "远射/定位球", 0.15, "左脚远射"))),
    "土耳其": TeamDepthHint("4-2-3-1", "技术中场 + 边路内切", ("恰基尔", "切利克", "德米拉尔", "巴达克", "卡迪奥卢", "恰尔汗奥卢", "尤克塞克", "云代尔", "居莱尔", "阿克图尔科卢", "伊尔马兹"), ("托松", "科克库", "亚兹哲"), (PlayerProjection("恰尔汗奥卢", "中场", "远射/定位球", 0.18, "任意球和长传"), PlayerProjection("居莱尔", "前腰", "创造", 0.17, "肋部最后一传"), PlayerProjection("伊尔马兹", "前锋", "冲击终结", 0.22, "纵深跑动"))),
    "库拉索": TeamDepthHint("4-2-3-1", "低位防守 + 单点反击", ("鲁姆", "马蒂纳", "范埃伊玛", "巴库纳", "费利达", "巴库纳", "安东尼亚", "霍伊", "纳尔辛格", "佐纳", "扬加"), ("科尔多瓦", "埃利亚", "玛格丽塔"), (PlayerProjection("扬加", "中锋", "支点终结", 0.26, "禁区对抗"), PlayerProjection("纳尔辛格", "边锋", "速度推进", 0.18, "边路冲刺"), PlayerProjection("霍伊", "前腰", "定位球", 0.13, "定位球输送"))),
    "科特迪瓦": TeamDepthHint("4-3-3", "身体压制 + 边路强突", ("福法纳", "奥里耶", "迪奥曼德", "恩迪卡", "科南", "凯西", "桑加雷", "福法纳", "阿丁格拉", "哈勒", "佩佩"), ("克拉索", "博加", "迪亚基特"), (PlayerProjection("哈勒", "中锋", "禁区终结", 0.28, "高点和点球"), PlayerProjection("阿丁格拉", "边锋", "突破制造", 0.20, "一对一和传中"), PlayerProjection("凯西", "中场", "后插上", 0.14, "二线前插"))),
    "厄瓜多尔": TeamDepthHint("4-2-3-1", "高强度逼抢 + 边路推进", ("加林德斯", "普雷西亚多", "帕乔", "因卡皮耶", "埃斯图皮尼安", "凯塞多", "格鲁埃索", "普拉塔", "派斯", "萨米恩托", "恩纳·瓦伦西亚"), ("罗德里格斯", "梅纳", "弗朗哥"), (PlayerProjection("恩纳·瓦伦西亚", "中锋", "核心终结", 0.29, "点球和禁区射门"), PlayerProjection("凯塞多", "中场", "推进/二点", 0.12, "抢断后推进"), PlayerProjection("派斯", "前腰", "创造", 0.16, "肋部突破"))),
    "瑞典": TeamDepthHint("4-4-2", "双前锋 + 边路传中", ("奥尔森", "克拉夫特", "林德洛夫", "希恩", "奥古斯丁松", "库卢塞夫斯基", "卡尤斯特", "斯万贝里", "福斯贝里", "伊萨克", "哲凯赖什"), ("埃兰加", "克莱松", "夸伊森"), (PlayerProjection("伊萨克", "前锋", "核心终结", 0.29, "禁区内射门"), PlayerProjection("哲凯赖什", "前锋", "冲击终结", 0.27, "纵深推进"), PlayerProjection("库卢塞夫斯基", "右路", "创造", 0.17, "内切传射"))),
    "突尼斯": TeamDepthHint("4-3-3", "紧凑防守 + 直接反击", ("达门", "德拉格尔", "塔勒比", "布龙", "阿卜迪", "莱杜尼", "斯希里", "哈兹里", "姆萨克尼", "杰巴利", "斯利蒂"), ("拉伊杜尼", "赫尼斯", "梅布里"), (PlayerProjection("姆萨克尼", "前场", "核心传射", 0.22, "禁区前沿处理"), PlayerProjection("哈兹里", "前锋", "定位球/终结", 0.20, "任意球和远射"), PlayerProjection("杰巴利", "中锋", "支点", 0.18, "背身做球"))),
    "比利时": TeamDepthHint("4-2-3-1", "控球推进 + 中锋支点", ("库尔图瓦", "卡斯塔涅", "维尔通亨", "费斯", "泰特", "奥纳纳", "蒂莱曼斯", "多库", "德布劳内", "特罗萨德", "卢卡库"), ("奥蓬达", "巴卡约科", "卡拉斯科"), (PlayerProjection("卢卡库", "中锋", "禁区终结", 0.32, "小禁区触球"), PlayerProjection("德布劳内", "前腰", "创造核心", 0.20, "关键传球"), PlayerProjection("多库", "边锋", "突破制造", 0.17, "一对一突破"))),
    "埃及": TeamDepthHint("4-3-3", "右路核心 + 快速转换", ("埃尔谢纳维", "哈尼", "赫加齐", "阿卜杜勒莫内姆", "哈姆迪", "埃尔内尼", "法蒂", "特雷泽盖", "萨拉赫", "马尔穆什", "穆斯塔法"), ("科卡", "齐佐", "阿什拉夫"), (PlayerProjection("萨拉赫", "右边锋", "核心终结", 0.34, "内切射门和点球"), PlayerProjection("马尔穆什", "前锋", "纵深冲击", 0.22, "反击跑动"), PlayerProjection("特雷泽盖", "左边锋", "二线终结", 0.15, "后点包抄"))),
    "伊朗": TeamDepthHint("4-2-3-1", "强硬防守 + 双前锋轮转", ("贝兰万德", "雷扎伊安", "卡纳尼", "普拉利甘吉", "莫哈马迪", "埃扎托拉希", "努罗拉希", "贾汉巴赫什", "高多斯", "塔雷米", "阿兹蒙"), ("安萨里法德", "莫赫比", "古利扎德"), (PlayerProjection("塔雷米", "前锋", "传射核心", 0.30, "点球和禁区跑动"), PlayerProjection("阿兹蒙", "中锋", "禁区终结", 0.26, "头球和抢点"), PlayerProjection("贾汉巴赫什", "边锋", "远射", 0.14, "右路内切"))),
    "新西兰": TeamDepthHint("4-4-2", "身体对抗 + 定位球", ("伍德", "佩恩", "皮纳克", "图伊洛马", "卡卡塞", "贝尔", "斯塔门尼奇", "加贝特", "贾斯特", "辛格", "克里斯·伍德"), ("韦恩", "麦考瓦特", "罗哈斯"), (PlayerProjection("克里斯·伍德", "中锋", "高空终结", 0.34, "头球和门前抢点"), PlayerProjection("辛格", "前腰", "创造/远射", 0.17, "禁区前沿射门"), PlayerProjection("加贝特", "边路", "传中", 0.12, "边路输送"))),
    "佛得角": TeamDepthHint("4-3-3", "边路速度 + 防守反击", ("沃齐尼亚", "斯托皮拉", "洛佩斯", "塞梅多", "福尔塔多", "安德拉德", "罗沙", "蒙泰罗", "贝贝", "门德斯", "卡布拉尔"), ("塔瓦雷斯", "杜阿尔特", "桑托斯"), (PlayerProjection("贝贝", "边锋", "远射/终结", 0.22, "远射和定位球"), PlayerProjection("瑞安·门德斯", "前锋", "反击终结", 0.21, "纵深跑动"), PlayerProjection("若万·卡布拉尔", "边锋", "突破制造", 0.18, "一对一"))),
    "沙特阿拉伯": TeamDepthHint("4-3-3", "控球推进 + 高位压迫", ("奥韦斯", "布莱克", "坦巴克蒂", "阿姆里", "沙赫拉尼", "卡诺", "法拉吉", "马尔基", "多萨里", "谢赫里", "布赖坎"), ("穆瓦拉德", "加里卜", "阿卜杜勒哈米德"), (PlayerProjection("萨勒姆·多萨里", "左边锋", "核心传射", 0.27, "内切和点球"), PlayerProjection("布赖坎", "前锋", "禁区终结", 0.23, "抢点"), PlayerProjection("谢赫里", "中锋", "支点", 0.18, "背身接应"))),
    "乌拉圭": TeamDepthHint("4-3-3", "高压逼抢 + 强力中锋", ("罗切特", "南德斯", "希门尼斯", "阿劳霍", "奥利韦拉", "乌加特", "巴尔韦德", "本坦库尔", "佩利斯特里", "努涅斯", "德拉克鲁斯"), ("苏亚雷斯", "卡诺比奥", "阿拉斯凯塔"), (PlayerProjection("努涅斯", "中锋", "纵深终结", 0.31, "冲刺和禁区射门"), PlayerProjection("巴尔韦德", "中场", "远射推进", 0.14, "远射和二线前插"), PlayerProjection("德拉克鲁斯", "前场", "创造", 0.15, "肋部传球"))),
    "塞内加尔": TeamDepthHint("4-3-3", "身体速度 + 边路爆点", ("门迪", "萨巴利", "库利巴利", "迪亚洛", "雅各布斯", "盖耶", "门迪", "库亚特", "萨尔", "马内", "迪亚"), ("杰克逊", "迪耶迪乌", "恩迪亚耶"), (PlayerProjection("马内", "左边锋", "核心终结", 0.30, "内切和点球"), PlayerProjection("伊斯梅拉·萨尔", "右边锋", "速度冲击", 0.18, "右路纵深"), PlayerProjection("尼古拉斯·杰克逊", "前锋", "冲击终结", 0.20, "禁区跑动"))),
    "伊拉克": TeamDepthHint("4-2-3-1", "紧凑防守 + 前场单点", ("哈桑", "多斯基", "纳提克", "阿里", "亚辛", "巴耶什", "阿米尔", "阿塔万", "侯赛因·阿里", "阿德南", "艾曼·侯赛因"), ("穆罕默德·阿里", "拉希德", "阿明"), (PlayerProjection("艾曼·侯赛因", "中锋", "禁区终结", 0.31, "高球和点球"), PlayerProjection("侯赛因·阿里", "右路", "突破制造", 0.17, "边路推进"), PlayerProjection("巴耶什", "中场", "二线远射", 0.13, "远射和定位球"))),
    "挪威": TeamDepthHint("4-3-3", "强力中锋 + 直塞纵深", ("尼兰德", "佩德森", "阿耶尔", "厄斯蒂高", "梅林", "贝格", "厄德高", "托尔斯特维特", "索尔洛特", "哈兰德", "鲍勃"), ("努萨", "海于格", "伯格"), (PlayerProjection("哈兰德", "中锋", "核心终结", 0.39, "禁区射门和点球"), PlayerProjection("厄德高", "前腰", "创造核心", 0.18, "直塞和远射"), PlayerProjection("索尔洛特", "前锋", "支点", 0.20, "高球和背身"))),
    "阿尔及利亚": TeamDepthHint("4-2-3-1", "右路创造 + 技术推进", ("曼德雷亚", "阿塔尔", "本塞拜尼", "图巴", "艾特努里", "本纳赛尔", "费古利", "马赫雷斯", "阿乌阿尔", "贝莱利", "布内贾"), ("古伊里", "德洛尔", "泽鲁基"), (PlayerProjection("马赫雷斯", "右边锋", "核心传射", 0.28, "内切和定位球"), PlayerProjection("古伊里", "前锋", "禁区终结", 0.22, "跑位和射门"), PlayerProjection("本纳赛尔", "中场", "推进", 0.10, "纵向传球"))),
    "奥地利": TeamDepthHint("4-2-3-1", "高位压迫 + 快速纵向", ("彭茨", "波施", "林哈特", "丹索", "姆韦内", "莱默尔", "赛瓦尔德", "萨比策", "鲍姆加特纳", "格里利奇", "阿瑙托维奇"), ("格雷戈里奇", "魏曼", "施密德"), (PlayerProjection("阿瑙托维奇", "中锋", "支点终结", 0.25, "背身和点球"), PlayerProjection("萨比策", "前腰", "远射/定位球", 0.19, "远射和任意球"), PlayerProjection("鲍姆加特纳", "前场", "后插上", 0.17, "二线前插"))),
    "约旦": TeamDepthHint("3-4-2-1", "低位组织 + 快速反击", ("阿布莱拉", "纳西布", "阿拉布", "阿贾林", "哈达德", "拉什丹", "马尔迪", "阿尔纳伊马特", "塔马里", "奥尔万", "阿布扎雷克"), ("费萨尔", "萨米尔", "阿纳斯"), (PlayerProjection("穆萨·塔马里", "右前场", "核心突破", 0.31, "边路突破和内切"), PlayerProjection("阿尔纳伊马特", "前锋", "反击终结", 0.24, "纵深跑位"), PlayerProjection("奥尔万", "前场", "二线射门", 0.14, "禁区前沿射门"))),
    "民主刚果": TeamDepthHint("4-3-3", "身体压迫 + 快速边锋", ("姆帕西", "卡卢卢", "姆本巴", "巴图宾西卡", "马苏亚库", "卡库塔", "皮克尔", "姆武帕", "巴坎布", "维萨", "埃利亚"), ("西拉斯", "邦贡达", "穆莱卡"), (PlayerProjection("维萨", "前锋", "终结/推进", 0.25, "禁区跑动"), PlayerProjection("巴坎布", "中锋", "禁区终结", 0.24, "门前抢点"), PlayerProjection("西拉斯", "边锋", "速度冲击", 0.18, "纵深冲刺"))),
    "乌兹别克斯坦": TeamDepthHint("3-4-2-1", "防守纪律 + 肋部推进", ("尤苏波夫", "阿利库洛夫", "阿舒尔马托夫", "埃什穆罗多夫", "赛菲耶夫", "舒库罗夫", "哈姆罗别科夫", "图尔贡博耶夫", "马沙里波夫", "法伊祖拉耶夫", "肖穆罗多夫"), ("乌鲁诺夫", "谢尔盖耶夫", "纳斯鲁拉耶夫"), (PlayerProjection("肖穆罗多夫", "中锋", "核心终结", 0.30, "禁区射门和支点"), PlayerProjection("法伊祖拉耶夫", "前腰", "创造", 0.17, "肋部带球"), PlayerProjection("马沙里波夫", "边前腰", "传射", 0.16, "定位球和传中"))),
    "哥伦比亚": TeamDepthHint("4-2-3-1", "技术前腰 + 边路强点", ("巴尔加斯", "穆尼奥斯", "桑切斯", "卢库米", "莫希卡", "莱尔马", "里奥斯", "迪亚斯", "哈梅斯", "阿里亚斯", "博雷"), ("杜兰", "科尔多瓦", "金特罗"), (PlayerProjection("路易斯·迪亚斯", "左边锋", "核心爆点", 0.28, "左路突破和射门"), PlayerProjection("哈梅斯", "前腰", "创造/定位球", 0.19, "最后一传和定位球"), PlayerProjection("杜兰", "中锋", "冲击终结", 0.21, "禁区冲击"))),
    "克罗地亚": TeamDepthHint("4-3-3", "中场控球 + 节奏控制", ("利瓦科维奇", "尤拉诺维奇", "舒塔洛", "格瓦迪奥尔", "索萨", "布罗佐维奇", "莫德里奇", "科瓦契奇", "克拉马里奇", "佩里西奇", "布迪米尔"), ("马耶尔", "帕萨利奇", "佩特科维奇"), (PlayerProjection("克拉马里奇", "前锋", "禁区终结", 0.24, "小范围射门"), PlayerProjection("莫德里奇", "中场", "组织/定位球", 0.12, "关键传球"), PlayerProjection("佩里西奇", "边路", "后点冲击", 0.15, "后点包抄"))),
    "加纳": TeamDepthHint("4-2-3-1", "身体冲击 + 边路速度", ("阿蒂齐吉", "兰普泰", "阿马泰", "萨利苏", "巴巴", "托马斯", "萨梅德", "库杜斯", "阿尤", "苏莱马纳", "伊尼亚基·威廉姆斯"), ("塞梅尼奥", "奥斯曼·布卡里", "乔丹·阿尤"), (PlayerProjection("库杜斯", "前腰", "核心传射", 0.27, "盘带和远射"), PlayerProjection("伊尼亚基·威廉姆斯", "中锋", "纵深终结", 0.24, "反越位"), PlayerProjection("塞梅尼奥", "前锋", "冲击终结", 0.18, "身体冲撞和射门"))),
    "巴拿马": TeamDepthHint("5-4-1", "紧凑防守 + 定位球", ("梅希亚", "穆里略", "科尔多瓦", "安德拉德", "戴维斯", "黑水", "戈多伊", "卡拉斯基利亚", "巴尔塞纳斯", "法哈尔多", "迪亚斯"), ("沃特曼", "金特罗", "亚尼斯"), (PlayerProjection("卡拉斯基利亚", "中场", "推进组织", 0.18, "纵向推进"), PlayerProjection("法哈尔多", "前锋", "禁区终结", 0.23, "门前抢点"), PlayerProjection("巴尔塞纳斯", "边路", "定位球", 0.15, "传中和任意球"))),
}

TEAM_DISCIPLINE: Dict[str, DisciplineStatus] = {}

TEAM_ALIASES = {
    "Mexico": "墨西哥", "MEX": "墨西哥",
    "South Africa": "南非", "RSA": "南非",
    "Korea Republic": "韩国", "South Korea": "韩国", "KOR": "韩国",
    "Czech Republic": "捷克", "Czechia": "捷克", "CZE": "捷克",
    "Canada": "加拿大", "CAN": "加拿大",
    "Bosnia and Herzegovina": "波黑", "BIH": "波黑",
    "Qatar": "卡塔尔", "QAT": "卡塔尔",
    "Switzerland": "瑞士", "SUI": "瑞士",
    "Brazil": "巴西", "BRA": "巴西",
    "Morocco": "摩洛哥", "MAR": "摩洛哥",
    "Haiti": "海地", "HAI": "海地",
    "Scotland": "苏格兰", "SCO": "苏格兰",
    "United States": "美国", "USA": "美国",
    "Paraguay": "巴拉圭", "PAR": "巴拉圭",
    "Australia": "澳大利亚", "AUS": "澳大利亚",
    "Türkiye": "土耳其", "Turkiye": "土耳其", "Turkey": "土耳其", "TUR": "土耳其",
    "Germany": "德国", "GER": "德国", "DEU": "德国",
    "Curacao": "库拉索", "Curaçao": "库拉索", "CUW": "库拉索",
    "Cote d'Ivoire": "科特迪瓦", "Ivory Coast": "科特迪瓦", "CIV": "科特迪瓦",
    "Ecuador": "厄瓜多尔", "ECU": "厄瓜多尔",
    "Netherlands": "荷兰", "NED": "荷兰",
    "Japan": "日本", "JPN": "日本",
    "Sweden": "瑞典", "SWE": "瑞典",
    "Tunisia": "突尼斯", "TUN": "突尼斯",
    "Belgium": "比利时", "BEL": "比利时",
    "Egypt": "埃及", "EGY": "埃及",
    "Iran": "伊朗", "IRN": "伊朗",
    "New Zealand": "新西兰", "NZL": "新西兰",
    "Spain": "西班牙", "ESP": "西班牙",
    "Cape Verde": "佛得角", "CPV": "佛得角",
    "Saudi Arabia": "沙特阿拉伯", "KSA": "沙特阿拉伯",
    "Uruguay": "乌拉圭", "URU": "乌拉圭",
    "France": "法国", "FRA": "法国",
    "Senegal": "塞内加尔", "SEN": "塞内加尔",
    "Iraq": "伊拉克", "IRQ": "伊拉克",
    "Norway": "挪威", "NOR": "挪威",
    "Argentina": "阿根廷", "ARG": "阿根廷",
    "Algeria": "阿尔及利亚", "ALG": "阿尔及利亚",
    "Austria": "奥地利", "AUT": "奥地利",
    "Jordan": "约旦", "JOR": "约旦",
    "Portugal": "葡萄牙", "POR": "葡萄牙",
    "DR Congo": "民主刚果", "Congo DR": "民主刚果", "COD": "民主刚果",
    "Uzbekistan": "乌兹别克斯坦", "UZB": "乌兹别克斯坦",
    "Colombia": "哥伦比亚", "COL": "哥伦比亚",
    "England": "英格兰", "ENG": "英格兰",
    "Croatia": "克罗地亚", "CRO": "克罗地亚",
    "Ghana": "加纳", "GHA": "加纳",
    "Panama": "巴拿马", "PAN": "巴拿马",
}


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _team(name: str) -> TeamProfile:
    key = TEAM_ALIASES.get(name, name)
    if key in TEAM_PROFILES:
        return TEAM_PROFILES[key]
    return TeamProfile(name=name, code=name[:3].upper(), fifa_rank=80, elo_rating=1500, confederation="UNK")


def _ranking_snapshot_payload(home: TeamProfile, away: TeamProfile) -> Dict:
    return {
        **FIFA_RANKING_SOURCE,
        "teams": {
            "home": {"team": home.name, "code": home.code, "rank": home.fifa_rank},
            "away": {"team": away.name, "code": away.code, "rank": away.fifa_rank},
        },
    }


def _form_score(team: TeamProfile) -> float:
    rank_score = _clip((80 - team.fifa_rank) / 12, 0, 5.5)
    elo_score = _clip((team.elo_rating - 1450) / 145, 0, 4.2)
    pedigree = min(team.titles * 0.18, 0.6)
    debut_penalty = -0.25 if team.is_debut else 0
    return _clip(3.5 + rank_score * 0.55 + elo_score * 0.45 + pedigree + debut_penalty, 3.8, 9.4)


def _review_side_context(review_adjustment: Optional[Mapping[str, Any]], side: str) -> Mapping[str, Any]:
    if not isinstance(review_adjustment, Mapping):
        return {}
    review_context = review_adjustment.get("review_context")
    if not isinstance(review_context, Mapping):
        return {}
    form_context = review_context.get("form_context")
    if not isinstance(form_context, Mapping):
        return {}
    side_context = form_context.get(side)
    return side_context if isinstance(side_context, Mapping) else {}


def _resolved_form_score(team: TeamProfile, review_adjustment: Optional[Mapping[str, Any]], side: str) -> Tuple[float, str]:
    context = _review_side_context(review_adjustment, side)
    score = context.get("score")
    if score is not None:
        try:
            return _clip(float(score), 3.8, 9.4), str(context.get("source_label") or "本届世界杯正式赛窗口")
        except (TypeError, ValueError):
            pass
    return _form_score(team), "赛前基础状态"


def _advantage_points(side: str, level: str) -> int:
    points = 95 if level == "full" else 48 if level == "half" else 0
    if side == "home":
        return points
    if side == "away":
        return -points
    return 0


def _is_host_team(team: TeamProfile) -> bool:
    return team.code in {"USA", "MEX", "CAN"}


def _poisson(lambda_: float, goals: int) -> float:
    return (lambda_ ** goals * math.exp(-lambda_)) / math.factorial(goals)


def _dixon_coles_tau(home_goals: int, away_goals: int, xg_home: float, xg_away: float, rho: float = -0.075) -> float:
    if home_goals == 0 and away_goals == 0:
        return max(0.01, 1 - xg_home * xg_away * rho)
    if home_goals == 0 and away_goals == 1:
        return max(0.01, 1 + xg_home * rho)
    if home_goals == 1 and away_goals == 0:
        return max(0.01, 1 + xg_away * rho)
    if home_goals == 1 and away_goals == 1:
        return max(0.01, 1 - rho)
    return 1.0


def _score_matrix(xg_home: float, xg_away: float, use_dc: bool = True) -> List[Tuple[int, int, float]]:
    matrix: List[Tuple[int, int, float]] = []
    for home_goals in range(9):
        for away_goals in range(9):
            prob = _poisson(xg_home, home_goals) * _poisson(xg_away, away_goals)
            if use_dc:
                prob *= _dixon_coles_tau(home_goals, away_goals, xg_home, xg_away)
            matrix.append((home_goals, away_goals, prob))
    total = sum(prob for _, _, prob in matrix) or 1
    return [(h, a, prob / total) for h, a, prob in matrix]


def _weather_scale(weather: Optional[str]) -> Tuple[float, str]:
    mapping = {
        "rain": (0.94, "雨天/湿滑：降低节奏，但定位球和门将脱手风险会上升"),
        "storm": (0.88, "暴雨/强对流：明显压低地面推进效率"),
        "hot": (0.96, "高温闷热：体能下降，比赛节奏小幅下调"),
        "wind": (0.96, "大风：传中、长传稳定性下降，远射波动增加"),
        "normal": (1.0, "天气：常规条件"),
        None: (1.0, "天气：常规条件"),
    }
    return mapping.get(weather, mapping["normal"])


def _stage_scale(stage: Optional[str], match_round: Optional[int], is_knockout: bool) -> Tuple[float, str]:
    if stage == "Third-place":
        return 1.14, "季军赛：战意和轮换异常，开放比赛权重上升"
    if stage == "Final":
        return 0.93, "决赛：风险控制更强，总进球略降"
    if is_knockout:
        return 0.97, "淘汰赛：先求稳，但强队换人深度会保留后程进球权重"
    if match_round == 1:
        return 0.99, "小组赛首轮：试探因素存在，但开幕阶段进攻意愿保留"
    if match_round == 2:
        return 1.02, "小组赛第二轮：抢分关键战，节奏略升"
    if match_round == 3:
        return 1.08, "小组赛末轮：战意/轮换变量放大，总进球波动上升"
    return 1.0, "赛事阶段：常规赛程权重"


def _int_or_none(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _third_round_status(side_state: Mapping[str, Any]) -> str:
    explicit = str(side_state.get("status") or "").strip().lower()
    if explicit in {"locked_first", "near_qualified", "must_win", "edge"}:
        return explicit
    points = _int_or_none(side_state.get("points"))
    rank = _int_or_none(side_state.get("rank"))
    if points is None:
        return "unknown"
    if rank == 1 and points >= 6:
        return "locked_first"
    if rank is not None and rank <= 2 and points >= 4:
        return "near_qualified"
    if points <= 1:
        return "must_win"
    if points == 3 or (rank is not None and rank >= 3):
        return "edge"
    return "unknown"


def _third_round_strategy_adjustment(
    match_round: Optional[int],
    review_adjustment: Optional[Mapping[str, Any]],
    home: TeamProfile,
    away: TeamProfile,
) -> Dict[str, Any]:
    if int(match_round or 0) != 3 or not isinstance(review_adjustment, Mapping):
        return {"applied": False}
    review_context = review_adjustment.get("review_context")
    if not isinstance(review_context, Mapping) or review_context.get("mode") != "third_round_group_strategy":
        return {"applied": False}

    strategy = review_context.get("third_round_strategy")
    if not isinstance(strategy, Mapping):
        strategy = {}
    home_state = strategy.get("home") if isinstance(strategy.get("home"), Mapping) else {}
    away_state = strategy.get("away") if isinstance(strategy.get("away"), Mapping) else {}
    home_status = _third_round_status(home_state)
    away_status = _third_round_status(away_state)
    if home_status == "unknown" and away_status == "unknown":
        return {"applied": False}

    home_multiplier = 1.0
    away_multiplier = 1.0
    total_multiplier = 1.0
    draw_delta = 0.0
    notes: List[str] = ["出线形势高权重"]

    statuses = {home_status, away_status}
    if home_status == "near_qualified" and away_status == "near_qualified":
        home_multiplier *= 0.98
        away_multiplier *= 0.98
        total_multiplier *= 0.94
        draw_delta += 0.04
        notes.append("双方接近出线区，优先稳住不败，平局/小比分权重上调")
    elif "must_win" in statuses:
        if home_status == "must_win":
            home_multiplier *= 1.12
            away_multiplier *= 1.02
            notes.append(f"{home.name}必须争胜，主动提速和弱侧xG上调")
        if away_status == "must_win":
            away_multiplier *= 1.12
            home_multiplier *= 1.02
            notes.append(f"{away.name}必须争胜，主动提速和弱侧xG上调")
        if home_status == "locked_first":
            home_multiplier *= 0.99
            notes.append(f"{home.name}已接近锁定第一，轮换保护但反击空间仍保留")
        if away_status == "locked_first":
            away_multiplier *= 0.99
            notes.append(f"{away.name}已接近锁定第一，轮换保护但反击空间仍保留")
        total_multiplier *= 1.03
    elif "locked_first" in statuses:
        if home_status == "locked_first":
            home_multiplier *= 0.95
            notes.append(f"{home.name}小组第一主动权高，轮换保护和控节奏上升")
        if away_status == "locked_first":
            away_multiplier *= 0.95
            notes.append(f"{away.name}小组第一主动权高，轮换保护和控节奏上升")
        total_multiplier *= 0.96
        draw_delta += 0.025
    elif "edge" in statuses:
        if home_status == "edge":
            home_multiplier *= 1.05
            notes.append(f"{home.name}出线边缘，抢分/净胜球动机上升")
        if away_status == "edge":
            away_multiplier *= 1.05
            notes.append(f"{away.name}出线边缘，抢分/净胜球动机上升")
        total_multiplier *= 1.01
        draw_delta += 0.012

    path_weight = str(strategy.get("path_weight") or review_context.get("path_weight") or "low").strip().lower()
    if path_weight in {"medium", "high"} and "must_win" not in statuses:
        path_delta = 0.018 if path_weight == "medium" else 0.028
        draw_delta += path_delta
        total_multiplier *= 0.98
        notes.append(f"潜在路径{path_weight}权重触发，名次选择只做条件校准")
    else:
        notes.append("潜在路径低权重，不直接假设主动挑对手")

    return {
        "applied": True,
        "home_xg_multiplier": round(_clip(home_multiplier, 0.90, 1.14), 3),
        "away_xg_multiplier": round(_clip(away_multiplier, 0.90, 1.14), 3),
        "total_xg_multiplier": round(_clip(total_multiplier, 0.90, 1.08), 3),
        "draw_probability_delta": round(_clip(draw_delta, 0.0, 0.065), 4),
        "draw_probability_cap": 0.50,
        "notes": notes[:4],
    }


def _venue_scale(venue_factor: Optional[str]) -> Tuple[float, str]:
    mapping = {
        "high_altitude": (0.97, "高海拔场地：体能消耗增加，但远射和定位球波动上升"),
        "indoor": (1.03, "顶棚/室内场地：天气扰动降低，技术发挥更稳定"),
        "normal": (1.0, "场地：常规条件"),
        None: (1.0, "场地：常规条件"),
    }
    return mapping.get(venue_factor, mapping["normal"])


def _round2(value: float) -> float:
    return round(value + 1e-9, 2)


def _round3(value: float) -> float:
    return round(value + 1e-9, 3)


def _score_outcome(home_goals: int, away_goals: int) -> str:
    if home_goals > away_goals:
        return "home"
    if home_goals < away_goals:
        return "away"
    return "draw"


def _calibrated_score_matrix(
    matrix: List[Tuple[int, int, float]],
    probabilities: Dict[str, float],
    home_xg: float,
    away_xg: float,
) -> List[Tuple[int, int, float]]:
    favorite_outcome, favorite_probability = max(
        (("home", probabilities.get("home", 0.0)), ("away", probabilities.get("away", 0.0))),
        key=lambda item: item[1],
    )
    draw_probability = probabilities.get("draw", 0.0)
    xg_edge = abs(home_xg - away_xg)
    draw_mode_penalty = (
        favorite_probability >= 0.5
        and favorite_probability - draw_probability >= 0.24
        and xg_edge >= 0.45
        and home_xg + away_xg >= 2.35
    )
    outcome_totals = {
        "home": sum(prob for h, a, prob in matrix if h > a),
        "draw": sum(prob for h, a, prob in matrix if h == a),
        "away": sum(prob for h, a, prob in matrix if h < a),
    }
    calibrated: List[Tuple[int, int, float]] = []
    for home_goals, away_goals, prob in matrix:
        outcome = _score_outcome(home_goals, away_goals)
        outcome_total = outcome_totals.get(outcome) or 1
        adjusted = prob * (probabilities.get(outcome, 0) / outcome_total)
        if draw_mode_penalty and outcome == "draw":
            adjusted *= 0.72
        if draw_mode_penalty and outcome == favorite_outcome:
            adjusted *= 1.04
        if (
            probabilities.get("home", 0) >= 0.6
            and home_xg - away_xg >= 0.95
            and away_xg <= 1.12
            and home_goals > away_goals
            and away_goals == 0
        ):
            adjusted *= 1.16
        if (
            probabilities.get("away", 0) >= 0.6
            and away_xg - home_xg >= 0.95
            and home_xg <= 1.12
            and away_goals > home_goals
            and home_goals == 0
        ):
            adjusted *= 1.16
        calibrated.append((home_goals, away_goals, adjusted))

    total = sum(prob for _, _, prob in calibrated) or 1
    return [(h, a, prob / total) for h, a, prob in calibrated]


def _matrix_probability(matrix: List[Tuple[int, int, float]], home_goals: int, away_goals: int) -> float:
    return next((prob for h, a, prob in matrix if h == home_goals and a == away_goals), 0.0)


def _score_from_xg(
    matrix: List[Tuple[int, int, float]],
    home_xg: float,
    away_xg: float,
    preferred_outcome: str,
) -> Optional[Tuple[int, int, float]]:
    diff = home_xg - away_xg
    favorite_xg = max(home_xg, away_xg)
    underdog_xg = min(home_xg, away_xg)

    if abs(diff) < 1.05:
        return None

    favorite_goals = int(round(favorite_xg + 0.35))
    if favorite_xg >= 3.05 and underdog_xg <= 0.78:
        favorite_goals = 4
    elif favorite_xg >= 2.25:
        favorite_goals = max(favorite_goals, 3)
    else:
        favorite_goals = max(favorite_goals, 2)

    underdog_goals = 0 if underdog_xg < 0.82 else 1 if underdog_xg < 1.22 else int(round(underdog_xg))
    favorite_goals = int(_clip(favorite_goals, 2, 5))
    underdog_goals = int(_clip(underdog_goals, 0, 3))

    if diff > 0 and preferred_outcome == "home":
        candidate = (favorite_goals, underdog_goals)
    elif diff < 0 and preferred_outcome == "away":
        candidate = (underdog_goals, favorite_goals)
    else:
        return None

    prob = _matrix_probability(matrix, candidate[0], candidate[1])
    return (candidate[0], candidate[1], prob) if prob > 0 else None


def _select_representative_score(
    matrix: List[Tuple[int, int, float]],
    expected_total: float,
    home_xg: float,
    away_xg: float,
    preferred_outcome: Optional[str] = None,
) -> Tuple[int, int, float]:
    ranked = sorted(matrix, key=lambda item: item[2], reverse=True)
    mode_home, mode_away, _ = ranked[0]
    target_outcome = preferred_outcome or _score_outcome(mode_home, mode_away)
    minimum_total = 3 if expected_total >= 3.05 else 2 if expected_total >= 2.58 else 0

    xg_score = _score_from_xg(matrix, home_xg, away_xg, target_outcome)
    if xg_score:
        return xg_score

    if (
        (minimum_total == 0 or mode_home + mode_away >= minimum_total)
        and _score_outcome(mode_home, mode_away) == target_outcome
    ):
        return ranked[0]

    target_scores = [
        item for item in ranked[:14]
        if _score_outcome(item[0], item[1]) == target_outcome and item[0] + item[1] >= minimum_total
    ]
    if target_scores:
        return target_scores[0]

    higher_total = [item for item in ranked[:14] if item[0] + item[1] >= minimum_total]
    return higher_total[0] if higher_total else ranked[0]


def _total_goals_prediction(matrix: List[Tuple[int, int, float]], expected_total: float) -> Dict:
    lines = []
    for line in (1.5, 2.5, 3.5):
        over = sum(prob for home_goals, away_goals, prob in matrix if home_goals + away_goals > line)
        under = sum(prob for home_goals, away_goals, prob in matrix if home_goals + away_goals < line)
        lines.append({
            "line": line,
            "over_probability": round(over, 3),
            "under_probability": round(under, 3),
        })

    main_line = next(item for item in lines if item["line"] == 2.5)
    total_distribution: Dict[int, float] = {}
    for home_goals, away_goals, prob in matrix:
        total_goals = home_goals + away_goals
        total_distribution[total_goals] = total_distribution.get(total_goals, 0) + prob
    most_likely_total = max(total_distribution.items(), key=lambda item: item[1])[0]
    over_probability = main_line["over_probability"]
    under_probability = main_line["under_probability"]
    line_15 = next(item for item in lines if item["line"] == 1.5)
    line_35 = next(item for item in lines if item["line"] == 3.5)
    side_probability = max(over_probability, under_probability)
    signal_strength = abs(over_probability - under_probability)

    if over_probability >= under_probability:
        if over_probability < 0.57:
            recommendation = "大2.5观察"
            recommendation_level = "low"
            risk_note = "2.5球主线优势不足，比分池优先看具体强弱和双方进球。"
        elif line_35["under_probability"] >= 0.58 and line_35["under_probability"] >= over_probability - 0.01:
            recommendation = "大2.5轻微 / 3.5防小"
            recommendation_level = "medium"
            risk_note = "2.5大成立但3.5小保护更强，倾向2-1、3-0、2-0这类不过度追高比分。"
        elif line_35["over_probability"] >= 0.48 and expected_total >= 3.35:
            recommendation = "大2.5偏强 / 3.5可跟进"
            recommendation_level = "high"
            risk_note = "3.5球上沿也有支撑，比分池允许4球以上溢出。"
        else:
            recommendation = "大2.5"
            recommendation_level = "medium" if signal_strength < 0.24 else "high"
            risk_note = "主线偏大，但是否追到3.5以上需看强队转化率和弱方进球能力。"
    else:
        if under_probability < 0.57:
            recommendation = "小2.5观察"
            recommendation_level = "low"
            risk_note = "2.5球主线优势不足，需结合半场节奏和首发进攻配置复核。"
        elif line_15["over_probability"] >= 0.72:
            recommendation = "小2.5轻微 / 1.5防大"
            recommendation_level = "medium"
            risk_note = "2.5小更优，但1.5大概率较高，重点防1-1或2-0。"
        else:
            recommendation = "小2.5"
            recommendation_level = "medium" if signal_strength < 0.24 else "high"
            risk_note = "主线偏小，比分池优先保留0-1、1-1、1-0和2-0。"

    return {
        "expected_total": _round2(expected_total),
        "most_likely_total": most_likely_total,
        "main_line": 2.5,
        "over_probability": over_probability,
        "under_probability": under_probability,
        "recommendation": recommendation,
        "recommendation_level": recommendation_level,
        "risk_note": risk_note,
        "side_probability": round(side_probability, 3),
        "signal_strength": round(signal_strength, 3),
        "confidence": round(signal_strength, 3),
        "lines": lines,
    }


def _probability_triplet(home: float, draw: float, away: float) -> Dict[str, float]:
    total = home + draw + away
    if total <= 0:
        return {"home": 0.333, "draw": 0.334, "away": 0.333}
    return {
        "home": home / total,
        "draw": draw / total,
        "away": away / total,
    }


def _market_difference(model: Dict[str, float], market: Dict[str, float]) -> float:
    return max(abs(model.get(key, 0) - market.get(key, 0)) for key in ("home", "draw", "away"))


def _market_calibration_weight(difference: float) -> Tuple[float, str]:
    if difference < 0.06:
        return 0.0, "aligned"
    if difference < 0.12:
        return 0.08, "mild"
    if difference < 0.20:
        return 0.13, "moderate"
    return 0.18, "strong"


def _calibrate_with_market(
    model: Dict[str, float],
    market_odds: Dict,
) -> Tuple[Dict[str, float], Dict]:
    market = market_odds.get("h2h") if market_odds else None
    market_source = market_odds.get("source") if market_odds else None
    is_historical_prior = market_source == "football_data_historical_prior"
    signal_label = "公开历史赔率样本" if is_historical_prior else "赛前实时赔率"
    if not market:
        status = market_odds.get("status", "not_available") if market_odds else "not_available"
        message = market_odds.get("message", "赛前市场信号暂不可用") if market_odds else "赛前市场信号暂不可用"
        return model, {
            "applied": False,
            "weight": 0,
            "difference": 0,
            "level": status,
            "message": message,
            "source": market_source,
            "model": {key: round(value, 3) for key, value in model.items()},
            "market": None,
            "final": {key: round(value, 3) for key, value in model.items()},
            "model_probabilities": {key: round(value, 3) for key, value in model.items()},
            "market_probabilities": None,
            "final_probabilities": {key: round(value, 3) for key, value in model.items()},
        }

    normalised_market = _probability_triplet(
        float(market.get("home", 0)),
        float(market.get("draw", 0)),
        float(market.get("away", 0)),
    )
    difference = _market_difference(model, normalised_market)
    weight, level = _market_calibration_weight(difference)
    if is_historical_prior and weight > 0:
        weight = min(weight, 0.04)
    if weight == 0:
        final = model
        message = f"模型与{signal_label}方向接近，本场不做概率校准。"
    else:
        blended = {
            key: model[key] * (1 - weight) + normalised_market[key] * weight
            for key in ("home", "draw", "away")
        }
        final = _probability_triplet(blended["home"], blended["draw"], blended["away"])
        message = f"{signal_label}与模型分歧 {difference:.1%}，已按 {weight:.0%} 权重轻量校准。"

    rounded_model = {key: round(value, 3) for key, value in model.items()}
    rounded_market = {key: round(value, 3) for key, value in normalised_market.items()}
    rounded_final = {key: round(value, 3) for key, value in final.items()}
    return final, {
        "applied": weight > 0,
        "weight": round(weight, 3),
        "difference": round(difference, 3),
        "level": level,
        "message": message,
        "source": market_source,
        "model": rounded_model,
        "market": rounded_market,
        "final": rounded_final,
        "model_probabilities": rounded_model,
        "market_probabilities": rounded_market,
        "final_probabilities": rounded_final,
    }


def _market_signal_status_label(status: str) -> str:
    labels = {
        "disabled": "实时赔率校准已关闭",
        "not_configured": "实时赔率源待配置",
        "not_available": "实时赔率暂不可用",
        "unsupported_provider": "实时赔率数据源不支持",
        "no_match": "未匹配到本场实时赔率",
        "no_markets": "暂无可用实时赔率盘口",
        "error": "实时赔率连接异常",
        "historical_prior": "历史赔率样本参考",
    }
    return labels.get(status, status or "实时赔率暂不可用")


def _market_total_preference(market_odds: Dict) -> Optional[Tuple[str, float]]:
    totals = market_odds.get("totals") if market_odds else None
    if not totals:
        return None
    over = float(totals.get("over_probability", 0) or 0)
    under = float(totals.get("under_probability", 0) or 0)
    if abs(over - under) < 0.08:
        return None
    return ("over" if over > under else "under", float(totals.get("line", 2.5) or 2.5))


def _select_market_aware_score(
    matrix: List[Tuple[int, int, float]],
    expected_total: float,
    home_xg: float,
    away_xg: float,
    preferred_outcome: Optional[str],
    market_odds: Dict,
    calibration: Dict,
) -> Tuple[int, int, float]:
    representative = _select_representative_score(matrix, expected_total, home_xg, away_xg, preferred_outcome)
    if not calibration.get("applied"):
        return representative

    total_preference = _market_total_preference(market_odds)
    if not total_preference:
        return representative

    direction, line = total_preference
    ranked = sorted(matrix, key=lambda item: item[2], reverse=True)
    for home_goals, away_goals, probability in ranked[:24]:
        if preferred_outcome and _score_outcome(home_goals, away_goals) != preferred_outcome:
            continue
        total_goals = home_goals + away_goals
        if direction == "over" and total_goals > line:
            return home_goals, away_goals, probability
        if direction == "under" and total_goals < line:
            return home_goals, away_goals, probability
    return representative


def _select_primary_score(
    matrix: List[Tuple[int, int, float]],
    probabilities: Dict[str, float],
    expected_total: float,
    representative_score: Tuple[int, int, float],
) -> Tuple[int, int, float]:
    """Choose the headline score without letting low-score modes dominate high-tempo games."""
    ranked = sorted(matrix, key=lambda item: item[2], reverse=True)
    if not ranked:
        return representative_score
    mode_home, mode_away, mode_probability = ranked[0]
    rep_home, rep_away, _ = representative_score
    representative_probability = _matrix_probability(matrix, rep_home, rep_away)
    representative = (
        rep_home,
        rep_away,
        representative_probability or representative_score[2],
    )

    favorite_outcome, favorite_probability = max(
        (("home", probabilities.get("home", 0.0)), ("away", probabilities.get("away", 0.0))),
        key=lambda item: item[1],
    )
    draw_probability = probabilities.get("draw", 0.0)
    representative_outcome = _score_outcome(rep_home, rep_away)
    mode_total = mode_home + mode_away
    representative_total = rep_home + rep_away
    high_tempo_group_signal = (
        expected_total >= 3.0
        and favorite_probability >= 0.62
        and favorite_probability - draw_probability >= 0.32
    )
    plausible_probability = representative[2] >= mode_probability * 0.34
    adds_stoppage_time_goal = representative_total >= mode_total + 1

    if (
        high_tempo_group_signal
        and representative_outcome == favorite_outcome
        and adds_stoppage_time_goal
        and plausible_probability
    ):
        return representative
    return ranked[0]


TEMPLATE_SCORE_SET = {(2, 0), (2, 1), (1, 2), (0, 2)}
DRAW_SCORE_SET = {(0, 0), (1, 1), (2, 2)}


def _append_unique_score(pool: List[Tuple[int, int, float]], candidate: Optional[Tuple[int, int, float]]) -> None:
    if not candidate:
        return
    if any(home == candidate[0] and away == candidate[1] for home, away, _ in pool):
        return
    pool.append(candidate)


def _replace_third_or_append(pool: List[Tuple[int, int, float]], candidate: Optional[Tuple[int, int, float]]) -> bool:
    if not candidate:
        return False
    if any(home == candidate[0] and away == candidate[1] for home, away, _ in pool[:3]):
        return False
    if len(pool) >= 3:
        pool[2] = candidate
    else:
        pool.append(candidate)
    return True


def _score_discipline_match_shape(
    probabilities: Dict[str, float],
    expected_total: float,
    home_xg: float,
    away_xg: float,
) -> str:
    home_prob = probabilities.get("home", 0.0)
    draw_prob = probabilities.get("draw", 0.0)
    away_prob = probabilities.get("away", 0.0)
    favorite = max(home_prob, away_prob)
    win_gap = abs(home_prob - away_prob)
    if favorite >= 0.61 and win_gap >= 0.25:
        return "A/C" if expected_total >= 3.05 and min(home_xg, away_xg) >= 0.82 else "A"
    if expected_total >= 3.05 and min(home_xg, away_xg) >= 0.82:
        return "C"
    if expected_total <= 2.55 or draw_prob >= 0.31:
        return "D"
    if favorite < 0.56 or draw_prob >= 0.25:
        return "B"
    return "balanced"


def _score_discipline_draw_target(expected_total: float, home_xg: float, away_xg: float) -> int:
    if expected_total >= 3.35 and min(home_xg, away_xg) >= 1.15:
        return 2
    if expected_total <= 2.25:
        return 0
    return 1


def _score_discipline_overflow_candidate(
    matrix: List[Tuple[int, int, float]],
    favorite_outcome: str,
    home_xg: float,
    away_xg: float,
    excluded: Iterable[Tuple[int, int]],
) -> Optional[Tuple[int, int, float]]:
    if favorite_outcome == "home":
        raw_candidates = [(3, 1), (4, 0), (4, 1), (5, 0), (5, 1)]
        if away_xg < 0.82:
            raw_candidates = [(4, 0), (3, 0), (5, 0), (3, 1), (4, 1)]
    elif favorite_outcome == "away":
        raw_candidates = [(1, 3), (0, 4), (1, 4), (0, 5), (1, 5)]
        if home_xg < 0.82:
            raw_candidates = [(0, 4), (0, 3), (0, 5), (1, 3), (1, 4)]
    else:
        return None

    excluded_set = set(excluded)
    for home_goals, away_goals in raw_candidates:
        if (home_goals, away_goals) in excluded_set:
            continue
        probability = _matrix_probability(matrix, home_goals, away_goals)
        if probability > 0:
            return home_goals, away_goals, probability
    return None


def _apply_score_discipline(
    top_scores: List[Tuple[int, int, float]],
    matrix: List[Tuple[int, int, float]],
    probabilities: Dict[str, float],
    expected_total: float,
    home_xg: float,
    away_xg: float,
    match_round: Optional[int],
    is_knockout: bool,
    market_calibration: Dict,
    representative_score: Tuple[int, int, float],
) -> Tuple[List[Tuple[int, int, float]], List[str]]:
    """Map WC2026 score-pool discipline into the model's score output."""
    pool = list(top_scores)
    notes: List[str] = []
    if not pool:
        return pool, notes

    shape = _score_discipline_match_shape(probabilities, expected_total, home_xg, away_xg)
    favorite_outcome, favorite_probability = max(
        (("home", probabilities.get("home", 0.0)), ("away", probabilities.get("away", 0.0))),
        key=lambda item: item[1],
    )
    draw_probability = probabilities.get("draw", 0.0)
    group_round = int(match_round or 0)
    first_home, first_away, _ = pool[0]
    has_draw_top3 = any((home, away) in DRAW_SCORE_SET for home, away, _ in pool[:3])
    evidence_is_partial = not market_calibration.get("applied")
    needs_draw_protection = (
        not is_knockout
        and shape not in {"A", "A/C"}
        and not has_draw_top3
        and (
            evidence_is_partial
            or draw_probability >= 0.22
            or favorite_probability < 0.58
            or group_round in {1, 3}
            or (first_home, first_away) in TEMPLATE_SCORE_SET
        )
    )
    if needs_draw_protection:
        draw_score = _score_for_outcome(
            matrix,
            "draw",
            expected_total=expected_total,
            reference_score=representative_score,
            excluded_scores={(home, away) for home, away, _ in pool[:3]},
            draw_target_goals=_score_discipline_draw_target(expected_total, home_xg, away_xg),
        )
        if _replace_third_or_append(pool, draw_score):
            notes.append("比分纪律: 证据未完整或热门优势不足，Top3加入防平比分")

    has_btts_top3 = any(home > 0 and away > 0 for home, away, _ in pool[:3])
    if shape in {"C", "A/C"} and min(home_xg, away_xg) >= 0.88 and expected_total >= 2.75 and not has_btts_top3:
        btts_scores = [
            item for item in sorted(matrix, key=lambda item: item[2], reverse=True)
            if item[0] > 0 and item[1] > 0 and _score_outcome(item[0], item[1]) in {favorite_outcome, "draw"}
        ]
        if btts_scores and _replace_third_or_append(pool, btts_scores[0]):
            notes.append("比分纪律: 开放对攻场景保留双方进球比分")

    has_overflow_top3 = any(home + away >= 4 for home, away, _ in pool[:3])
    if shape in {"A", "A/C"} and expected_total >= 3.12 and favorite_probability >= 0.68 and not has_overflow_top3:
        overflow = _score_discipline_overflow_candidate(
            matrix,
            favorite_outcome,
            home_xg,
            away_xg,
            excluded={(home, away) for home, away, _ in pool[:3]},
        )
        if _replace_third_or_append(pool, overflow):
            notes.append("比分纪律: 强队突破场景加入大胜溢出候选")

    if (first_home, first_away) in TEMPLATE_SCORE_SET:
        notes.append("比分纪律: 首选落在2-0/2-1模板簇，已用比分池校验防平和溢出")

    deduped: List[Tuple[int, int, float]] = []
    for item in pool:
        _append_unique_score(deduped, item)
    if len(deduped) < 3:
        for item in sorted(matrix, key=lambda item: item[2], reverse=True):
            _append_unique_score(deduped, item)
            if len(deduped) >= 3:
                break
    return deduped, notes


def _score_for_outcome(
    matrix: List[Tuple[int, int, float]],
    outcome: str,
    expected_total: Optional[float] = None,
    reference_score: Optional[Tuple[int, int, float]] = None,
    excluded_scores: Optional[Iterable[Tuple[int, int]]] = None,
    draw_target_goals: Optional[int] = None,
) -> Tuple[int, int, float]:
    ranked = sorted(matrix, key=lambda item: item[2], reverse=True)
    excluded = set(excluded_scores or ())
    if expected_total is not None and reference_score is not None:
        ref_home, ref_away, _ = reference_score
        candidates = [
            item for item in ranked
            if _score_outcome(item[0], item[1]) == outcome
            and (item[0], item[1]) not in excluded
        ]
        if not candidates:
            candidates = [item for item in ranked if _score_outcome(item[0], item[1]) == outcome]
        if candidates:
            if outcome == "draw":
                ref_total = ref_home + ref_away
                if draw_target_goals is not None:
                    target_draw_goals = draw_target_goals
                elif expected_total <= 1.65 and ref_total <= 2:
                    target_draw_goals = 0
                elif ref_total >= 4 or (expected_total >= 3.15 and ref_total >= 3):
                    target_draw_goals = 2
                else:
                    target_draw_goals = 1
                draw_score = next(
                    (
                        item for item in candidates
                        if item[0] == target_draw_goals and item[1] == target_draw_goals
                    ),
                    None,
                )
                if draw_score:
                    return draw_score

            def candidate_score(item: Tuple[int, int, float]) -> float:
                home_goals, away_goals, probability = item
                total_penalty = abs((home_goals + away_goals) - expected_total) * 0.34
                ref_penalty = (abs(home_goals - ref_home) + abs(away_goals - ref_away)) * 0.22
                margin_penalty = max(0, abs((home_goals - away_goals) - (ref_home - ref_away)) - 2) * 0.18
                return math.log(max(probability, 1e-9)) - total_penalty - ref_penalty - margin_penalty

            return max(candidates, key=candidate_score)

    for home_goals, away_goals, probability in ranked:
        if (home_goals, away_goals) in excluded:
            continue
        if _score_outcome(home_goals, away_goals) == outcome:
            return home_goals, away_goals, probability
    return ranked[0]


def _nearest_score_to_anchor(
    matrix: List[Tuple[int, int, float]],
    outcome: str,
    target_home: int,
    target_away: int,
    excluded_scores: Optional[Iterable[Tuple[int, int]]] = None,
) -> Optional[Tuple[int, int, float]]:
    excluded = set(excluded_scores or ())
    candidates = [
        item for item in sorted(matrix, key=lambda item: item[2], reverse=True)
        if _score_outcome(item[0], item[1]) == outcome
        and (item[0], item[1]) not in excluded
    ]
    if not candidates:
        candidates = [
            item for item in sorted(matrix, key=lambda item: item[2], reverse=True)
            if _score_outcome(item[0], item[1]) == outcome
        ]
    if not candidates:
        return None

    def utility(item: Tuple[int, int, float]) -> float:
        home_goals, away_goals, probability = item
        target_total = target_home + target_away
        return (
            math.log(max(probability, 1e-9))
            - abs(home_goals - target_home) * 0.82
            - abs(away_goals - target_away) * 0.82
            - abs((home_goals + away_goals) - target_total) * 0.22
        )

    return max(candidates, key=utility)


def _upset_score_for_outcome(
    matrix: List[Tuple[int, int, float]],
    outcome: str,
    expected_total: float,
    reference_score: Tuple[int, int, float],
    excluded_scores: Optional[Iterable[Tuple[int, int]]],
    favorite: str,
    favorite_probability: float,
    probabilities: Dict[str, float],
    home_xg: float,
    away_xg: float,
    rating_diff: float,
    market_odds: Dict,
) -> Tuple[Tuple[int, int, float], List[str]]:
    excluded = set(excluded_scores or ())
    ref_home, ref_away, _ = reference_score
    favorite_side = favorite if favorite in {"home", "away"} else ("home" if rating_diff >= 0 else "away")
    underdog_side = "away" if favorite_side == "home" else "home"
    favorite_xg = home_xg if favorite_side == "home" else away_xg
    underdog_xg = away_xg if favorite_side == "home" else home_xg
    favorite_ref_goals = ref_home if favorite_side == "home" else ref_away
    underdog_ref_goals = ref_away if favorite_side == "home" else ref_home
    pool_outcomes = {_score_outcome(home, away) for home, away in excluded}
    pool_has_upset_shape = outcome in pool_outcomes
    pool_has_btts = any(home > 0 and away > 0 for home, away in excluded)
    reference_total = ref_home + ref_away
    total_preference = _market_total_preference(market_odds)
    over_signal = bool(total_preference and total_preference[0] == "over")
    notes: List[str] = ["冷门比分按强队进球下修、弱方达标或微超筛选，避免与主选比分极端反转"]

    if pool_has_upset_shape:
        notes.append("主选池已覆盖一种冷门形态，冷门比分允许向相邻低总进球或小胜方向漂移")

    if outcome == "draw":
        if pool_has_upset_shape and reference_total <= 3:
            target_draw_goals = 0
        elif favorite_probability >= 0.70 and underdog_xg < 0.85 and not pool_has_btts:
            target_draw_goals = 0
        elif (
            reference_total >= 4
            and favorite_probability < 0.69
            and underdog_xg < 0.95
        ):
            target_draw_goals = 0
        elif (
            expected_total >= 3.25
            and reference_total >= 4
            and (
                (favorite_probability >= 0.69 and (underdog_xg >= 0.85 or pool_has_btts or over_signal))
                or underdog_xg >= 1.05
            )
        ):
            target_draw_goals = 2
        else:
            target_draw_goals = 1
        score = _nearest_score_to_anchor(
            matrix,
            "draw",
            target_draw_goals,
            target_draw_goals,
            excluded_scores=excluded,
        )
        if score:
            if target_draw_goals == 0:
                if reference_total >= 4 and not (favorite_probability >= 0.70 and underdog_xg < 0.85 and not pool_has_btts):
                    notes.append("强队冷门优先看进球效率断电，0-0 是高比分主选池的低位纠偏")
                else:
                    notes.append("强队冷门优先看进球效率断电，0-0 是干净胜主选池的低位邻近解")
            elif target_draw_goals == 2:
                notes.append("主预测已进入高总进球/双方进球形态，冷门平局上移到 2-2")
            else:
                notes.append("弱方进球预期接近达标位，平局冷门优先落在 1-1")
            return score, notes

    favorite_target = min(favorite_ref_goals, max(0, int(math.floor(favorite_xg + 0.15)))) - 1
    if favorite_probability >= 0.62:
        favorite_target -= 1
    if pool_has_upset_shape:
        favorite_target -= 1
    favorite_target = max(0, favorite_target)

    underdog_target = max(1, int(round(underdog_xg)))
    if underdog_xg >= 1.35 or (pool_has_upset_shape and underdog_xg >= 1.05):
        underdog_target = max(underdog_target, 2)
    if underdog_target <= favorite_target:
        underdog_target = favorite_target + 1
    if not pool_has_upset_shape:
        underdog_target = min(underdog_target, max(1, int(round(underdog_xg)) + 1))

    target_home, target_away = (
        (favorite_target, underdog_target)
        if favorite_side == "home"
        else (underdog_target, favorite_target)
    )
    score = _nearest_score_to_anchor(
        matrix,
        outcome,
        target_home,
        target_away,
        excluded_scores=excluded,
    )
    if score:
        notes.append("胜负冷门优先选热门方少进 1-2 球、弱方 1 球起步的小比分路径")
        return score, notes

    fallback = _score_for_outcome(
        matrix,
        outcome,
        expected_total=expected_total,
        reference_score=reference_score,
        excluded_scores=excluded_scores,
    )
    return fallback, notes


def _upset_prediction(
    home: TeamProfile,
    away: TeamProfile,
    probabilities: Dict[str, float],
    matrix: List[Tuple[int, int, float]],
    market_odds: Dict,
    calibration: Dict,
    rating_diff: float,
    expected_total: float,
    representative_score: Tuple[int, int, float],
    home_xg: float,
    away_xg: float,
    excluded_scores: Optional[Iterable[Tuple[int, int]]] = None,
) -> Dict:
    ordered = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    favorite, favorite_probability = ordered[0]
    draw_probability = probabilities.get("draw", 0.0)
    if favorite in {"home", "away"}:
        underdog_outcome = "away" if favorite == "home" else "home"
        underdog_probability = probabilities.get(underdog_outcome, 0.0)
        heavy_favorite = favorite_probability >= 0.7 or abs(rating_diff) >= 260
        balanced_draw_risk = (
            favorite_probability < 0.62
            and draw_probability >= underdog_probability * 1.05
        )
        if heavy_favorite or balanced_draw_risk:
            upset_outcome = "draw"
            upset_team = "平局"
            favorite_team = home.name if favorite == "home" else away.name
            label = "平局冷门"
        elif favorite == "home":
            upset_outcome = "away"
            upset_team = away.name
            favorite_team = home.name
            label = "客队爆冷"
        else:
            upset_outcome = "home"
            upset_team = home.name
            favorite_team = away.name
            label = "主队爆冷"
    else:
        home_edge = abs(rating_diff)
        upset_outcome = "away" if rating_diff > 0 else "home"
        upset_team = away.name if rating_diff > 0 else home.name
        favorite_team = home.name if rating_diff > 0 else away.name
        favorite_probability = max(probabilities["home"], probabilities["away"])
        label = "胜负冷门" if home_edge >= 80 else "平局冷门"

    upset_base = probabilities.get(upset_outcome, 0.0)
    draw_drag = draw_probability * (0.06 if upset_outcome == "draw" else 0.22 if favorite != "draw" else 0.35)
    market_bump = 0.0
    market = calibration.get("market") or {}
    model = calibration.get("model") or {}
    if market and upset_outcome in market:
        market_bump = max(0.0, market[upset_outcome] - model.get(upset_outcome, 0.0)) * 0.45
    probability = _clip(upset_base + draw_drag + market_bump, 0.03, 0.48)

    selected_score, anchor_reasons = _upset_score_for_outcome(
        matrix,
        upset_outcome,
        expected_total,
        representative_score,
        excluded_scores,
        favorite,
        favorite_probability,
        probabilities,
        home_xg,
        away_xg,
        rating_diff,
        market_odds,
    )
    score_home, score_away, score_probability = selected_score
    reasons = []
    reasons.extend(anchor_reasons)
    if upset_outcome == "draw":
        reasons.append("强热门场景下平局已属于冷门，比分按主预测附近的期望总进球筛选")
    if draw_probability >= 0.24:
        reasons.append("平局基准较高，比赛进入胶着后会放大爆冷窗口")
    if market_bump > 0.015:
        reasons.append("实时赔率对弱势结果的隐含概率高于模型原始判断")
    if abs(rating_diff) >= 220:
        reasons.append("强弱差明显，强队若早段久攻不下，心理与转换风险会集中暴露")
    elif abs(rating_diff) <= 90:
        reasons.append("双方实力差没有拉开，单个定位球或红黄牌事件足以改变走势")
    total_preference = _market_total_preference(market_odds)
    if total_preference:
        direction, line = total_preference
        reasons.append(f"总进球外部信号偏向{'大' if direction == 'over' else '小'}{line:g}，会改变冷门比分形态")
    if not reasons:
        reasons.append("冷门主要来自比分矩阵尾部概率，当前没有强实时赔率或事件信号")

    if probability >= 0.28:
        risk_level = "high"
    elif probability >= 0.18:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "label": label,
        "team": upset_team,
        "against": favorite_team,
        "outcome": upset_outcome,
        "probability": round(probability, 3),
        "risk_level": risk_level,
        "score": f"{score_home}-{score_away}",
        "score_probability": round(score_probability * 100, 2),
        "reasons": reasons[:4],
        "favorite_probability": round(favorite_probability, 3),
    }


def _tactic_with_squad(team: TeamProfile, tactic: TacticalTemplate) -> TacticalTemplate:
    starters, bench = squad_lineup(team.code or team.name, tactic.formation)
    if not starters:
        return tactic
    return replace(
        tactic,
        starters=starters,
        bench_options=bench[:15] if bench else tactic.bench_options,
    )


def _tactic_for(team: TeamProfile) -> TacticalTemplate:
    tactic = TEAM_TACTICS.get(team.name)
    if tactic:
        return _tactic_with_squad(team, tactic)
    hint = TEAM_DEPTH_HINTS.get(team.name)
    if hint:
        primary = hint.scorers[0].name if hint.scorers else team.name
        return _tactic_with_squad(team, TacticalTemplate(
            formation=hint.formation,
            style=hint.style,
            attacking_pattern=f"围绕{primary}的终结点和边路推进建立进攻，弱势局面优先打转换",
            defensive_shape="中低位压缩中路，边路回收后用第一脚向前球寻找反击",
            set_piece="定位球和二点球是非强队提升xG的关键来源",
            risk="若后腰或中卫出现黄牌压力，防线侵略性会下降并影响二点保护",
            starters=hint.starters,
            bench_options=hint.bench_options,
        ))
    return _tactic_with_squad(team, TacticalTemplate(
        formation=DEFAULT_TACTIC.formation,
        style=DEFAULT_TACTIC.style,
        attacking_pattern=DEFAULT_TACTIC.attacking_pattern,
        defensive_shape=DEFAULT_TACTIC.defensive_shape,
        set_piece=DEFAULT_TACTIC.set_piece,
        risk=DEFAULT_TACTIC.risk,
        starters=tuple(f"{team.name}{name}" for name in DEFAULT_TACTIC.starters),
        bench_options=tuple(f"{team.name}{name}" for name in DEFAULT_TACTIC.bench_options),
    ))


def _canonical_team_name(value: Any) -> str:
    text = str(value or "")
    return str(TEAM_ALIASES.get(text, text))


def _same_team(left: Any, right: Any) -> bool:
    return _canonical_team_name(left).casefold() == _canonical_team_name(right).casefold()


def _player_names(values: Any) -> List[str]:
    players: List[str] = []
    if not isinstance(values, list):
        return players
    for item in values:
        if isinstance(item, Mapping):
            name = item.get("name") or item.get("player") or item.get("short_name") or item.get("displayName")
        else:
            name = item
        if name:
            players.append(str(name))
    return players


def _lineup_entry_for_team(match_context: Optional[Mapping[str, Any]], team: TeamProfile) -> Optional[Mapping[str, Any]]:
    if not isinstance(match_context, Mapping):
        return None
    report = match_context.get("report") if isinstance(match_context.get("report"), Mapping) else {}
    lineup_rows = report.get("lineups")
    if not isinstance(lineup_rows, list):
        lineup_rows = match_context.get("lineups")
    if not isinstance(lineup_rows, list):
        return None

    for row in lineup_rows:
        if not isinstance(row, Mapping):
            continue
        row_team = row.get("team") or row.get("team_name") or row.get("name")
        if row_team and _same_team(row_team, team.name):
            return row
        if not row_team:
            side = str(row.get("side") or "").lower()
            if side == "home" and _same_team(match_context.get("home_team"), team.name):
                return row
            if side == "away" and _same_team(match_context.get("away_team"), team.name):
                return row
    return None


def _tactical_evidence_from_lineup(
    team: TeamProfile,
    row: Mapping[str, Any],
    *,
    source: str,
    source_label: str,
    confidence: float,
    note: str,
) -> TacticalEvidence:
    base = _tactic_for(team)
    formation = str(row.get("formation") or base.formation).strip() or base.formation
    starters = _player_names(row.get("starters") or row.get("starting_xi") or row.get("start_xi") or row.get("startXI") or row.get("lineup"))
    substitutes = _player_names(row.get("substitutes") or row.get("bench") or row.get("subs"))
    if len(starters) < 8:
        starters = list(base.starters)
    if not substitutes:
        substitutes = list(base.bench_options)
    tactic = replace(
        base,
        formation=formation,
        starters=tuple(starters),
        bench_options=tuple(substitutes),
    )
    return TacticalEvidence(
        tactic=tactic,
        source=source,
        source_label=source_label,
        note=note,
        confidence=confidence,
    )


def _recent_lineup_evidence(
    team: TeamProfile,
    side: str,
    review_adjustment: Optional[Mapping[str, Any]],
) -> Optional[TacticalEvidence]:
    context = _review_side_context(review_adjustment, side)
    formation = str(context.get("latest_formation") or "").strip()
    starters = context.get("latest_starters")
    substitutes = context.get("latest_substitutes")
    if not formation and not starters:
        return None
    row = {
        "formation": formation,
        "starters": starters if isinstance(starters, list) else [],
        "substitutes": substitutes if isinstance(substitutes, list) else [],
    }
    note = f"{team.name}最近正式赛实际阵型 {formation or _tactic_for(team).formation} 已纳入阵型相克与首发参照"
    confidence = 0.72 if isinstance(starters, list) and len(starters) >= 8 else 0.66
    return _tactical_evidence_from_lineup(
        team,
        row,
        source="recent_world_cup_lineup",
        source_label="最近正式赛实际阵型",
        confidence=confidence,
        note=note,
    )


def _contextual_tactic(
    team: TeamProfile,
    side: str,
    match_context: Optional[Mapping[str, Any]],
    review_adjustment: Optional[Mapping[str, Any]],
) -> TacticalEvidence:
    current_lineup = _lineup_entry_for_team(match_context, team)
    if current_lineup:
        formation = str(current_lineup.get("formation") or _tactic_for(team).formation).strip() or _tactic_for(team).formation
        starters = _player_names(current_lineup.get("starters") or current_lineup.get("starting_xi") or current_lineup.get("start_xi") or current_lineup.get("startXI") or current_lineup.get("lineup"))
        confidence = 0.9 if len(starters) >= 10 else 0.84
        return _tactical_evidence_from_lineup(
            team,
            current_lineup,
            source="current_match_lineup",
            source_label="官方/赛前首发",
            confidence=confidence,
            note=f"{team.name}官方/赛前首发 {formation} 已覆盖旧候选池",
        )

    recent_lineup = _recent_lineup_evidence(team, side, review_adjustment)
    if recent_lineup:
        return recent_lineup

    tactic = _tactic_for(team)
    squad = get_team_squad(team.code or team.name)
    if squad:
        confidence = 0.64 if team.name in TEAM_TACTICS else 0.58
        source = "official_26_squad_candidate_pool"
        source_label = "官方26人名单候选池"
        note = f"{team.name}暂无当场官方首发，按官方26人名单与 {tactic.formation} 阵型生成候选首发；临场首发接入后自动覆盖"
    else:
        confidence = 0.62 if team.name in TEAM_TACTICS else 0.55 if team.name in TEAM_DEPTH_HINTS else 0.45
        source = "candidate_pool"
        source_label = "候选池"
        note = f"{team.name}暂无官方/赛前首发，暂用赛前候选池 {tactic.formation}"
    return TacticalEvidence(
        tactic=tactic,
        source=source,
        source_label=source_label,
        note=note,
        confidence=confidence,
    )


def _players_for(team: TeamProfile) -> Tuple[PlayerProjection, ...]:
    squad_players = squad_player_projections(team.code or team.name)
    if squad_players:
        return tuple(
            PlayerProjection(
                str(player["name"]),
                str(player["position"]),
                str(player["role"]),
                float(player["attack_share"]),
                str(player["key_metric"]),
            )
            for player in squad_players
        )
    players = TEAM_PLAYERS.get(team.name)
    if players:
        return players
    hint = TEAM_DEPTH_HINTS.get(team.name)
    if hint:
        return hint.scorers
    return (
        PlayerProjection(f"{team.name}中锋", "中锋", "禁区终结", 0.24, "禁区触球和抢点"),
        PlayerProjection(f"{team.name}边锋", "边锋", "推进制造", 0.18, "边路突破和传中"),
        PlayerProjection(f"{team.name}前腰", "前腰", "组织核心", 0.14, "关键传球"),
        PlayerProjection(f"{team.name}中场", "中场", "二点球", 0.09, "远射和二次进攻"),
    )


def _discipline_for(team: TeamProfile) -> DisciplineStatus:
    return TEAM_DISCIPLINE.get(team.name, DisciplineStatus())


def _prop_baseline(team: TeamProfile) -> TeamPropBaseline:
    rank_strength = _clip((70 - team.fifa_rank) / 55, -0.45, 1.05)
    elo_strength = _clip((team.elo_rating - 1600) / 700, -0.35, 0.8)
    strength = (rank_strength + elo_strength) / 2

    conf_corner_boost = {
        "UEFA": 0.12,
        "CONMEBOL": 0.08,
        "CONCACAF": 0.02,
        "CAF": -0.02,
        "AFC": -0.04,
        "OFC": -0.08,
    }.get(team.confederation, 0.0)
    conf_card_boost = {
        "CONMEBOL": 0.24,
        "CONCACAF": 0.16,
        "CAF": 0.12,
        "UEFA": 0.03,
        "AFC": -0.02,
        "OFC": -0.04,
    }.get(team.confederation, 0.0)

    tactic = _tactic_for(team)
    text = " ".join([tactic.style, tactic.attacking_pattern, tactic.defensive_shape, tactic.set_piece])
    width_bonus = 0.22 if any(token in text for token in ("边路", "传中", "翼")) else 0.0
    press_bonus = 0.18 if any(token in text for token in ("高位", "压迫", "逼抢")) else 0.0
    low_block_penalty = -0.16 if any(token in text for token in ("低位", "回收")) else 0.0

    corners_for = 4.35 + strength * 1.05 + conf_corner_boost + width_bonus + press_bonus * 0.35
    corners_against = 4.65 - strength * 0.72 - conf_corner_boost * 0.35 - low_block_penalty * 0.25
    yellow_for = 1.55 + conf_card_boost + press_bonus * 0.26 + max(0.0, -strength) * 0.28
    yellow_against = 1.52 + conf_card_boost * 0.45 + max(0.0, strength) * 0.12

    return TeamPropBaseline(
        corners_for=round(_clip(corners_for, 2.8, 7.0), 2),
        corners_against=round(_clip(corners_against, 2.9, 6.8), 2),
        yellow_cards_for=round(_clip(yellow_for, 0.9, 3.2), 2),
        yellow_cards_against=round(_clip(yellow_against, 0.9, 2.8), 2),
    )


def _window_prop_baseline(team: TeamProfile, context: Mapping[str, Any], fallback: TeamPropBaseline) -> TeamPropBaseline:
    sample_matches = int(context.get("sample_matches") or 0)
    if sample_matches <= 0:
        return fallback

    def blended(key: str, fallback_value: float, low: float, high: float) -> float:
        try:
            actual = float(context.get(key))
        except (TypeError, ValueError):
            return fallback_value
        if context.get("prop_sample_policy") == "official_mean":
            weight = 1.0
        else:
            weight = 0.82 if sample_matches >= 2 else 0.72
        return round(_clip(actual * weight + fallback_value * (1 - weight), low, high), 2)

    return TeamPropBaseline(
        corners_for=blended("corners_for", fallback.corners_for, 1.8, 9.2),
        corners_against=blended("corners_against", fallback.corners_against, 1.8, 9.2),
        yellow_cards_for=blended("yellow_cards_for", fallback.yellow_cards_for, 0.0, 4.2),
        yellow_cards_against=blended("yellow_cards_against", fallback.yellow_cards_against, 0.0, 4.2),
        sample_matches=sample_matches,
        source=str(context.get("source_label") or "current_world_cup_form_window"),
    )


def _set_piece_card_prediction(
    home: TeamProfile,
    away: TeamProfile,
    home_xg: float,
    away_xg: float,
    high_press: bool,
    is_knockout: bool,
    home_discipline: DisciplineStatus,
    away_discipline: DisciplineStatus,
    review_adjustment: Optional[Mapping[str, Any]] = None,
) -> Dict:
    home_context = _review_side_context(review_adjustment, "home")
    away_context = _review_side_context(review_adjustment, "away")
    home_base = _window_prop_baseline(home, home_context, _prop_baseline(home))
    away_base = _window_prop_baseline(away, away_context, _prop_baseline(away))

    home_attack_pressure = _clip(0.88 + home_xg / 3.2 * 0.24 + (home.elo_rating - away.elo_rating) / 2800, 0.72, 1.32)
    away_attack_pressure = _clip(0.88 + away_xg / 3.2 * 0.24 + (away.elo_rating - home.elo_rating) / 2800, 0.72, 1.32)
    home_corners = (home_base.corners_for * 0.62 + away_base.corners_against * 0.38) * home_attack_pressure
    away_corners = (away_base.corners_for * 0.62 + home_base.corners_against * 0.38) * away_attack_pressure

    card_intensity = (0.22 if is_knockout else 0.0) + (0.18 if high_press else 0.0)
    home_recent_cards = home_discipline.yellow_cards * 0.08 + home_discipline.red_cards * 0.18
    away_recent_cards = away_discipline.yellow_cards * 0.08 + away_discipline.red_cards * 0.18
    home_yellows = home_base.yellow_cards_for * 0.66 + away_base.yellow_cards_against * 0.18 + card_intensity + home_recent_cards
    away_yellows = away_base.yellow_cards_for * 0.66 + home_base.yellow_cards_against * 0.18 + card_intensity + away_recent_cards

    corners_total = round(home_corners + away_corners, 1)
    yellow_total = round(home_yellows + away_yellows, 1)
    basis = [
        f"角球: {home.name}{home_base.source}约 {home_base.corners_for:.1f} 个角球/送对手 {home_base.corners_against:.1f} 个，结合本场xG {home_xg:.2f} 修正",
        f"角球: {away.name}{away_base.source}约 {away_base.corners_for:.1f} 个角球/送对手 {away_base.corners_against:.1f} 个，结合本场xG {away_xg:.2f} 修正",
        f"黄牌: {home.name}{home_base.source} {home_base.yellow_cards_for:.1f} 张，{away.name}{away_base.source} {away_base.yellow_cards_for:.1f} 张，按对抗强度修正",
        "修正项: 淘汰赛、高强度逼抢、累计牌面和强弱差会提高黄牌风险；边路/压迫打法会提高角球预期",
    ]

    return {
        "corners": {
            "home": round(home_corners, 1),
            "away": round(away_corners, 1),
            "total": corners_total,
            "edge": home.name if home_corners > away_corners + 0.4 else away.name if away_corners > home_corners + 0.4 else "接近",
            "basis": basis[:2],
        },
        "yellow_cards": {
            "home": round(home_yellows, 1),
            "away": round(away_yellows, 1),
            "total": yellow_total,
            "risk": "偏高" if yellow_total >= 4.4 else "偏低" if yellow_total <= 2.6 else "常规",
            "basis": basis[2:],
        },
        "basis": basis,
    }


def _lineup_with_availability(tactic: TacticalTemplate, discipline: DisciplineStatus) -> Tuple[List[str], List[str]]:
    starters = list(tactic.starters)
    bench = list(tactic.bench_options)
    for suspended in discipline.suspended_players:
        if suspended in starters:
            replacement = next((player for player in bench if player not in discipline.suspended_players), None)
            index = starters.index(suspended)
            starters[index] = f"{replacement or '替补待定'}（替 {suspended}）"
    return starters, bench


def _discipline_note(team: TeamProfile, discipline: DisciplineStatus) -> str:
    parts = []
    if discipline.suspended_players:
        parts.append(f"停赛: {'、'.join(discipline.suspended_players)}")
    if discipline.card_risk_players:
        parts.append(f"黄牌风险: {'、'.join(discipline.card_risk_players)}")
    if discipline.yellow_cards or discipline.red_cards:
        parts.append(f"累计黄牌{discipline.yellow_cards}张/红牌{discipline.red_cards}张")
    return "；".join(parts) if parts else f"{team.name}暂无官方实时红黄牌数据，暂不做牌面修正"


def _lineup_payload(
    team: TeamProfile,
    discipline: DisciplineStatus,
    evidence: Optional[TacticalEvidence] = None,
) -> Dict:
    evidence = evidence or _contextual_tactic(team, "home", None, None)
    tactic = evidence.tactic
    starters, bench = _lineup_with_availability(tactic, discipline)
    confidence = evidence.confidence
    confidence -= min(len(discipline.suspended_players) * 0.12 + len(discipline.card_risk_players) * 0.02, 0.2)
    confidence_floor = 0.82 if evidence.source == "current_match_lineup" else 0.38
    confidence_ceiling = 0.94 if evidence.source == "current_match_lineup" else 0.78
    return {
        "team": team.name,
        "formation": tactic.formation,
        "starters": starters,
        "bench_options": bench,
        "confidence": round(_clip(confidence, confidence_floor, confidence_ceiling), 2),
        "note": f"{evidence.note}；红黄牌仅在官方实时数据接入后修正",
        "source": evidence.source_label,
        "evidence_source": evidence.source,
        "suspended_players": list(discipline.suspended_players),
        "card_risk_players": list(discipline.card_risk_players),
        "discipline_note": _discipline_note(team, discipline),
    }


def _tactical_payload(team: TeamProfile, evidence: Optional[TacticalEvidence] = None) -> Dict:
    evidence = evidence or _contextual_tactic(team, "home", None, None)
    tactic = evidence.tactic
    return {
        "team": team.name,
        "formation": tactic.formation,
        "style": tactic.style,
        "attacking_pattern": tactic.attacking_pattern,
        "defensive_shape": tactic.defensive_shape,
        "set_piece": tactic.set_piece,
        "risk": tactic.risk,
        "source": evidence.source,
        "source_label": evidence.source_label,
        "evidence_note": evidence.note,
    }


def _formation_family(formation: str) -> str:
    if formation.startswith("3-") or formation.startswith("5-"):
        return "back_three"
    if formation.startswith("4-3-3"):
        return "front_three"
    if formation.startswith("4-2-3-1"):
        return "double_pivot"
    if formation.startswith("4-4-2"):
        return "two_strikers"
    return "balanced"


def _tactical_matchup(
    home: TeamProfile,
    away: TeamProfile,
    home_tactic: Optional[TacticalTemplate] = None,
    away_tactic: Optional[TacticalTemplate] = None,
) -> Tuple[float, float, float, Dict, List[str]]:
    home_tactic = home_tactic or _tactic_for(home)
    away_tactic = away_tactic or _tactic_for(away)
    home_family = _formation_family(home_tactic.formation)
    away_family = _formation_family(away_tactic.formation)
    home_scale = 1.0
    away_scale = 1.0
    total_scale = 1.0
    notes: List[str] = []

    if home_family == "front_three" and away_family == "back_three":
        home_scale *= 0.97
        away_scale *= 1.03
        notes.append(f"{away.name}三中卫可覆盖{home.name}三前锋宽度，{home.name}阵地战效率小降")
    elif home_family == "back_three" and away_family == "front_three":
        home_scale *= 1.03
        away_scale *= 0.97
        notes.append(f"{home.name}三中卫对{away.name}三前锋有宽度保护，反击出口略增")

    if home_family == "double_pivot" and away_family == "two_strikers":
        home_scale *= 1.04
        notes.append(f"{home.name}双后腰对{away.name}双前锋二点球保护更稳")
    elif home_family == "two_strikers" and away_family == "double_pivot":
        away_scale *= 1.04
        notes.append(f"{away.name}双后腰能削弱{home.name}双前锋直塞冲击")

    home_high_press = "高位" in home_tactic.style or "压迫" in home_tactic.style
    away_low_block = "低位" in away_tactic.style or "回收" in away_tactic.defensive_shape
    away_high_press = "高位" in away_tactic.style or "压迫" in away_tactic.style
    home_low_block = "低位" in home_tactic.style or "回收" in home_tactic.defensive_shape

    if home_high_press and away_low_block:
        home_scale *= 1.03
        total_scale *= 1.02
        notes.append(f"{home.name}压迫对{away.name}低位出球有抢断收益，但会抬高转换节奏")
    if away_high_press and home_low_block:
        away_scale *= 1.03
        total_scale *= 1.02
        notes.append(f"{away.name}压迫对{home.name}低位出球有抢断收益，但会抬高转换节奏")

    if ("边路" in home_tactic.attacking_pattern or "边锋" in home_tactic.style) and away_family == "back_three":
        home_scale *= 0.98
        notes.append(f"{away.name}翼卫/三中卫结构会压缩{home.name}边路爆点空间")
    if ("边路" in away_tactic.attacking_pattern or "边锋" in away_tactic.style) and home_family == "back_three":
        away_scale *= 0.98
        notes.append(f"{home.name}翼卫/三中卫结构会压缩{away.name}边路爆点空间")

    if not notes:
        notes.append("双方阵型相克不明显，模型按基础实力、状态和场地因素为主")

    payload = {
        "home_team": home.name,
        "away_team": away.name,
        "home_formation": home_tactic.formation,
        "away_formation": away_tactic.formation,
        "home_xg_multiplier": round(home_scale, 3),
        "away_xg_multiplier": round(away_scale, 3),
        "tempo_multiplier": round(total_scale, 3),
        "notes": notes[:3],
    }
    return home_scale, away_scale, total_scale, payload, notes[:3]


def _key_player_payload(team: TeamProfile, team_xg: float) -> List[Dict]:
    payload = []
    for player in _players_for(team)[:3]:
        player_xg = team_xg * player.attack_share
        payload.append({
            "name": player.name,
            "team": team.name,
            "position": player.position,
            "role": player.role,
            "rating": round(_clip(6.8 + player.attack_share * 8 + (team.elo_rating - 1600) / 900, 6.6, 9.4), 1),
            "goals_projection": _round2(player_xg),
            "assist_projection": _round2(max(0.04, team_xg * player.attack_share * 0.42)),
            "key_metric": player.key_metric,
            "note": f"预计参与{round(player.attack_share * 100)}%左右的本队进攻xG",
        })
    return payload


def _goal_scorer_payload(home: TeamProfile, away: TeamProfile, home_xg: float, away_xg: float) -> List[Dict]:
    candidates = []
    for team, team_xg in ((home, home_xg), (away, away_xg)):
        for player in _players_for(team)[:4]:
            player_xg = team_xg * player.attack_share
            probability = 1 - math.exp(-player_xg)
            candidates.append({
                "name": player.name,
                "team": team.name,
                "probability": round(probability, 3),
                "xg": _round2(player_xg),
                "reason": f"{player.role} · {player.key_metric}",
            })
    return sorted(candidates, key=lambda item: item["probability"], reverse=True)[:6]


def _discipline_payload(team: TeamProfile, discipline: DisciplineStatus) -> Dict:
    has_suspension = bool(discipline.suspended_players or discipline.red_cards)
    has_card_risk = bool(discipline.card_risk_players or discipline.yellow_cards >= 2)
    if has_suspension:
        impact = "存在停赛或红牌后续影响，首发和xG已下调"
    elif has_card_risk:
        impact = "存在黄牌累计风险，防守侵略性和首发置信度小幅下调"
    else:
        impact = "暂无官方实时红黄牌数据，当前不将牌面因素计入模型"
    return {
        "team": team.name,
        "yellow_cards": discipline.yellow_cards,
        "red_cards": discipline.red_cards,
        "suspended_players": list(discipline.suspended_players),
        "card_risk_players": list(discipline.card_risk_players),
        "impact": impact,
    }


def predict_match(
    home_team: str,
    away_team: str,
    venue: Optional[str] = None,
    weather: Optional[str] = "normal",
    model_type: str = "form_weighted",
    advantage_team: str = "none",
    advantage_level: str = "none",
    is_knockout: bool = False,
    high_press: bool = False,
    home_key_absence: bool = False,
    away_key_absence: bool = False,
    home_fatigue: bool = False,
    away_fatigue: bool = False,
    match_round: Optional[int] = None,
    stage: Optional[str] = None,
    venue_factor: Optional[str] = "normal",
    force_neutral: bool = False,
    review_adjustment: Optional[Dict[str, Any]] = None,
    team_feature_adjustment: Optional[Dict[str, Any]] = None,
    match_context: Optional[Mapping[str, Any]] = None,
) -> Dict:
    home = _team(home_team)
    away = _team(away_team)
    home_adv = _advantage_points(advantage_team, advantage_level)
    applied_advantage_level = advantage_level
    auto_advantage_note: Optional[str] = None
    if not force_neutral and home_adv == 0 and advantage_team == "none" and advantage_level == "none":
        if not is_knockout and not stage:
            if _is_host_team(home):
                home_adv = 95
                applied_advantage_level = "full"
                auto_advantage_note = f"小组赛东道主: {home.name} 完整主场 +95 Elo"
            elif _is_host_team(away):
                home_adv = -95
                applied_advantage_level = "full"
                auto_advantage_note = f"小组赛东道主: {away.name} 完整主场 +95 Elo"
        else:
            if home.code == "USA":
                home_adv = 95
                applied_advantage_level = "full"
                auto_advantage_note = f"淘汰赛美国主场: {home.name} 完整主场 +95 Elo"
            elif away.code == "USA":
                home_adv = -95
                applied_advantage_level = "full"
                auto_advantage_note = f"淘汰赛美国主场: {away.name} 完整主场 +95 Elo"

    home_form, home_form_source = _resolved_form_score(home, review_adjustment, "home")
    away_form, away_form_source = _resolved_form_score(away, review_adjustment, "away")
    home_discipline = _discipline_for(home)
    away_discipline = _discipline_for(away)
    home_tactical_evidence = _contextual_tactic(home, "home", match_context, review_adjustment)
    away_tactical_evidence = _contextual_tactic(away, "away", match_context, review_adjustment)
    home_rating = home.elo_rating + home_adv
    away_rating = away.elo_rating

    if model_type in {"form_weighted", "monte_carlo"}:
        home_rating += int((home_form - 6.5) * 18)
        away_rating += int((away_form - 6.5) * 18)
        home_rating += int(_clip((away.fifa_rank - home.fifa_rank) * 1.2, -38, 38))

    rating_diff = home_rating - away_rating
    base_total_xg = 2.78
    if model_type == "form_weighted":
        base_total_xg = 2.92
    elif model_type == "monte_carlo":
        base_total_xg = 2.96
    base_total_xg += min(abs(rating_diff) / 1150, 0.58)
    home_share = _clip(0.5 + rating_diff / 1650, 0.24, 0.82)
    home_xg = base_total_xg * home_share
    away_xg = base_total_xg * (1 - home_share)

    factors = [
        f"Elo/实力: {home.name} {home.elo_rating} vs {away.name} {away.elo_rating}",
        f"FIFA排名: #{home.fifa_rank} vs #{away.fifa_rank}",
    ]
    for evidence in (home_tactical_evidence, away_tactical_evidence):
        factors.append(f"首发/阵型: {evidence.note}")

    if model_type in {"form_weighted", "monte_carlo"}:
        if home_form_source == away_form_source:
            factors.append(f"状态权重: {home.name} {home_form:.1f}/10 vs {away.name} {away_form:.1f}/10（{home_form_source}）")
        else:
            factors.append(
                f"状态权重: {home.name} {home_form:.1f}/10（{home_form_source}） "
                f"vs {away.name} {away_form:.1f}/10（{away_form_source}）"
            )

    if home_adv:
        team = home.name if home_adv > 0 else away.name
        level_label = "完整主场" if applied_advantage_level == "full" else "半主场"
        factors.append(f"主场地域: {team} {level_label} +{abs(home_adv)} Elo")
    elif auto_advantage_note:
        factors.append(f"主场地域: {auto_advantage_note}")
    elif force_neutral:
        factors.append("主场地域: 已手动强制中立，忽略自动地域优势")

    weather_multiplier, weather_desc = _weather_scale(weather)
    stage_multiplier, stage_desc = _stage_scale(stage, match_round, is_knockout)
    venue_multiplier, venue_desc = _venue_scale(venue_factor)
    total_multiplier = weather_multiplier * stage_multiplier * venue_multiplier
    if high_press:
        total_multiplier *= 1.08
        factors.append("战术补充: 高强度逼抢，比赛节奏和总xG上调")

    if home_key_absence:
        home_xg *= 0.86
        away_xg *= 1.04
        factors.append(f"人工补充: {home.name} 关键伤停/停赛")
    if away_key_absence:
        away_xg *= 0.86
        home_xg *= 1.04
        factors.append(f"人工补充: {away.name} 关键伤停/停赛")
    if home_fatigue:
        home_xg *= 0.93
        factors.append(f"人工补充: {home.name} 体能负荷偏高")
    if away_fatigue:
        away_xg *= 0.93
        factors.append(f"人工补充: {away.name} 体能负荷偏高")

    if review_adjustment and review_adjustment.get("applied"):
        home_review_delta = _clip(float(review_adjustment.get("home_attack_delta") or 0), -0.08, 0.10)
        away_review_delta = _clip(float(review_adjustment.get("away_attack_delta") or 0), -0.08, 0.10)
        if home_review_delta:
            home_xg *= 1 + home_review_delta
        if away_review_delta:
            away_xg *= 1 + away_review_delta
        reasons = list(review_adjustment.get("reasons") or [])[:2]
        reason_suffix = f": {'; '.join(reasons)}" if reasons else ""
        factors.append(f"赛后复盘: 已根据完赛表现/积分形势校准{reason_suffix}")
    feature_context = team_feature_adjustment if isinstance(team_feature_adjustment, Mapping) else {}
    if feature_context and feature_context.get("applied"):
        home_feature_delta = _clip(float(feature_context.get("home_attack_delta") or 0), -0.06, 0.06)
        away_feature_delta = _clip(float(feature_context.get("away_attack_delta") or 0), -0.06, 0.06)
        if home_feature_delta:
            home_xg *= 1 + home_feature_delta
        if away_feature_delta:
            away_xg *= 1 + away_feature_delta
        reasons = list(feature_context.get("reasons") or [])[:2]
        reason_suffix = f": {'; '.join(reasons)}" if reasons else ""
        factors.append(f"球队特征库: 已按赛后画像低权重校准{reason_suffix}")

    review_context = review_adjustment.get("review_context") if isinstance(review_adjustment, Mapping) else {}
    if isinstance(review_context, Mapping):
        form_context = review_context.get("form_context")
        if isinstance(form_context, Mapping):
            form_notes = [
                str(item.get("note"))
                for item in (form_context.get("home"), form_context.get("away"))
                if isinstance(item, Mapping) and item.get("note")
            ]
            for note in form_notes[:2]:
                factors.append(f"近况窗口: {note}")

    home_tactic_scale, away_tactic_scale, tactic_total_scale, tactical_matchup, tactic_notes = _tactical_matchup(
        home,
        away,
        home_tactical_evidence.tactic,
        away_tactical_evidence.tactic,
    )
    home_xg *= home_tactic_scale
    away_xg *= away_tactic_scale
    total_multiplier *= tactic_total_scale
    factors.extend([f"阵型相克: {note}" for note in tactic_notes])

    if home_discipline.suspended_players or home_discipline.red_cards:
        penalty = _clip(1 - 0.07 * len(home_discipline.suspended_players) - 0.05 * home_discipline.red_cards, 0.74, 1.0)
        home_xg *= penalty
        away_xg *= 1.03
        factors.append(f"红黄牌可用性: {home.name} {_discipline_note(home, home_discipline)}，首发与xG已修正")
    elif home_discipline.card_risk_players or home_discipline.yellow_cards >= 2:
        home_xg *= 0.98
        factors.append(f"黄牌累计风险: {home.name} {_discipline_note(home, home_discipline)}，防守侵略性小幅下调")

    if away_discipline.suspended_players or away_discipline.red_cards:
        penalty = _clip(1 - 0.07 * len(away_discipline.suspended_players) - 0.05 * away_discipline.red_cards, 0.74, 1.0)
        away_xg *= penalty
        home_xg *= 1.03
        factors.append(f"红黄牌可用性: {away.name} {_discipline_note(away, away_discipline)}，首发与xG已修正")
    elif away_discipline.card_risk_players or away_discipline.yellow_cards >= 2:
        away_xg *= 0.98
        factors.append(f"黄牌累计风险: {away.name} {_discipline_note(away, away_discipline)}，防守侵略性小幅下调")

    if home.is_debut or away.is_debut:
        debut_teams = "、".join(t.name for t in (home, away) if t.is_debut)
        factors.append(f"世界杯底蕴: {debut_teams} 新军，大赛紧张变量已纳入")

    home_xg = _clip(home_xg * total_multiplier, 0.25, 4.35)
    away_xg = _clip(away_xg * total_multiplier, 0.25, 4.35)
    third_round_strategy = _third_round_strategy_adjustment(match_round, review_adjustment, home, away)
    if third_round_strategy.get("applied"):
        home_xg = _clip(
            home_xg
            * float(third_round_strategy.get("home_xg_multiplier") or 1.0)
            * float(third_round_strategy.get("total_xg_multiplier") or 1.0),
            0.25,
            4.35,
        )
        away_xg = _clip(
            away_xg
            * float(third_round_strategy.get("away_xg_multiplier") or 1.0)
            * float(third_round_strategy.get("total_xg_multiplier") or 1.0),
            0.25,
            4.35,
        )
        strategy_notes = "；".join(str(note) for note in third_round_strategy.get("notes") or [] if note)
        factors.append(
            "第三轮战意: "
            f"{strategy_notes}；xG倍率 {third_round_strategy['home_xg_multiplier']}/"
            f"{third_round_strategy['away_xg_multiplier']}，总节奏 {third_round_strategy['total_xg_multiplier']}"
        )

    use_dc = model_type != "baseline"
    matrix = _score_matrix(home_xg, away_xg, use_dc=use_dc)
    expected_total = home_xg + away_xg
    total_goals_prediction = _total_goals_prediction(matrix, expected_total)
    home_win_90 = sum(prob for h, a, prob in matrix if h > a)
    draw_90 = sum(prob for h, a, prob in matrix if h == a)
    away_win_90 = sum(prob for h, a, prob in matrix if h < a)
    regular_time_probabilities = _probability_triplet(home_win_90, draw_90, away_win_90)

    penalty_probability = None
    extra_time_probability = None
    extra_time_decisive_probability = None
    tie_break_share = None
    if is_knockout:
        tie_break_share = 1 / (1 + 10 ** (-(home_rating - away_rating) / 360))
        home_win = home_win_90 + draw_90 * tie_break_share
        away_win = away_win_90 + draw_90 * (1 - tie_break_share)
        draw_prob = 0.0
        extra_time_probability = draw_90
        penalty_probability = min(draw_90, _clip(draw_90 * 0.68, 0.0, 0.42))
        extra_time_decisive_probability = max(0.0, draw_90 - penalty_probability)
        factors.append(
            "淘汰赛处理: "
            f"90分钟平局 {draw_90:.1%} 转入加时/点球晋级概率，"
            f"加时决胜约 {extra_time_decisive_probability:.1%}，点球决胜约 {penalty_probability:.1%}"
        )
    else:
        home_win, draw_prob, away_win = home_win_90, draw_90, away_win_90

    total = home_win + draw_prob + away_win
    home_win = home_win / total
    draw_prob = draw_prob / total
    away_win = away_win / total

    if not is_knockout and review_adjustment and review_adjustment.get("applied"):
        draw_delta = _clip(float(review_adjustment.get("draw_probability_delta") or 0), 0.0, 0.08)
        if draw_delta:
            draw_prob = min(draw_prob + draw_delta, 0.45)
            remaining = max(0.05, 1 - draw_prob)
            win_total = max(0.001, home_win + away_win)
            home_win = remaining * home_win / win_total
            away_win = remaining * away_win / win_total
            factors.append(f"赛后复盘: 小组出线形势提高平局动机 +{draw_delta * 100:.1f}%")

    if not is_knockout and third_round_strategy.get("applied"):
        strategy_draw_delta = _clip(float(third_round_strategy.get("draw_probability_delta") or 0), 0.0, 0.065)
        if strategy_draw_delta:
            cap = float(third_round_strategy.get("draw_probability_cap") or 0.50)
            draw_prob = min(draw_prob + strategy_draw_delta, cap)
            remaining = max(0.05, 1 - draw_prob)
            win_total = max(0.001, home_win + away_win)
            home_win = remaining * home_win / win_total
            away_win = remaining * away_win / win_total
            factors.append(
                f"第三轮战意: 出线/路径情景提高平局或不败动机 +{strategy_draw_delta * 100:.1f}%，"
                f"单项上限 {cap * 100:.0f}%"
            )

    if not is_knockout and feature_context and feature_context.get("applied"):
        feature_draw_delta = _clip(float(feature_context.get("draw_probability_delta") or 0), 0.0, 0.04)
        if feature_draw_delta:
            draw_prob = min(draw_prob + feature_draw_delta, 0.43)
            remaining = max(0.05, 1 - draw_prob)
            win_total = max(0.001, home_win + away_win)
            home_win = remaining * home_win / win_total
            away_win = remaining * away_win / win_total
            factors.append(f"球队特征库: 低比分/平局倾向修正 +{feature_draw_delta * 100:.1f}%")

    model_probabilities = _probability_triplet(home_win, draw_prob, away_win)
    market_odds = fetch_market_odds(
        home.name,
        away.name,
        home.code,
        away.code,
        model_probabilities=model_probabilities,
        expected_total=expected_total,
    )
    public_data_sources = build_public_data_sources(market_odds)
    calibrated_probabilities, market_calibration = _calibrate_with_market(model_probabilities, market_odds)
    home_win = calibrated_probabilities["home"]
    draw_prob = calibrated_probabilities["draw"]
    away_win = calibrated_probabilities["away"]
    if is_knockout and draw_prob > 0:
        tie_break_share = tie_break_share if tie_break_share is not None else 0.5
        home_win += draw_prob * tie_break_share
        away_win += draw_prob * (1 - tie_break_share)
        draw_prob = 0.0
        knockout_total = home_win + away_win
        home_win = home_win / knockout_total
        away_win = away_win / knockout_total
        if isinstance(market_calibration, dict):
            market_calibration["final"] = {
                "home": _round3(home_win),
                "draw": 0.0,
                "away": _round3(away_win),
            }
            market_calibration["final_probabilities"] = dict(market_calibration["final"])
    final_probabilities = _probability_triplet(home_win, draw_prob, away_win)

    if market_odds.get("totals"):
        market_totals = market_odds["totals"]
        total_goals_prediction["market_line"] = market_totals.get("line")
        total_goals_prediction["market_over_probability"] = market_totals.get("over_probability")
        total_goals_prediction["market_under_probability"] = market_totals.get("under_probability")
        total_goals_prediction["market_recommendation"] = (
            f"大{market_totals.get('line')}"
            if (market_totals.get("over_probability") or 0) >= (market_totals.get("under_probability") or 0)
            else f"小{market_totals.get('line')}"
        )

    factors.append(
        "大小球校验: "
        f"{total_goals_prediction.get('recommendation')}，"
        f"主线概率 {(total_goals_prediction.get('side_probability') or 0) * 100:.1f}%，"
        f"信号强度 {(total_goals_prediction.get('signal_strength') or total_goals_prediction.get('confidence') or 0) * 100:.1f}%"
    )

    if market_calibration.get("source") == "football_data_historical_prior":
        if market_calibration.get("applied"):
            factors.append(
                f"市场信号校准: 公开历史赔率样本与模型分歧 {market_calibration['difference'] * 100:.1f}%，"
                f"仅按 {market_calibration['weight'] * 100:.0f}% 低权重修正"
            )
        else:
            factors.append("市场信号校准: 已接入公开历史赔率样本，方向接近，未调整原始预测")
    elif market_calibration.get("applied"):
        factors.append(
            f"市场信号校准: 实时赔率与模型最大分歧 {market_calibration['difference'] * 100:.1f}%，"
            f"按 {market_calibration['weight'] * 100:.0f}% 权重校准"
        )
    elif market_odds.get("h2h"):
        factors.append("市场信号校准: 实时赔率与模型接近，未调整原始预测")
    else:
        market_status = _market_signal_status_label(market_odds.get("status", "not_available"))
        factors.append(f"市场信号校准: {market_status}，暂不做硬校准")

    preferred_outcome = max(
        (("home", home_win), ("draw", draw_prob), ("away", away_win)),
        key=lambda item: item[1],
    )[0]
    representative_score = _select_market_aware_score(
        matrix,
        expected_total,
        home_xg,
        away_xg,
        preferred_outcome,
        market_odds,
        market_calibration,
    )
    score_distribution_probabilities = regular_time_probabilities if is_knockout else final_probabilities
    prediction_matrix = _calibrated_score_matrix(matrix, score_distribution_probabilities, home_xg, away_xg)
    ranked_scores = sorted(prediction_matrix, key=lambda item: item[2], reverse=True)
    primary_score = _select_primary_score(
        prediction_matrix,
        score_distribution_probabilities,
        expected_total,
        representative_score,
    )
    if ranked_scores and (primary_score[0], primary_score[1]) != (ranked_scores[0][0], ranked_scores[0][1]):
        factors.append("本届节奏校准: 高总进球代表比分保留在比分池，用于提示尾段进球和大胜溢出")
    top_scores = [primary_score] + [
        item for item in ranked_scores
        if item[0] != primary_score[0] or item[1] != primary_score[1]
    ][:4]
    top_scores, score_discipline_notes = _apply_score_discipline(
        top_scores,
        prediction_matrix,
        score_distribution_probabilities,
        expected_total,
        home_xg,
        away_xg,
        match_round,
        is_knockout,
        market_calibration,
        representative_score,
    )
    factors.extend(score_discipline_notes)
    display_scores = sorted(top_scores[:3], key=lambda item: item[2], reverse=True)
    possible_scores = [
        {"score": f"{h}-{a}", "probability": round(prob * 100, 2)}
        for h, a, prob in display_scores
    ]
    predicted_score = possible_scores[0]["score"]
    predicted_score_probability = possible_scores[0]["probability"]
    upset_excluded_scores = {(h, a) for h, a, _ in top_scores[:3]}

    if weather not in {None, "normal"}:
        factors.append(weather_desc)
    if venue_factor not in {None, "normal"}:
        factors.append(venue_desc)
    factors.append(stage_desc)
    if model_type == "monte_carlo":
        factors.append("Monte Carlo稳定版: 使用比分概率矩阵等价采样，避免每次请求随机漂移")
    elif model_type == "form_weighted":
        factors.append("Form Weighted: Elo + FIFA排名 + 本届正式赛状态窗口 + 市场信号")
    else:
        factors.append("Baseline: Elo + 主场/场地基础因子")

    margin = abs(home_win - away_win)
    confidence = _clip(max(home_win, draw_prob, away_win) * 0.82 + margin * 0.18, 0.38, 0.91)
    upset_prediction = _upset_prediction(
        home,
        away,
        final_probabilities,
        prediction_matrix,
        market_odds,
        market_calibration,
        rating_diff,
        expected_total,
        primary_score,
        home_xg,
        away_xg,
        upset_excluded_scores,
    )
    set_piece_card_prediction = _set_piece_card_prediction(
        home,
        away,
        home_xg,
        away_xg,
        high_press,
        is_knockout,
        home_discipline,
        away_discipline,
        review_adjustment,
    )
    factors.append(
        "角球/黄牌: "
        f"预计角球 {set_piece_card_prediction['corners']['total']} 个，"
        f"黄牌 {set_piece_card_prediction['yellow_cards']['total']} 张，"
        "按本届正式赛窗口、xG和比赛强度修正"
    )
    knockout_decision = None
    if is_knockout:
        tie_break_value = tie_break_share if tie_break_share is not None else 0.5
        extra_time_value = extra_time_probability or 0.0
        penalty_value = penalty_probability or 0.0
        extra_decisive_value = extra_time_decisive_probability or 0.0
        knockout_decision = {
            "regular_time_home_win_probability": _round3(regular_time_probabilities["home"]),
            "regular_time_draw_probability": _round3(regular_time_probabilities["draw"]),
            "regular_time_away_win_probability": _round3(regular_time_probabilities["away"]),
            "extra_time_probability": _round3(extra_time_value),
            "extra_time_decisive_probability": _round3(extra_decisive_value),
            "penalty_probability": _round3(penalty_value),
            "advancement_home_probability": _round3(home_win),
            "advancement_away_probability": _round3(away_win),
            "tie_break_share": _round3(tie_break_value),
            "basis": [
                "FIFA 2026淘汰赛规则: 90分钟打平后进行上下半场各15分钟加时赛",
                "加时仍平后进入点球大战；点球仅用于决出晋级方，不改写120分钟比分",
                "90分钟比分沿用Elo/FIFA排名/状态权重/xG概率矩阵",
                "加时与点球层参考历史世界杯淘汰赛先验，并按双方强度差修正晋级倾向",
            ],
        }

    return {
        "home_win_probability": round(home_win, 3),
        "draw_probability": round(draw_prob, 3),
        "away_win_probability": round(away_win, 3),
        "predicted_score": predicted_score,
        "regulation_predicted_score": predicted_score if is_knockout else None,
        "predicted_score_probability": predicted_score_probability,
        "possible_scores": possible_scores,
        "regular_time_probabilities": {
            "home": _round3(regular_time_probabilities["home"]),
            "draw": _round3(regular_time_probabilities["draw"]),
            "away": _round3(regular_time_probabilities["away"]),
        } if is_knockout else None,
        "extra_time_probability": _round3(extra_time_probability or 0.0) if is_knockout else None,
        "extra_time_decisive_probability": _round3(extra_time_decisive_probability or 0.0) if is_knockout else None,
        "penalty_probability": _round3(penalty_probability or 0.0) if is_knockout else None,
        "knockout_decision": knockout_decision,
        "confidence": round(confidence, 3),
        "model_version": "美加墨世界杯AI预测模型 26.5",
        "model_type": model_type,
        "factors": factors,
        "xg_home": _round2(home_xg),
        "xg_away": _round2(away_xg),
        "total_goals_prediction": total_goals_prediction,
        "market_odds": market_odds,
        "market_calibration": market_calibration,
        "public_data_sources": public_data_sources,
        "upset_prediction": upset_prediction,
        "set_piece_card_prediction": set_piece_card_prediction,
        "ranking_snapshot": _ranking_snapshot_payload(home, away),
        "tactical_analysis": [
            _tactical_payload(home, home_tactical_evidence),
            _tactical_payload(away, away_tactical_evidence),
        ],
        "tactical_matchup": tactical_matchup,
        "lineup_prediction": [
            _lineup_payload(home, home_discipline, home_tactical_evidence),
            _lineup_payload(away, away_discipline, away_tactical_evidence),
        ],
        "key_players": _key_player_payload(home, home_xg) + _key_player_payload(away, away_xg),
        "goal_scorer_predictions": _goal_scorer_payload(home, away, home_xg, away_xg),
        "discipline_analysis": [
            _discipline_payload(home, home_discipline),
            _discipline_payload(away, away_discipline),
        ],
        "review_adjustment": review_adjustment if review_adjustment else None,
        "team_feature_adjustment": team_feature_adjustment if team_feature_adjustment else None,
        "profile_adjustment": team_feature_adjustment if team_feature_adjustment else None,
        "is_knockout": is_knockout,
        "venue": venue,
    }
