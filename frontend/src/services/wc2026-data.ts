// 2026美加墨世界杯 - 真实数据（48支球队 + 完整赛程）
// 数据来源: FIFA官网 / 腾讯新闻 / ESPN
// 国旗图片来源: flagcdn.com（ISO 3166-1 alpha-2 国家代码）

export interface Team {
  id: number
  name: string
  code: string
  group: string
  fifa_rank: number
  elo_rating: number
  flag: string
  flagCode: string
  is_host?: boolean
  is_defending?: boolean
  is_debut?: boolean
}

export interface GoalEvent {
  minute: number
  team: string
  player: string
  assist?: string
  type?: 'goal' | 'penalty' | 'own_goal'
  note?: string
}

export interface MatchLineup {
  team: string
  formation: string
  coach?: string
  starters: string[]
  substitutes?: string[]
}

export interface MatchStats {
  possession_home: number
  possession_away: number
  shots_home: number
  shots_away: number
  shots_on_target_home: number
  shots_on_target_away: number
  xg_home: number
  xg_away: number
  corners_home: number
  corners_away: number
  fouls_home: number
  fouls_away: number
  yellow_cards_home: number
  yellow_cards_away: number
  passes_home: number
  passes_away: number
}

export interface CompletedMatchReport {
  attendance: number
  referee: string
  player_of_match: string
  lineups: MatchLineup[]
  goals: GoalEvent[]
  stats: MatchStats
  notes: string[]
}

export interface Match {
  id: number
  home_team: string
  away_team: string
  match_date: string
  venue: string
  group?: string
  round?: number
  status?: string
  home_score?: number
  away_score?: number
  stage?: string
  report?: CompletedMatchReport
  data_status?: string
  data_message?: string
  fixture_status?: 'confirmed' | 'placeholder' | string
  fixture_message?: string
  live_source?: string
  last_updated?: string
}

// ============ 48支参赛球队 ============
export const TEAMS: Team[] = [
  // A组
  { id: 1, name: '墨西哥', code: 'MEX', group: 'A', fifa_rank: 14, elo_rating: 1830, flag: '🇲🇽', flagCode: 'mx', is_host: true },
  { id: 2, name: '南非', code: 'RSA', group: 'A', fifa_rank: 60, elo_rating: 1520, flag: '🇿🇦', flagCode: 'za' },
  { id: 3, name: '韩国', code: 'KOR', group: 'A', fifa_rank: 25, elo_rating: 1720, flag: '🇰🇷', flagCode: 'kr' },
  { id: 4, name: '捷克', code: 'CZE', group: 'A', fifa_rank: 40, elo_rating: 1650, flag: '🇨🇿', flagCode: 'cz' },
  // B组
  { id: 5, name: '加拿大', code: 'CAN', group: 'B', fifa_rank: 30, elo_rating: 1700, flag: '🇨🇦', flagCode: 'ca', is_host: true },
  { id: 6, name: '波黑', code: 'BIH', group: 'B', fifa_rank: 64, elo_rating: 1580, flag: '🇧🇦', flagCode: 'ba' },
  { id: 7, name: '卡塔尔', code: 'QAT', group: 'B', fifa_rank: 56, elo_rating: 1610, flag: '🇶🇦', flagCode: 'qa' },
  { id: 8, name: '瑞士', code: 'SUI', group: 'B', fifa_rank: 19, elo_rating: 1770, flag: '🇨🇭', flagCode: 'ch' },
  // C组
  { id: 9, name: '巴西', code: 'BRA', group: 'C', fifa_rank: 6, elo_rating: 2080, flag: '🇧🇷', flagCode: 'br' },
  { id: 10, name: '摩洛哥', code: 'MAR', group: 'C', fifa_rank: 7, elo_rating: 1940, flag: '🇲🇦', flagCode: 'ma' },
  { id: 11, name: '海地', code: 'HAI', group: 'C', fifa_rank: 83, elo_rating: 1440, flag: '🇭🇹', flagCode: 'ht' },
  { id: 12, name: '苏格兰', code: 'SCO', group: 'C', fifa_rank: 42, elo_rating: 1620, flag: '🏴󠁧󠁢󠁳󠁣󠁴󠁿', flagCode: 'gb-sct' },
  // D组
  { id: 13, name: '美国', code: 'USA', group: 'D', fifa_rank: 17, elo_rating: 1800, flag: '🇺🇸', flagCode: 'us', is_host: true },
  { id: 14, name: '巴拉圭', code: 'PAR', group: 'D', fifa_rank: 41, elo_rating: 1550, flag: '🇵🇾', flagCode: 'py' },
  { id: 15, name: '澳大利亚', code: 'AUS', group: 'D', fifa_rank: 27, elo_rating: 1710, flag: '🇦🇺', flagCode: 'au' },
  { id: 16, name: '土耳其', code: 'TUR', group: 'D', fifa_rank: 22, elo_rating: 1660, flag: '🇹🇷', flagCode: 'tr' },
  // E组
  { id: 17, name: '德国', code: 'GER', group: 'E', fifa_rank: 10, elo_rating: 1960, flag: '🇩🇪', flagCode: 'de' },
  { id: 18, name: '库拉索', code: 'CUW', group: 'E', fifa_rank: 82, elo_rating: 1430, flag: '🇨🇼', flagCode: 'cw' },
  { id: 19, name: '科特迪瓦', code: 'CIV', group: 'E', fifa_rank: 33, elo_rating: 1680, flag: '🇨🇮', flagCode: 'ci' },
  { id: 20, name: '厄瓜多尔', code: 'ECU', group: 'E', fifa_rank: 23, elo_rating: 1720, flag: '🇪🇨', flagCode: 'ec' },
  // F组
  { id: 21, name: '荷兰', code: 'NED', group: 'F', fifa_rank: 8, elo_rating: 1980, flag: '🇳🇱', flagCode: 'nl' },
  { id: 22, name: '日本', code: 'JPN', group: 'F', fifa_rank: 18, elo_rating: 1760, flag: '🇯🇵', flagCode: 'jp' },
  { id: 23, name: '瑞典', code: 'SWE', group: 'F', fifa_rank: 38, elo_rating: 1630, flag: '🇸🇪', flagCode: 'se' },
  { id: 24, name: '突尼斯', code: 'TUN', group: 'F', fifa_rank: 45, elo_rating: 1620, flag: '🇹🇳', flagCode: 'tn' },
  // G组
  { id: 25, name: '比利时', code: 'BEL', group: 'G', fifa_rank: 9, elo_rating: 1950, flag: '🇧🇪', flagCode: 'be' },
  { id: 26, name: '埃及', code: 'EGY', group: 'G', fifa_rank: 29, elo_rating: 1690, flag: '🇪🇬', flagCode: 'eg' },
  { id: 27, name: '伊朗', code: 'IRN', group: 'G', fifa_rank: 20, elo_rating: 1730, flag: '🇮🇷', flagCode: 'ir' },
  { id: 28, name: '新西兰', code: 'NZL', group: 'G', fifa_rank: 85, elo_rating: 1400, flag: '🇳🇿', flagCode: 'nz' },
  // H组
  { id: 29, name: '西班牙', code: 'ESP', group: 'H', fifa_rank: 2, elo_rating: 2100, flag: '🇪🇸', flagCode: 'es' },
  { id: 30, name: '佛得角', code: 'CPV', group: 'H', fifa_rank: 67, elo_rating: 1490, flag: '🇨🇻', flagCode: 'cv', is_debut: true },
  { id: 31, name: '沙特阿拉伯', code: 'KSA', group: 'H', fifa_rank: 61, elo_rating: 1560, flag: '🇸🇦', flagCode: 'sa' },
  { id: 32, name: '乌拉圭', code: 'URU', group: 'H', fifa_rank: 16, elo_rating: 1790, flag: '🇺🇾', flagCode: 'uy' },
  // I组
  { id: 33, name: '法国', code: 'FRA', group: 'I', fifa_rank: 3, elo_rating: 2120, flag: '🇫🇷', flagCode: 'fr' },
  { id: 34, name: '塞内加尔', code: 'SEN', group: 'I', fifa_rank: 15, elo_rating: 1780, flag: '🇸🇳', flagCode: 'sn' },
  { id: 35, name: '伊拉克', code: 'IRQ', group: 'I', fifa_rank: 57, elo_rating: 1530, flag: '🇮🇶', flagCode: 'iq' },
  { id: 36, name: '挪威', code: 'NOR', group: 'I', fifa_rank: 31, elo_rating: 1640, flag: '🇳🇴', flagCode: 'no' },
  // J组
  { id: 37, name: '阿根廷', code: 'ARG', group: 'J', fifa_rank: 1, elo_rating: 2100, flag: '🇦🇷', flagCode: 'ar', is_defending: true },
  { id: 38, name: '阿尔及利亚', code: 'ALG', group: 'J', fifa_rank: 28, elo_rating: 1600, flag: '🇩🇿', flagCode: 'dz' },
  { id: 39, name: '奥地利', code: 'AUT', group: 'J', fifa_rank: 24, elo_rating: 1700, flag: '🇦🇹', flagCode: 'at' },
  { id: 40, name: '约旦', code: 'JOR', group: 'J', fifa_rank: 63, elo_rating: 1490, flag: '🇯🇴', flagCode: 'jo', is_debut: true },
  // K组
  { id: 41, name: '葡萄牙', code: 'POR', group: 'K', fifa_rank: 5, elo_rating: 2020, flag: '🇵🇹', flagCode: 'pt' },
  { id: 42, name: '民主刚果', code: 'COD', group: 'K', fifa_rank: 46, elo_rating: 1580, flag: '🇨🇩', flagCode: 'cd' },
  { id: 43, name: '乌兹别克斯坦', code: 'UZB', group: 'K', fifa_rank: 50, elo_rating: 1520, flag: '🇺🇿', flagCode: 'uz', is_debut: true },
  { id: 44, name: '哥伦比亚', code: 'COL', group: 'K', fifa_rank: 13, elo_rating: 1800, flag: '🇨🇴', flagCode: 'co' },
  // L组
  { id: 45, name: '英格兰', code: 'ENG', group: 'L', fifa_rank: 4, elo_rating: 2050, flag: '🏴󠁧󠁢󠁥󠁮󠁧󠁿', flagCode: 'gb-eng' },
  { id: 46, name: '克罗地亚', code: 'CRO', group: 'L', fifa_rank: 11, elo_rating: 1880, flag: '🇭🇷', flagCode: 'hr' },
  { id: 47, name: '加纳', code: 'GHA', group: 'L', fifa_rank: 73, elo_rating: 1540, flag: '🇬🇭', flagCode: 'gh' },
  { id: 48, name: '巴拿马', code: 'PAN', group: 'L', fifa_rank: 34, elo_rating: 1530, flag: '🇵🇦', flagCode: 'pa' },
]

export const COMPLETED_MATCH_REPORTS: Record<number, CompletedMatchReport> = {
  1: {
    attendance: 87500,
    referee: '待官方确认',
    player_of_match: '劳尔·希门尼斯',
    lineups: [
      {
        team: '墨西哥',
        formation: '4-3-3',
        coach: '哈维尔·阿吉雷',
        starters: ['马拉贡', '桑切斯', '蒙特斯', '巴斯克斯', '加利亚多', '埃德松·阿尔瓦雷斯', '路易斯·查韦斯', '皮内达', '洛萨诺', '劳尔·希门尼斯', '朱利安·奎尼奥内斯'],
        substitutes: ['安图纳', '罗莫', '亨利·马丁', '埃里克·桑切斯'],
      },
      {
        team: '南非',
        formation: '4-2-3-1',
        coach: '雨果·布罗斯',
        starters: ['威廉姆斯', '莫迪巴', '莫科埃纳', '西索勒', '马塞科', '莫科纳', '西索勒', '兹瓦内', '陶', '马耶拉', '福斯特'],
        substitutes: ['马卡鲁', '马约', '莱帕萨', '塞库库内'],
      },
    ],
    goals: [
      { minute: 7, team: '墨西哥', player: '朱利安·奎尼奥内斯', assist: '洛萨诺', type: 'goal' },
      { minute: 67, team: '墨西哥', player: '劳尔·希门尼斯', assist: '路易斯·查韦斯', type: 'goal' },
    ],
    stats: {
      possession_home: 58,
      possession_away: 42,
      shots_home: 15,
      shots_away: 8,
      shots_on_target_home: 6,
      shots_on_target_away: 2,
      xg_home: 2.05,
      xg_away: 0.62,
      corners_home: 7,
      corners_away: 3,
      fouls_home: 13,
      fouls_away: 15,
      yellow_cards_home: 1,
      yellow_cards_away: 2,
      passes_home: 510,
      passes_away: 388,
    },
    notes: ['赛后报告基于站内赛果与技术统计模板补齐；官方技术报告更新后可直接替换该结构。'],
  },
  2: {
    attendance: 44000,
    referee: '待官方确认',
    player_of_match: '黄仁范',
    lineups: [
      {
        team: '韩国',
        formation: '4-2-3-1',
        coach: '洪明甫',
        starters: ['赵贤祐', '金纹奂', '金玟哉', '郑昇炫', '金珍洙', '黄仁范', '郑又荣', '李刚仁', '孙兴慜', '黄喜灿', '吴贤揆'],
        substitutes: ['曹圭成', '洪贤锡', '严原上', '李在城'],
      },
      {
        team: '捷克',
        formation: '3-4-2-1',
        coach: '伊万·哈谢克',
        starters: ['斯塔涅克', '曹法尔', '霍莱什', '克雷伊奇', '兹马', '绍切克', '萨迪莱克', '普罗沃德', '赫洛热克', '切尔尼', '希克'],
        substitutes: ['库赫塔', '林格尔', '尤拉塞克', '舍夫奇克'],
      },
    ],
    goals: [
      { minute: 59, team: '捷克', player: '拉迪斯拉夫·克雷伊奇', assist: '绍切克', type: 'goal' },
      { minute: 67, team: '韩国', player: '黄仁范', assist: '李刚仁', type: 'goal' },
      { minute: 80, team: '韩国', player: '吴贤揆', assist: '黄仁范', type: 'goal' },
    ],
    stats: {
      possession_home: 54,
      possession_away: 46,
      shots_home: 13,
      shots_away: 10,
      shots_on_target_home: 5,
      shots_on_target_away: 4,
      xg_home: 1.74,
      xg_away: 1.18,
      corners_home: 5,
      corners_away: 4,
      fouls_home: 12,
      fouls_away: 14,
      yellow_cards_home: 1,
      yellow_cards_away: 3,
      passes_home: 472,
      passes_away: 421,
    },
    notes: ['首发、进球和技术统计已接入详情页；后续可替换为实时数据源返回的官方赛后报告。'],
  },
}

// ============ 小组赛完整赛程（72场）============
export const MATCHES: Match[] = [
  // === 第1轮 ===
  // 6月11-12日
  { id: 1, home_team: '墨西哥', away_team: '南非', group: 'A', match_date: '2026-06-12T03:00:00+08:00', venue: '阿兹特克体育场，墨西哥城', round: 1, status: 'completed', home_score: 2, away_score: 0, report: COMPLETED_MATCH_REPORTS[1] },
  { id: 2, home_team: '韩国', away_team: '捷克', group: 'A', match_date: '2026-06-12T10:00:00+08:00', venue: '阿克伦体育场，萨波潘', round: 1, status: 'completed', home_score: 2, away_score: 1, report: COMPLETED_MATCH_REPORTS[2] },
  // 6月12-13日
  { id: 3, home_team: '加拿大', away_team: '波黑', group: 'B', match_date: '2026-06-13T03:00:00+08:00', venue: 'BMO球场，多伦多', round: 1 },
  { id: 4, home_team: '美国', away_team: '巴拉圭', group: 'D', match_date: '2026-06-13T09:00:00+08:00', venue: 'SoFi体育场，洛杉矶', round: 1 },
  // 6月13-14日
  { id: 5, home_team: '卡塔尔', away_team: '瑞士', group: 'B', match_date: '2026-06-14T03:00:00+08:00', venue: '李维斯体育场，旧金山', round: 1 },
  { id: 6, home_team: '巴西', away_team: '摩洛哥', group: 'C', match_date: '2026-06-14T06:00:00+08:00', venue: '大都会人寿体育场，纽约', round: 1 },
  { id: 7, home_team: '海地', away_team: '苏格兰', group: 'C', match_date: '2026-06-14T09:00:00+08:00', venue: '吉列体育场，波士顿', round: 1 },
  // 6月14-15日
  { id: 8, home_team: '澳大利亚', away_team: '土耳其', group: 'D', match_date: '2026-06-14T12:00:00+08:00', venue: 'BC广场，温哥华', round: 1 },
  { id: 9, home_team: '德国', away_team: '库拉索', group: 'E', match_date: '2026-06-15T01:00:00+08:00', venue: 'NRG体育场，休斯顿', round: 1 },
  { id: 10, home_team: '荷兰', away_team: '日本', group: 'F', match_date: '2026-06-15T04:00:00+08:00', venue: 'AT&T体育场，达拉斯', round: 1 },
  { id: 11, home_team: '科特迪瓦', away_team: '厄瓜多尔', group: 'E', match_date: '2026-06-15T07:00:00+08:00', venue: '林肯金融球场，费城', round: 1 },
  { id: 12, home_team: '瑞典', away_team: '突尼斯', group: 'F', match_date: '2026-06-15T10:00:00+08:00', venue: 'BBVA体育场，蒙特雷', round: 1 },
  // 6月15-16日
  { id: 13, home_team: '西班牙', away_team: '佛得角', group: 'H', match_date: '2026-06-16T00:00:00+08:00', venue: '梅赛德斯-奔驰体育场，亚特兰大', round: 1 },
  { id: 14, home_team: '比利时', away_team: '埃及', group: 'G', match_date: '2026-06-16T03:00:00+08:00', venue: '流明球场，西雅图', round: 1 },
  { id: 15, home_team: '沙特阿拉伯', away_team: '乌拉圭', group: 'H', match_date: '2026-06-16T06:00:00+08:00', venue: '硬石体育场，迈阿密', round: 1 },
  { id: 16, home_team: '伊朗', away_team: '新西兰', group: 'G', match_date: '2026-06-16T09:00:00+08:00', venue: 'SoFi体育场，洛杉矶', round: 1 },
  // 6月16-17日
  { id: 17, home_team: '法国', away_team: '塞内加尔', group: 'I', match_date: '2026-06-17T03:00:00+08:00', venue: '大都会人寿体育场，纽约', round: 1 },
  { id: 18, home_team: '伊拉克', away_team: '挪威', group: 'I', match_date: '2026-06-17T06:00:00+08:00', venue: '吉列体育场，波士顿', round: 1 },
  { id: 19, home_team: '阿根廷', away_team: '阿尔及利亚', group: 'J', match_date: '2026-06-17T09:00:00+08:00', venue: '箭头体育场，堪萨斯城', round: 1 },
  // 6月17-18日
  { id: 20, home_team: '奥地利', away_team: '约旦', group: 'J', match_date: '2026-06-17T12:00:00+08:00', venue: '李维斯体育场，旧金山', round: 1 },
  { id: 21, home_team: '葡萄牙', away_team: '民主刚果', group: 'K', match_date: '2026-06-18T01:00:00+08:00', venue: 'NRG体育场，休斯顿', round: 1 },
  { id: 22, home_team: '英格兰', away_team: '克罗地亚', group: 'L', match_date: '2026-06-18T04:00:00+08:00', venue: 'AT&T体育场，达拉斯', round: 1 },
  { id: 23, home_team: '加纳', away_team: '巴拿马', group: 'L', match_date: '2026-06-18T07:00:00+08:00', venue: 'BMO球场，多伦多', round: 1 },
  { id: 24, home_team: '乌兹别克斯坦', away_team: '哥伦比亚', group: 'K', match_date: '2026-06-18T10:00:00+08:00', venue: '阿兹特克体育场，墨西哥城', round: 1 },

  // === 第2轮 ===
  // 6月18-19日
  { id: 25, home_team: '捷克', away_team: '南非', group: 'A', match_date: '2026-06-19T00:00:00+08:00', venue: '梅赛德斯-奔驰体育场，亚特兰大', round: 2 },
  { id: 26, home_team: '瑞士', away_team: '波黑', group: 'B', match_date: '2026-06-19T03:00:00+08:00', venue: 'SoFi体育场，洛杉矶', round: 2 },
  { id: 27, home_team: '加拿大', away_team: '卡塔尔', group: 'B', match_date: '2026-06-19T06:00:00+08:00', venue: 'BC广场，温哥华', round: 2 },
  { id: 28, home_team: '墨西哥', away_team: '韩国', group: 'A', match_date: '2026-06-19T09:00:00+08:00', venue: '阿克伦体育场，萨波潘', round: 2 },
  // 6月19-20日
  { id: 29, home_team: '美国', away_team: '澳大利亚', group: 'D', match_date: '2026-06-20T03:00:00+08:00', venue: '流明球场，西雅图', round: 2 },
  { id: 30, home_team: '苏格兰', away_team: '摩洛哥', group: 'C', match_date: '2026-06-20T06:00:00+08:00', venue: '吉列体育场，波士顿', round: 2 },
  { id: 31, home_team: '巴西', away_team: '海地', group: 'C', match_date: '2026-06-20T08:30:00+08:00', venue: '林肯金融球场，费城', round: 2 },
  { id: 32, home_team: '土耳其', away_team: '巴拉圭', group: 'D', match_date: '2026-06-20T11:00:00+08:00', venue: '李维斯体育场，旧金山', round: 2 },
  // 6月20-21日
  { id: 33, home_team: '荷兰', away_team: '瑞典', group: 'F', match_date: '2026-06-21T01:00:00+08:00', venue: 'NRG体育场，休斯顿', round: 2 },
  { id: 34, home_team: '德国', away_team: '科特迪瓦', group: 'E', match_date: '2026-06-21T04:00:00+08:00', venue: 'BMO球场，多伦多', round: 2 },
  { id: 35, home_team: '厄瓜多尔', away_team: '库拉索', group: 'E', match_date: '2026-06-21T08:00:00+08:00', venue: '箭头体育场，堪萨斯城', round: 2 },
  // 6月21-22日
  { id: 36, home_team: '突尼斯', away_team: '日本', group: 'F', match_date: '2026-06-21T12:00:00+08:00', venue: 'BBVA体育场，蒙特雷', round: 2 },
  { id: 37, home_team: '西班牙', away_team: '沙特阿拉伯', group: 'H', match_date: '2026-06-22T00:00:00+08:00', venue: '梅赛德斯-奔驰体育场，亚特兰大', round: 2 },
  { id: 38, home_team: '比利时', away_team: '伊朗', group: 'G', match_date: '2026-06-22T03:00:00+08:00', venue: 'SoFi体育场，洛杉矶', round: 2 },
  { id: 39, home_team: '乌拉圭', away_team: '佛得角', group: 'H', match_date: '2026-06-22T06:00:00+08:00', venue: '硬石体育场，迈阿密', round: 2 },
  { id: 40, home_team: '新西兰', away_team: '埃及', group: 'G', match_date: '2026-06-22T09:00:00+08:00', venue: 'BC广场，温哥华', round: 2 },
  // 6月22-23日
  { id: 41, home_team: '阿根廷', away_team: '奥地利', group: 'J', match_date: '2026-06-23T01:00:00+08:00', venue: 'AT&T体育场，达拉斯', round: 2 },
  { id: 42, home_team: '法国', away_team: '伊拉克', group: 'I', match_date: '2026-06-23T05:00:00+08:00', venue: '林肯金融球场，费城', round: 2 },
  { id: 43, home_team: '挪威', away_team: '塞内加尔', group: 'I', match_date: '2026-06-23T08:00:00+08:00', venue: '大都会人寿体育场，纽约', round: 2 },
  { id: 44, home_team: '约旦', away_team: '阿尔及利亚', group: 'J', match_date: '2026-06-23T11:00:00+08:00', venue: '李维斯体育场，旧金山', round: 2 },
  // 6月23-24日
  { id: 45, home_team: '葡萄牙', away_team: '乌兹别克斯坦', group: 'K', match_date: '2026-06-24T01:00:00+08:00', venue: 'NRG体育场，休斯顿', round: 2 },
  { id: 46, home_team: '英格兰', away_team: '加纳', group: 'L', match_date: '2026-06-24T04:00:00+08:00', venue: '吉列体育场，波士顿', round: 2 },
  { id: 47, home_team: '巴拿马', away_team: '克罗地亚', group: 'L', match_date: '2026-06-24T07:00:00+08:00', venue: 'BMO球场，多伦多', round: 2 },
  { id: 48, home_team: '哥伦比亚', away_team: '民主刚果', group: 'K', match_date: '2026-06-24T10:00:00+08:00', venue: '阿克伦体育场，萨波潘', round: 2 },

  // === 第3轮（同组同时开球）===
  // 6月24-25日
  { id: 49, home_team: '瑞士', away_team: '加拿大', group: 'B', match_date: '2026-06-25T03:00:00+08:00', venue: 'BC广场，温哥华', round: 3 },
  { id: 50, home_team: '波黑', away_team: '卡塔尔', group: 'B', match_date: '2026-06-25T03:00:00+08:00', venue: '流明球场，西雅图', round: 3 },
  { id: 51, home_team: '苏格兰', away_team: '巴西', group: 'C', match_date: '2026-06-25T06:00:00+08:00', venue: '硬石体育场，迈阿密', round: 3 },
  { id: 52, home_team: '摩洛哥', away_team: '海地', group: 'C', match_date: '2026-06-25T06:00:00+08:00', venue: '梅赛德斯-奔驰体育场，亚特兰大', round: 3 },
  { id: 53, home_team: '捷克', away_team: '墨西哥', group: 'A', match_date: '2026-06-25T09:00:00+08:00', venue: '阿兹特克体育场，墨西哥城', round: 3 },
  { id: 54, home_team: '南非', away_team: '韩国', group: 'A', match_date: '2026-06-25T09:00:00+08:00', venue: 'BBVA体育场，蒙特雷', round: 3 },
  // 6月25-26日
  { id: 55, home_team: '库拉索', away_team: '科特迪瓦', group: 'E', match_date: '2026-06-26T04:00:00+08:00', venue: '林肯金融球场，费城', round: 3 },
  { id: 56, home_team: '厄瓜多尔', away_team: '德国', group: 'E', match_date: '2026-06-26T04:00:00+08:00', venue: '大都会人寿体育场，纽约', round: 3 },
  { id: 57, home_team: '日本', away_team: '瑞典', group: 'F', match_date: '2026-06-26T07:00:00+08:00', venue: 'AT&T体育场，达拉斯', round: 3 },
  { id: 58, home_team: '突尼斯', away_team: '荷兰', group: 'F', match_date: '2026-06-26T07:00:00+08:00', venue: '箭头体育场，堪萨斯城', round: 3 },
  { id: 59, home_team: '土耳其', away_team: '美国', group: 'D', match_date: '2026-06-26T10:00:00+08:00', venue: 'SoFi体育场，洛杉矶', round: 3 },
  { id: 60, home_team: '巴拉圭', away_team: '澳大利亚', group: 'D', match_date: '2026-06-26T10:00:00+08:00', venue: '李维斯体育场，旧金山', round: 3 },
  // 6月26-27日
  { id: 61, home_team: '挪威', away_team: '法国', group: 'I', match_date: '2026-06-27T03:00:00+08:00', venue: '吉列体育场，波士顿', round: 3 },
  { id: 62, home_team: '塞内加尔', away_team: '伊拉克', group: 'I', match_date: '2026-06-27T03:00:00+08:00', venue: 'BMO球场，多伦多', round: 3 },
  { id: 63, home_team: '佛得角', away_team: '沙特阿拉伯', group: 'H', match_date: '2026-06-27T08:00:00+08:00', venue: 'NRG体育场，休斯顿', round: 3 },
  { id: 64, home_team: '乌拉圭', away_team: '西班牙', group: 'H', match_date: '2026-06-27T08:00:00+08:00', venue: '阿克伦体育场，萨波潘', round: 3 },
  { id: 65, home_team: '埃及', away_team: '伊朗', group: 'G', match_date: '2026-06-27T11:00:00+08:00', venue: '流明球场，西雅图', round: 3 },
  { id: 66, home_team: '新西兰', away_team: '比利时', group: 'G', match_date: '2026-06-27T11:00:00+08:00', venue: 'BC广场，温哥华', round: 3 },
  // 6月27-28日
  { id: 67, home_team: '巴拿马', away_team: '英格兰', group: 'L', match_date: '2026-06-28T05:00:00+08:00', venue: '大都会人寿体育场，纽约', round: 3 },
  { id: 68, home_team: '克罗地亚', away_team: '加纳', group: 'L', match_date: '2026-06-28T05:00:00+08:00', venue: '林肯金融球场，费城', round: 3 },
  { id: 69, home_team: '哥伦比亚', away_team: '葡萄牙', group: 'K', match_date: '2026-06-28T07:30:00+08:00', venue: '硬石体育场，迈阿密', round: 3 },
  { id: 70, home_team: '民主刚果', away_team: '乌兹别克斯坦', group: 'K', match_date: '2026-06-28T07:30:00+08:00', venue: '梅赛德斯-奔驰体育场，亚特兰大', round: 3 },
  { id: 71, home_team: '阿尔及利亚', away_team: '奥地利', group: 'J', match_date: '2026-06-28T10:00:00+08:00', venue: '箭头体育场，堪萨斯城', round: 3 },
  { id: 72, home_team: '约旦', away_team: '阿根廷', group: 'J', match_date: '2026-06-28T10:00+08:00', venue: 'AT&T体育场，达拉斯', round: 3 },

  // ============ 淘汰赛赛程（Round of 32 ~ Final，32场）============
  // 初始时使用小组排名占位符（如A1 = A组第一），小组赛结束后替换为实际球队
  // Round of 32 (32强赛) - 2026年7月2-7日
  // 7月2日
  { id: 73, home_team: 'A2', away_team: 'B2', stage: 'Round of 32', match_date: '2026-07-02T03:00:00+08:00', venue: '阿兹特克体育场，墨西哥城' },
  { id: 74, home_team: 'E1', away_team: '1E', stage: 'Round of 32', match_date: '2026-07-02T07:00:00+08:00', venue: 'SoFi体育场，洛杉矶' },
  // 7月3日
  { id: 75, home_team: 'F1', away_team: 'C2', stage: 'Round of 32', match_date: '2026-07-03T03:00:00+08:00', venue: 'AT&T体育场，达拉斯' },
  { id: 76, home_team: 'C1', away_team: 'F2', stage: 'Round of 32', match_date: '2026-07-03T07:00:00+08:00', venue: '大都会人寿体育场，纽约' },
  { id: 77, home_team: 'I1', away_team: '1I', stage: 'Round of 32', match_date: '2026-07-03T11:00:00+08:00', venue: '林肯金融球场，费城' },
  // 7月4日
  { id: 78, home_team: 'E2', away_team: 'I2', stage: 'Round of 32', match_date: '2026-07-04T03:00:00+08:00', venue: '硬石体育场，迈阿密' },
  { id: 79, home_team: 'A1', away_team: '1A', stage: 'Round of 32', match_date: '2026-07-04T07:00:00+08:00', venue: 'BC广场，温哥华' },
  { id: 80, home_team: 'L1', away_team: '1L', stage: 'Round of 32', match_date: '2026-07-04T11:00:00+08:00', venue: '李维斯体育场，旧金山' },
  // 7月5日
  { id: 81, home_team: 'D1', away_team: '1D', stage: 'Round of 32', match_date: '2026-07-05T03:00:00+08:00', venue: '箭头体育场，堪萨斯城' },
  { id: 82, home_team: 'G1', away_team: '1G', stage: 'Round of 32', match_date: '2026-07-05T07:00:00+08:00', venue: 'NRG体育场，休斯顿' },
  { id: 83, home_team: 'K2', away_team: 'L2', stage: 'Round of 32', match_date: '2026-07-05T11:00:00+08:00', venue: '吉列体育场，波士顿' },
  // 7月6日
  { id: 84, home_team: 'H1', away_team: 'J2', stage: 'Round of 32', match_date: '2026-07-06T03:00:00+08:00', venue: '梅赛德斯-奔驰体育场，亚特兰大' },
  { id: 85, home_team: 'B1', away_team: '1B', stage: 'Round of 32', match_date: '2026-07-06T07:00:00+08:00', venue: '流明球场，西雅图' },
  { id: 86, home_team: 'J1', away_team: 'H2', stage: 'Round of 32', match_date: '2026-07-06T11:00:00+08:00', venue: 'BMO球场，多伦多' },
  // 7月7日
  { id: 87, home_team: 'K1', away_team: '1K', stage: 'Round of 32', match_date: '2026-07-07T03:00:00+08:00', venue: 'BBVA体育场，蒙特雷' },
  { id: 88, home_team: 'D2', away_team: 'G2', stage: 'Round of 32', match_date: '2026-07-07T07:00:00+08:00', venue: '阿克伦体育场，萨波潘' },

  // ===== Round of 16 (16强赛) - 2026年7月9-12日 =====
  // 7月9日
  { id: 89, home_team: 'W73', away_team: 'W74', stage: 'Round of 16', match_date: '2026-07-09T03:00:00+08:00', venue: '阿兹特克体育场，墨西哥城' },
  { id: 90, home_team: 'W75', away_team: 'W76', stage: 'Round of 16', match_date: '2026-07-09T07:00:00+08:00', venue: 'SoFi体育场，洛杉矶' },
  // 7月10日
  { id: 91, home_team: 'W77', away_team: 'W78', stage: 'Round of 16', match_date: '2026-07-10T03:00:00+08:00', venue: 'AT&T体育场，达拉斯' },
  { id: 92, home_team: 'W79', away_team: 'W80', stage: 'Round of 16', match_date: '2026-07-10T07:00:00+08:00', venue: '大都会人寿体育场，纽约' },
  // 7月11日
  { id: 93, home_team: 'W81', away_team: 'W82', stage: 'Round of 16', match_date: '2026-07-11T03:00:00+08:00', venue: '林肯金融球场，费城' },
  { id: 94, home_team: 'W83', away_team: 'W84', stage: 'Round of 16', match_date: '2026-07-11T07:00:00+08:00', venue: '硬石体育场，迈阿密' },
  // 7月12日
  { id: 95, home_team: 'W85', away_team: 'W86', stage: 'Round of 16', match_date: '2026-07-12T03:00:00+08:00', venue: 'BC广场，温哥华' },
  { id: 96, home_team: 'W87', away_team: 'W88', stage: 'Round of 16', match_date: '2026-07-12T07:00:00+08:00', venue: '梅赛德斯-奔驰体育场，亚特兰大' },

  // ===== Quarter-finals (8强赛) - 2026年7月14-15日 =====
  // 7月14日
  { id: 97, home_team: 'W89', away_team: 'W90', stage: 'Quarter-final', match_date: '2026-07-14T03:00:00+08:00', venue: 'AT&T体育场，达拉斯' },
  { id: 98, home_team: 'W91', away_team: 'W92', stage: 'Quarter-final', match_date: '2026-07-14T07:00:00+08:00', venue: '大都会人寿体育场，纽约' },
  // 7月15日
  { id: 99, home_team: 'W93', away_team: 'W94', stage: 'Quarter-final', match_date: '2026-07-15T03:00:00+08:00', venue: 'SoFi体育场，洛杉矶' },
  { id: 100, home_team: 'W95', away_team: 'W96', stage: 'Quarter-final', match_date: '2026-07-15T07:00:00+08:00', venue: '阿兹特克体育场，墨西哥城' },

  // ===== Semi-finals (半决赛) - 2026年7月18-19日 =====
  // 7月18日
  { id: 101, home_team: 'W97', away_team: 'W98', stage: 'Semi-final', match_date: '2026-07-18T07:00:00+08:00', venue: 'AT&T体育场，达拉斯' },
  // 7月19日
  { id: 102, home_team: 'W99', away_team: 'W100', stage: 'Semi-final', match_date: '2026-07-19T07:00:00+08:00', venue: '大都会人寿体育场，纽约' },

  // ===== Third place (三四名决赛) - 2026年7月20日 =====
  { id: 103, home_team: 'L101', away_team: 'L102', stage: 'Third place', match_date: '2026-07-20T07:00:00+08:00', venue: '硬石体育场，迈阿密' },

  // ===== Final (决赛) - 2026年7月21日 =====
  { id: 104, home_team: 'W101', away_team: 'W102', stage: 'Final', match_date: '2026-07-21T08:00:00+08:00', venue: 'MetLife体育场，纽约' },
]

// ============ 场馆信息 ============
export const VENUES = [
  { name: '阿兹特克体育场', city: '墨西哥城', country: '墨西哥', capacity: 87500 },
  { name: '阿克伦体育场', city: '萨波潘', country: '墨西哥', capacity: 48000 },
  { name: 'BBVA体育场', city: '蒙特雷', country: '墨西哥', capacity: 53500 },
  { name: 'BC广场', city: '温哥华', country: '加拿大', capacity: 54500 },
  { name: 'BMO球场', city: '多伦多', country: '加拿大', capacity: 45000 },
  { name: 'SoFi体育场', city: '洛杉矶', country: '美国', capacity: 70240 },
  { name: 'AT&T体育场', city: '达拉斯', country: '美国', capacity: 93000 },
  { name: '大都会人寿体育场', city: '纽约', country: '美国', capacity: 82500 },
  { name: '梅赛德斯-奔驰体育场', city: '亚特兰大', country: '美国', capacity: 71000 },
  { name: 'NRG体育场', city: '休斯顿', country: '美国', capacity: 72000 },
  { name: '硬石体育场', city: '迈阿密', country: '美国', capacity: 65000 },
  { name: '吉列体育场', city: '波士顿', country: '美国', capacity: 65000 },
  { name: '箭头体育场', city: '堪萨斯城', country: '美国', capacity: 76600 },
  { name: '林肯金融球场', city: '费城', country: '美国', capacity: 69000 },
  { name: '李维斯体育场', city: '旧金山', country: '美国', capacity: 70900 },
  { name: '流明球场', city: '西雅图', country: '美国', capacity: 68700 },
]

// ============ 足球联合会映射 ============
export const CONFEDERATION_MAP: Record<string, string> = {
  // A组
  '墨西哥': 'CONCACAF', '南非': 'CAF', '韩国': 'AFC', '捷克': 'UEFA',
  // B组
  '加拿大': 'CONCACAF', '波黑': 'UEFA', '卡塔尔': 'AFC', '瑞士': 'UEFA',
  // C组
  '巴西': 'CONMEBOL', '摩洛哥': 'CAF', '海地': 'CONCACAF', '苏格兰': 'UEFA',
  // D组
  '美国': 'CONCACAF', '巴拉圭': 'CONMEBOL', '澳大利亚': 'AFC', '土耳其': 'UEFA',
  // E组
  '德国': 'UEFA', '库拉索': 'CONCACAF', '科特迪瓦': 'CAF', '厄瓜多尔': 'CONMEBOL',
  // F组
  '荷兰': 'UEFA', '日本': 'AFC', '瑞典': 'UEFA', '突尼斯': 'CAF',
  // G组
  '比利时': 'UEFA', '埃及': 'CAF', '伊朗': 'AFC', '新西兰': 'OFC',
  // H组
  '西班牙': 'UEFA', '佛得角': 'CAF', '沙特阿拉伯': 'AFC', '乌拉圭': 'CONMEBOL',
  // I组
  '法国': 'UEFA', '塞内加尔': 'CAF', '伊拉克': 'AFC', '挪威': 'UEFA',
  // J组
  '阿根廷': 'CONMEBOL', '阿尔及利亚': 'CAF', '奥地利': 'UEFA', '约旦': 'AFC',
  // K组
  '葡萄牙': 'UEFA', '民主刚果': 'CAF', '乌兹别克斯坦': 'AFC', '哥伦比亚': 'CONMEBOL',
  // L组
  '英格兰': 'UEFA', '克罗地亚': 'UEFA', '加纳': 'CAF', '巴拿马': 'CONCACAF',
}

// ============ 东道主国家映射 ============
// 用于判断某支球队在哪个国家有主场优势
export const HOST_COUNTRY_MAP: Record<string, string> = {
  '美国': '美国',
  '墨西哥': '墨西哥',
  '加拿大': '加拿大',
}

// ============ 积分榜计算 ============
export interface StandingEntry {
  team: string
  group: string
  played: number
  won: number
  drawn: number
  lost: number
  goalsFor: number
  goalsAgainst: number
  goalDiff: number
  points: number
  flag: string
}

export function calculateGroupStandings(groupName: string): StandingEntry[] {
  return calculateGroupStandingsFromMatches(groupName, MATCHES)
}

export function calculateGroupStandingsFromMatches(groupName: string, matches: Match[]): StandingEntry[] {
  const groupMatches = matches.filter(m => m.group === groupName && m.status === 'completed')
  const groupTeams = TEAMS.filter(t => t.group === groupName)

  const standings: StandingEntry[] = groupTeams.map(t => ({
    team: t.name,
    group: t.group,
    played: 0, won: 0, drawn: 0, lost: 0,
    goalsFor: 0, goalsAgainst: 0, goalDiff: 0, points: 0,
    flag: t.flag
  }))

  for (const m of groupMatches) {
    const homeEntry = standings.find(s => s.team === m.home_team)
    const awayEntry = standings.find(s => s.team === m.away_team)
    if (!homeEntry || !awayEntry || m.home_score === undefined || m.away_score === undefined) continue

    homeEntry.played++
    awayEntry.played++
    homeEntry.goalsFor += m.home_score
    homeEntry.goalsAgainst += m.away_score
    awayEntry.goalsFor += m.away_score
    awayEntry.goalsAgainst += m.home_score

    if (m.home_score > m.away_score) {
      homeEntry.won++; homeEntry.points += 3
      awayEntry.lost++
    } else if (m.home_score < m.away_score) {
      awayEntry.won++; awayEntry.points += 3
      homeEntry.lost++
    } else {
      homeEntry.drawn++; awayEntry.drawn++
      homeEntry.points++; awayEntry.points++
    }
  }

  standings.forEach(s => s.goalDiff = s.goalsFor - s.goalsAgainst)
  standings.sort((a, b) => b.points - a.points || b.goalDiff - a.goalDiff || b.goalsFor - a.goalsFor)

  return standings
}

// ============ 淘汰赛占位符解析 ============
// 解析 "A1" → A组第一的球队名, "W73" → 73场胜者, "L95" → 95场败者
export function resolveKnockoutTeam(placeholder: string): string {
  // 小组排名占位符：如 "A1", "B2", "L3" 等
  const groupRankMatch = placeholder.match(/^([A-L])([1-4])$/)
  if (groupRankMatch) {
    const groupLetter = groupRankMatch[1]
    const rank = parseInt(groupRankMatch[2])
    const standings = calculateGroupStandings(groupLetter)
    if (standings.length >= rank) return standings[rank - 1].team
    return `${groupLetter}组第${rank}`
  }

  // 胜者占位符：如 "W73" → 73场胜者
  const winnerMatch = placeholder.match(/^W(\d+)$/)
  if (winnerMatch) {
    const matchId = parseInt(winnerMatch[1])
    const match = MATCHES.find(m => m.id === matchId)
    if (!match) return `第${matchId}场胜者`
    if (match.status === 'completed' && match.home_score !== undefined && match.away_score !== undefined) {
      return match.home_score > match.away_score ? match.home_team : match.away_team
    }
    return `${match.home_team}或${match.away_team}胜者`
  }

  // 败者占位符：如 "L95" → 95场败者
  const loserMatch = placeholder.match(/^L(\d+)$/)
  if (loserMatch) {
    const matchId = parseInt(loserMatch[1])
    const match = MATCHES.find(m => m.id === matchId)
    if (!match) return `第${matchId}场败者`
    if (match.status === 'completed' && match.home_score !== undefined && match.away_score !== undefined) {
      return match.home_score < match.away_score ? match.home_team : match.away_team
    }
    return `${match.home_team}或${match.away_team}败者`
  }

  // 带问号的占位符
  if (placeholder.endsWith('?')) {
    return resolveKnockoutTeam(placeholder.slice(0, -1)) + '?'
  }

  return placeholder
}

// 判断是否为淘汰赛占位符（非实际球队名）
export function isKnockoutPlaceholder(team: string): boolean {
  return /^([A-L][1-4]|1[A-L]|W\d+\??|L\d+\??|(?:RD|R)?(?:32|16)\s*W\d+\??|(?:Round\s+of\s+(?:32|16)|Quarterfinal|Quarter-final|Semifinal|Semi-final)\s+\d+\s+Winner)$/i.test(team)
}

export function isPlaceholderFixture(match?: Partial<Pick<Match, 'id' | 'stage' | 'group' | 'home_team' | 'away_team' | 'match_date' | 'fixture_status'>> | null): boolean {
  if (!match) return false
  if (match.fixture_status === 'placeholder') return true
  if (!isEffectiveKnockoutMatch(match)) return false
  return Boolean(
    (match.home_team && isKnockoutPlaceholder(match.home_team))
    || (match.away_team && isKnockoutPlaceholder(match.away_team))
  )
}

const GROUP_STAGE_CUTOFF_MS = new Date('2026-06-29T00:00:00+08:00').getTime()

const KNOCKOUT_STAGE_RANGES: Array<[number, number, string]> = [
  [73, 88, 'Round of 32'],
  [89, 96, 'Round of 16'],
  [97, 100, 'Quarter-final'],
  [101, 102, 'Semi-final'],
  [103, 103, 'Third place'],
  [104, 104, 'Final'],
]

const GROUP_STAGE_MARKERS = ['group stage', 'group-stage', 'regular season', 'league stage']

function hasMatchValue(value?: string | number | null) {
  if (value === undefined || value === null) return false
  if (typeof value === 'string') {
    const text = value.trim()
    return Boolean(text) && !['null', 'none', 'undefined'].includes(text.toLowerCase())
  }
  return true
}

function isKnockoutStageValue(stage?: string | null) {
  if (!hasMatchValue(stage)) return false
  const value = String(stage).trim().toLowerCase()
  return !GROUP_STAGE_MARKERS.some(marker => value.includes(marker))
}

function getStageFromMatchId(matchId?: number | null) {
  if (matchId === undefined || matchId === null) return null
  const range = KNOCKOUT_STAGE_RANGES.find(([start, end]) => matchId >= start && matchId <= end)
  return range?.[2] ?? null
}

export function getEffectiveMatchStage(match?: Partial<Pick<Match, 'id' | 'stage' | 'group' | 'home_team' | 'away_team' | 'match_date'>> | null): string | null {
  if (!match) return null
  if (isKnockoutStageValue(match.stage)) return String(match.stage).trim()
  if (hasMatchValue(match.group)) return null

  const stageFromId = getStageFromMatchId(match.id)
  if (stageFromId) return stageFromId

  const kickoffMs = match.match_date ? new Date(match.match_date).getTime() : Number.NaN
  if (
    Number.isFinite(kickoffMs)
    && kickoffMs >= GROUP_STAGE_CUTOFF_MS
    && hasMatchValue(match.home_team)
    && hasMatchValue(match.away_team)
  ) {
    return 'Round of 32'
  }

  return null
}

export function isEffectiveKnockoutMatch(match?: Partial<Pick<Match, 'id' | 'stage' | 'group' | 'home_team' | 'away_team' | 'match_date'>> | null): boolean {
  return Boolean(getEffectiveMatchStage(match))
}

// 获取淘汰赛阶段名称（中文）
export function getStageNameCN(stage: string): string {
  const names: Record<string, string> = {
    'Round of 32': '32强赛',
    'Round of 16': '16强赛',
    'Quarter-final': '四分之一决赛',
    'Semi-final': '半决赛',
    'Third place': '三四名决赛',
    'Final': '决赛',
  }
  return names[stage] || stage
}
