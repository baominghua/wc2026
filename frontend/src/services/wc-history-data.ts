// 世界杯历史数据统计 - 覆盖1994-2022年八届世界杯
// 数据来源: FIFA官方统计 + 公开数据整理

export interface TournamentStats {
  year: number
  host: string
  hostCode: string
  champion: string
  championCode: string
  runnerUp: string
  runnerUpCode: string
  thirdPlace: string
  thirdPlaceCode: string
  topScorer: string
  topScorerGoals: number
  topAssists: string
  topAssistCount: number
  totalGoals: number
  totalMatches: number
  totalTeams: number
  avgGoalsPerMatch: number
}

export interface PlayerHistoricalStats {
  name: string
  flagCode: string
  country: string
  position: string
  tournaments: number[]  // 参加的年份
  goals: number
  assists: number
  appearances: number
  yellowCards: number
  redCards: number
  minutesPlayed: number
  // 按年份的详细数据
  yearlyStats: {
    [year: number]: {
      goals: number
      assists: number
      appearances: number
      yellowCards: number
      redCards: number
    }
  }
}

export interface TeamHistoricalStats {
  name: string
  flagCode: string
  tournaments: number[]  // 参加的年份
  titles: number
  finals: number
  semiFinals: number
  quarterFinals: number
  totalWins: number
  totalDraws: number
  totalLosses: number
  totalGoalsFor: number
  totalGoalsAgainst: number
  biggestWin: string
  biggestLoss: string
  yearlyStats: {
    [year: number]: {
      position: string
      played: number
      won: number
      drawn: number
      lost: number
      goalsFor: number
      goalsAgainst: number
      finalRank: number
    }
  }
}

// ============ 赛事概况 ============
export const TOURNAMENTS: TournamentStats[] = [
  {
    year: 2022,
    host: '卡塔尔',
    hostCode: 'qa',
    champion: '阿根廷',
    championCode: 'ar',
    runnerUp: '法国',
    runnerUpCode: 'fr',
    thirdPlace: '克罗地亚',
    thirdPlaceCode: 'hr',
    topScorer: '姆巴佩',
    topScorerGoals: 8,
    topAssists: '格列兹曼',
    topAssistCount: 3,
    totalGoals: 172,
    totalMatches: 64,
    totalTeams: 32,
    avgGoalsPerMatch: 2.69,
  },
  {
    year: 2018,
    host: '俄罗斯',
    hostCode: 'ru',
    champion: '法国',
    championCode: 'fr',
    runnerUp: '克罗地亚',
    runnerUpCode: 'hr',
    thirdPlace: '比利时',
    thirdPlaceCode: 'be',
    topScorer: '凯恩',
    topScorerGoals: 6,
    topAssists: '哈扎尔/库蒂尼奥等',
    topAssistCount: 2,
    totalGoals: 169,
    totalMatches: 64,
    totalTeams: 32,
    avgGoalsPerMatch: 2.64,
  },
  {
    year: 2014,
    host: '巴西',
    hostCode: 'br',
    champion: '德国',
    championCode: 'de',
    runnerUp: '阿根廷',
    runnerUpCode: 'ar',
    thirdPlace: '荷兰',
    thirdPlaceCode: 'nl',
    topScorer: 'J·罗德里格斯',
    topScorerGoals: 6,
    topAssists: '托尼·克罗斯',
    topAssistCount: 3,
    totalGoals: 171,
    totalMatches: 64,
    totalTeams: 32,
    avgGoalsPerMatch: 2.67,
  },
  {
    year: 2010,
    host: '南非',
    hostCode: 'za',
    champion: '西班牙',
    championCode: 'es',
    runnerUp: '荷兰',
    runnerUpCode: 'nl',
    thirdPlace: '德国',
    thirdPlaceCode: 'de',
    topScorer: '穆勒/斯内德/大卫·比利亚/弗兰',
    topScorerGoals: 5,
    topAssists: '穆勒',
    topAssistCount: 3,
    totalGoals: 145,
    totalMatches: 64,
    totalTeams: 32,
    avgGoalsPerMatch: 2.27,
  },
  {
    year: 2006,
    host: '德国',
    hostCode: 'de',
    champion: '意大利',
    championCode: 'it',
    runnerUp: '法国',
    runnerUpCode: 'fr',
    thirdPlace: '德国',
    thirdPlaceCode: 'de',
    topScorer: '克洛泽',
    topScorerGoals: 5,
    topAssists: '里克尔梅 / 托蒂等',
    topAssistCount: 4,
    totalGoals: 147,
    totalMatches: 64,
    totalTeams: 32,
    avgGoalsPerMatch: 2.30,
  },
  {
    year: 2002,
    host: '韩日',
    hostCode: 'kr',
    champion: '巴西',
    championCode: 'br',
    runnerUp: '德国',
    runnerUpCode: 'de',
    thirdPlace: '土耳其',
    thirdPlaceCode: 'tr',
    topScorer: '罗纳尔多',
    topScorerGoals: 8,
    topAssists: '里瓦尔多 / 罗纳尔迪尼奥等',
    topAssistCount: 3,
    totalGoals: 161,
    totalMatches: 64,
    totalTeams: 32,
    avgGoalsPerMatch: 2.52,
  },
  {
    year: 1998,
    host: '法国',
    hostCode: 'fr',
    champion: '法国',
    championCode: 'fr',
    runnerUp: '巴西',
    runnerUpCode: 'br',
    thirdPlace: '克罗地亚',
    thirdPlaceCode: 'hr',
    topScorer: '达沃·苏克',
    topScorerGoals: 6,
    topAssists: '多名球员并列',
    topAssistCount: 3,
    totalGoals: 171,
    totalMatches: 64,
    totalTeams: 32,
    avgGoalsPerMatch: 2.67,
  },
  {
    year: 1994,
    host: '美国',
    hostCode: 'us',
    champion: '巴西',
    championCode: 'br',
    runnerUp: '意大利',
    runnerUpCode: 'it',
    thirdPlace: '瑞典',
    thirdPlaceCode: 'se',
    topScorer: '斯托伊奇科夫 / 萨连科',
    topScorerGoals: 6,
    topAssists: '多名球员并列',
    topAssistCount: 3,
    totalGoals: 141,
    totalMatches: 52,
    totalTeams: 24,
    avgGoalsPerMatch: 2.71,
  },
]

// ============ 球员历史数据 ============
export const PLAYER_STATS: PlayerHistoricalStats[] = [
  {
    name: '梅西',
    flagCode: 'ar',
    country: '阿根廷',
    position: '前锋',
    tournaments: [2010, 2014, 2018, 2022],
    goals: 13,
    assists: 8,
    appearances: 26,
    yellowCards: 3,
    redCards: 0,
    minutesPlayed: 2214,
    yearlyStats: {
      2010: { goals: 0, assists: 1, appearances: 5, yellowCards: 0, redCards: 0 },
      2014: { goals: 4, assists: 1, appearances: 7, yellowCards: 1, redCards: 0 },
      2018: { goals: 1, assists: 2, appearances: 4, yellowCards: 1, redCards: 0 },
      2022: { goals: 8, assists: 4, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '姆巴佩',
    flagCode: 'fr',
    country: '法国',
    position: '前锋',
    tournaments: [2018, 2022],
    goals: 12,
    assists: 3,
    appearances: 14,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 1145,
    yearlyStats: {
      2018: { goals: 4, assists: 1, appearances: 7, yellowCards: 1, redCards: 0 },
      2022: { goals: 8, assists: 2, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '托马斯·穆勒',
    flagCode: 'de',
    country: '德国',
    position: '中场',
    tournaments: [2010, 2014, 2018, 2022],
    goals: 10,
    assists: 6,
    appearances: 16,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 1323,
    yearlyStats: {
      2010: { goals: 5, assists: 3, appearances: 6, yellowCards: 0, redCards: 0 },
      2014: { goals: 5, assists: 3, appearances: 7, yellowCards: 1, redCards: 0 },
      2018: { goals: 0, assists: 0, appearances: 3, yellowCards: 0, redCards: 0 },
      2022: { goals: 0, assists: 0, appearances: 0, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '大卫·比利亚',
    flagCode: 'es',
    country: '西班牙',
    position: '前锋',
    tournaments: [2010, 2014],
    goals: 9,
    assists: 3,
    appearances: 12,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 967,
    yearlyStats: {
      2010: { goals: 5, assists: 1, appearances: 7, yellowCards: 1, redCards: 0 },
      2014: { goals: 4, assists: 2, appearances: 5, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '哈里·凯恩',
    flagCode: 'gb-eng',
    country: '英格兰',
    position: '前锋',
    tournaments: [2018, 2022],
    goals: 8,
    assists: 3,
    appearances: 12,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 1014,
    yearlyStats: {
      2018: { goals: 6, assists: 0, appearances: 6, yellowCards: 1, redCards: 0 },
      2022: { goals: 2, assists: 3, appearances: 6, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: 'J·罗德里格斯',
    flagCode: 'co',
    country: '哥伦比亚',
    position: '中场',
    tournaments: [2014, 2018],
    goals: 6,
    assists: 4,
    appearances: 10,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 810,
    yearlyStats: {
      2014: { goals: 6, assists: 2, appearances: 5, yellowCards: 1, redCards: 0 },
      2018: { goals: 0, assists: 2, appearances: 5, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '内马尔',
    flagCode: 'br',
    country: '巴西',
    position: '前锋',
    tournaments: [2014, 2018, 2022],
    goals: 6,
    assists: 3,
    appearances: 14,
    yellowCards: 3,
    redCards: 0,
    minutesPlayed: 1063,
    yearlyStats: {
      2014: { goals: 4, assists: 1, appearances: 5, yellowCards: 1, redCards: 0 },
      2018: { goals: 2, assists: 1, appearances: 5, yellowCards: 1, redCards: 0 },
      2022: { goals: 0, assists: 1, appearances: 4, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '莫德里奇',
    flagCode: 'hr',
    country: '克罗地亚',
    position: '中场',
    tournaments: [2014, 2018, 2022],
    goals: 3,
    assists: 5,
    appearances: 18,
    yellowCards: 3,
    redCards: 0,
    minutesPlayed: 1562,
    yearlyStats: {
      2014: { goals: 1, assists: 0, appearances: 3, yellowCards: 1, redCards: 0 },
      2018: { goals: 2, assists: 3, appearances: 7, yellowCards: 1, redCards: 0 },
      2022: { goals: 0, assists: 2, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '克洛泽',
    flagCode: 'de',
    country: '德国',
    position: '前锋',
    tournaments: [2002, 2006, 2010, 2014],
    goals: 16,
    assists: 2,
    appearances: 24,
    yellowCards: 1,
    redCards: 0,
    minutesPlayed: 1374,
    yearlyStats: {
      2002: { goals: 5, assists: 0, appearances: 7, yellowCards: 0, redCards: 0 },
      2006: { goals: 5, assists: 0, appearances: 7, yellowCards: 0, redCards: 0 },
      2010: { goals: 4, assists: 0, appearances: 5, yellowCards: 0, redCards: 0 },
      2014: { goals: 1, assists: 2, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '苏亚雷斯',
    flagCode: 'uy',
    country: '乌拉圭',
    position: '前锋',
    tournaments: [2010, 2014, 2018, 2022],
    goals: 7,
    assists: 4,
    appearances: 16,
    yellowCards: 4,
    redCards: 0,
    minutesPlayed: 1290,
    yearlyStats: {
      2010: { goals: 3, assists: 1, appearances: 6, yellowCards: 1, redCards: 0 },
      2014: { goals: 2, assists: 2, appearances: 5, yellowCards: 1, redCards: 0 },
      2018: { goals: 1, assists: 1, appearances: 5, yellowCards: 1, redCards: 0 },
      2022: { goals: 1, assists: 0, appearances: 0, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '格列兹曼',
    flagCode: 'fr',
    country: '法国',
    position: '前锋',
    tournaments: [2018, 2022],
    goals: 5,
    assists: 5,
    appearances: 14,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 1136,
    yearlyStats: {
      2018: { goals: 4, assists: 2, appearances: 7, yellowCards: 1, redCards: 0 },
      2022: { goals: 1, assists: 3, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '伊涅斯塔',
    flagCode: 'es',
    country: '西班牙',
    position: '中场',
    tournaments: [2010, 2014, 2018],
    goals: 2,
    assists: 4,
    appearances: 16,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 1218,
    yearlyStats: {
      2010: { goals: 2, assists: 1, appearances: 7, yellowCards: 1, redCards: 0 },
      2014: { goals: 0, assists: 2, appearances: 5, yellowCards: 1, redCards: 0 },
      2018: { goals: 0, assists: 1, appearances: 4, yellowCards: 0, redCards: 0 },
    }
  },
  {
    name: '罗本',
    flagCode: 'nl',
    country: '荷兰',
    position: '前锋',
    tournaments: [2010, 2014],
    goals: 5,
    assists: 3,
    appearances: 12,
    yellowCards: 1,
    redCards: 0,
    minutesPlayed: 978,
    yearlyStats: {
      2010: { goals: 2, assists: 1, appearances: 7, yellowCards: 0, redCards: 0 },
      2014: { goals: 3, assists: 2, appearances: 5, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '斯内德',
    flagCode: 'nl',
    country: '荷兰',
    position: '中场',
    tournaments: [2010, 2014],
    goals: 5,
    assists: 4,
    appearances: 12,
    yellowCards: 3,
    redCards: 0,
    minutesPlayed: 1021,
    yearlyStats: {
      2010: { goals: 5, assists: 3, appearances: 7, yellowCards: 2, redCards: 0 },
      2014: { goals: 0, assists: 1, appearances: 5, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '弗兰',
    flagCode: 'uy',
    country: '乌拉圭',
    position: '前锋',
    tournaments: [2010],
    goals: 5,
    assists: 2,
    appearances: 7,
    yellowCards: 1,
    redCards: 0,
    minutesPlayed: 630,
    yearlyStats: {
      2010: { goals: 5, assists: 2, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '厄齐尔',
    flagCode: 'de',
    country: '德国',
    position: '中场',
    tournaments: [2010, 2014, 2018],
    goals: 3,
    assists: 7,
    appearances: 19,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 1405,
    yearlyStats: {
      2010: { goals: 1, assists: 3, appearances: 7, yellowCards: 0, redCards: 0 },
      2014: { goals: 1, assists: 3, appearances: 7, yellowCards: 1, redCards: 0 },
      2018: { goals: 1, assists: 1, appearances: 5, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '哈扎尔',
    flagCode: 'be',
    country: '比利时',
    position: '中场',
    tournaments: [2014, 2018],
    goals: 3,
    assists: 4,
    appearances: 12,
    yellowCards: 1,
    redCards: 0,
    minutesPlayed: 992,
    yearlyStats: {
      2014: { goals: 0, assists: 2, appearances: 5, yellowCards: 0, redCards: 0 },
      2018: { goals: 3, assists: 2, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '托尼·克罗斯',
    flagCode: 'de',
    country: '德国',
    position: '中场',
    tournaments: [2010, 2014, 2018, 2022],
    goals: 3,
    assists: 5,
    appearances: 22,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 1736,
    yearlyStats: {
      2010: { goals: 0, assists: 1, appearances: 5, yellowCards: 0, redCards: 0 },
      2014: { goals: 2, assists: 3, appearances: 7, yellowCards: 1, redCards: 0 },
      2018: { goals: 1, assists: 1, appearances: 3, yellowCards: 1, redCards: 0 },
      2022: { goals: 0, assists: 0, appearances: 7, yellowCards: 0, redCards: 0 },
    }
  },
  {
    name: '迪马利亚',
    flagCode: 'ar',
    country: '阿根廷',
    position: '中场',
    tournaments: [2010, 2014, 2018, 2022],
    goals: 3,
    assists: 3,
    appearances: 16,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 926,
    yearlyStats: {
      2010: { goals: 1, assists: 1, appearances: 5, yellowCards: 0, redCards: 0 },
      2014: { goals: 1, assists: 1, appearances: 5, yellowCards: 1, redCards: 0 },
      2018: { goals: 0, assists: 0, appearances: 3, yellowCards: 1, redCards: 0 },
      2022: { goals: 1, assists: 1, appearances: 7, yellowCards: 0, redCards: 0 },
    }
  },
  {
    name: '卡瓦尼',
    flagCode: 'uy',
    country: '乌拉圭',
    position: '前锋',
    tournaments: [2010, 2014, 2018],
    goals: 5,
    assists: 2,
    appearances: 15,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 1038,
    yearlyStats: {
      2010: { goals: 0, assists: 0, appearances: 6, yellowCards: 1, redCards: 0 },
      2014: { goals: 2, assists: 1, appearances: 5, yellowCards: 0, redCards: 0 },
      2018: { goals: 3, assists: 1, appearances: 5, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '库蒂尼奥',
    flagCode: 'br',
    country: '巴西',
    position: '中场',
    tournaments: [2018],
    goals: 2,
    assists: 2,
    appearances: 5,
    yellowCards: 0,
    redCards: 0,
    minutesPlayed: 441,
    yearlyStats: {
      2018: { goals: 2, assists: 2, appearances: 5, yellowCards: 0, redCards: 0 },
    }
  },
  {
    name: '贝林厄姆',
    flagCode: 'gb-eng',
    country: '英格兰',
    position: '中场',
    tournaments: [2022],
    goals: 1,
    assists: 1,
    appearances: 5,
    yellowCards: 1,
    redCards: 0,
    minutesPlayed: 451,
    yearlyStats: {
      2022: { goals: 1, assists: 1, appearances: 5, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '吉鲁',
    flagCode: 'fr',
    country: '法国',
    position: '前锋',
    tournaments: [2018, 2022],
    goals: 3,
    assists: 3,
    appearances: 14,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 892,
    yearlyStats: {
      2018: { goals: 0, assists: 1, appearances: 7, yellowCards: 1, redCards: 0 },
      2022: { goals: 3, assists: 2, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '莱万多夫斯基',
    flagCode: 'pl',
    country: '波兰',
    position: '前锋',
    tournaments: [2018, 2022],
    goals: 2,
    assists: 1,
    appearances: 8,
    yellowCards: 1,
    redCards: 0,
    minutesPlayed: 679,
    yearlyStats: {
      2018: { goals: 0, assists: 0, appearances: 3, yellowCards: 0, redCards: 0 },
      2022: { goals: 2, assists: 1, appearances: 5, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '莫拉塔',
    flagCode: 'es',
    country: '西班牙',
    position: '前锋',
    tournaments: [2018, 2022],
    goals: 3,
    assists: 1,
    appearances: 10,
    yellowCards: 1,
    redCards: 0,
    minutesPlayed: 587,
    yearlyStats: {
      2018: { goals: 1, assists: 0, appearances: 5, yellowCards: 0, redCards: 0 },
      2022: { goals: 2, assists: 1, appearances: 5, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '罗纳尔多',
    flagCode: 'br',
    country: '巴西',
    position: '前锋',
    tournaments: [1998, 2002, 2006],
    goals: 15,
    assists: 4,
    appearances: 19,
    yellowCards: 1,
    redCards: 0,
    minutesPlayed: 1512,
    yearlyStats: {
      1998: { goals: 4, assists: 3, appearances: 7, yellowCards: 0, redCards: 0 },
      2002: { goals: 8, assists: 0, appearances: 7, yellowCards: 0, redCards: 0 },
      2006: { goals: 3, assists: 1, appearances: 5, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '齐达内',
    flagCode: 'fr',
    country: '法国',
    position: '中场',
    tournaments: [1998, 2002, 2006],
    goals: 5,
    assists: 1,
    appearances: 14,
    yellowCards: 4,
    redCards: 2,
    minutesPlayed: 1240,
    yearlyStats: {
      1998: { goals: 2, assists: 0, appearances: 7, yellowCards: 1, redCards: 1 },
      2002: { goals: 0, assists: 0, appearances: 1, yellowCards: 0, redCards: 0 },
      2006: { goals: 3, assists: 1, appearances: 6, yellowCards: 3, redCards: 1 },
    }
  },
  {
    name: '里瓦尔多',
    flagCode: 'br',
    country: '巴西',
    position: '中场',
    tournaments: [1998, 2002],
    goals: 8,
    assists: 4,
    appearances: 14,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 1214,
    yearlyStats: {
      1998: { goals: 3, assists: 2, appearances: 7, yellowCards: 1, redCards: 0 },
      2002: { goals: 5, assists: 2, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '罗纳尔迪尼奥',
    flagCode: 'br',
    country: '巴西',
    position: '中场',
    tournaments: [2002, 2006],
    goals: 2,
    assists: 3,
    appearances: 10,
    yellowCards: 1,
    redCards: 1,
    minutesPlayed: 775,
    yearlyStats: {
      2002: { goals: 2, assists: 2, appearances: 5, yellowCards: 1, redCards: 1 },
      2006: { goals: 0, assists: 1, appearances: 5, yellowCards: 0, redCards: 0 },
    }
  },
  {
    name: '达沃·苏克',
    flagCode: 'hr',
    country: '克罗地亚',
    position: '前锋',
    tournaments: [1998],
    goals: 6,
    assists: 1,
    appearances: 7,
    yellowCards: 1,
    redCards: 0,
    minutesPlayed: 628,
    yearlyStats: {
      1998: { goals: 6, assists: 1, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '罗马里奥',
    flagCode: 'br',
    country: '巴西',
    position: '前锋',
    tournaments: [1994],
    goals: 5,
    assists: 2,
    appearances: 7,
    yellowCards: 1,
    redCards: 0,
    minutesPlayed: 640,
    yearlyStats: {
      1994: { goals: 5, assists: 2, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '巴蒂斯图塔',
    flagCode: 'ar',
    country: '阿根廷',
    position: '前锋',
    tournaments: [1994, 1998, 2002],
    goals: 10,
    assists: 1,
    appearances: 12,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 1046,
    yearlyStats: {
      1994: { goals: 4, assists: 0, appearances: 4, yellowCards: 1, redCards: 0 },
      1998: { goals: 5, assists: 1, appearances: 5, yellowCards: 1, redCards: 0 },
      2002: { goals: 1, assists: 0, appearances: 3, yellowCards: 0, redCards: 0 },
    }
  },
  {
    name: '斯托伊奇科夫',
    flagCode: 'bg',
    country: '保加利亚',
    position: '前锋',
    tournaments: [1994, 1998],
    goals: 6,
    assists: 2,
    appearances: 10,
    yellowCards: 3,
    redCards: 0,
    minutesPlayed: 878,
    yearlyStats: {
      1994: { goals: 6, assists: 2, appearances: 7, yellowCards: 2, redCards: 0 },
      1998: { goals: 0, assists: 0, appearances: 3, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '奥列格·萨连科',
    flagCode: 'ru',
    country: '俄罗斯',
    position: '前锋',
    tournaments: [1994],
    goals: 6,
    assists: 0,
    appearances: 3,
    yellowCards: 0,
    redCards: 0,
    minutesPlayed: 270,
    yearlyStats: {
      1994: { goals: 6, assists: 0, appearances: 3, yellowCards: 0, redCards: 0 },
    }
  },
  {
    name: '贝贝托',
    flagCode: 'br',
    country: '巴西',
    position: '前锋',
    tournaments: [1994, 1998],
    goals: 6,
    assists: 4,
    appearances: 14,
    yellowCards: 1,
    redCards: 0,
    minutesPlayed: 1170,
    yearlyStats: {
      1994: { goals: 3, assists: 3, appearances: 7, yellowCards: 0, redCards: 0 },
      1998: { goals: 3, assists: 1, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '菲戈',
    flagCode: 'pt',
    country: '葡萄牙',
    position: '中场',
    tournaments: [2002, 2006],
    goals: 0,
    assists: 3,
    appearances: 10,
    yellowCards: 2,
    redCards: 0,
    minutesPlayed: 852,
    yearlyStats: {
      2002: { goals: 0, assists: 1, appearances: 3, yellowCards: 1, redCards: 0 },
      2006: { goals: 0, assists: 2, appearances: 7, yellowCards: 1, redCards: 0 },
    }
  },
  {
    name: '托蒂',
    flagCode: 'it',
    country: '意大利',
    position: '前腰',
    tournaments: [2002, 2006],
    goals: 1,
    assists: 4,
    appearances: 11,
    yellowCards: 4,
    redCards: 1,
    minutesPlayed: 824,
    yearlyStats: {
      2002: { goals: 0, assists: 0, appearances: 4, yellowCards: 2, redCards: 1 },
      2006: { goals: 1, assists: 4, appearances: 7, yellowCards: 2, redCards: 0 },
    }
  },
]

// ============ 2026球员实时数据 ============
// 只保留已经产生 2026 赛事事件的球员，避免赛前占位球星混入 2026 统计榜。
export interface LivePlayerEvent2026 {
  matchId: number
  minute: number
  team: string
  scorer: string
  scorerFlagCode: string
  scorerCountry: string
  scorerPosition: string
  assist?: string
  assistFlagCode?: string
  assistCountry?: string
  assistPosition?: string
}

export const LIVE_PLAYER_EVENTS_2026: LivePlayerEvent2026[] = [
  {
    matchId: 1,
    minute: 7,
    team: '墨西哥',
    scorer: '朱利安·奎尼奥内斯',
    scorerFlagCode: 'mx',
    scorerCountry: '墨西哥',
    scorerPosition: '前锋',
  },
  {
    matchId: 1,
    minute: 67,
    team: '墨西哥',
    scorer: '劳尔·希门尼斯',
    scorerFlagCode: 'mx',
    scorerCountry: '墨西哥',
    scorerPosition: '前锋',
  },
  {
    matchId: 2,
    minute: 67,
    team: '韩国',
    scorer: '黄仁范',
    scorerFlagCode: 'kr',
    scorerCountry: '韩国',
    scorerPosition: '中场',
  },
  {
    matchId: 2,
    minute: 80,
    team: '韩国',
    scorer: '吴贤揆',
    scorerFlagCode: 'kr',
    scorerCountry: '韩国',
    scorerPosition: '前锋',
    assist: '黄仁范',
    assistFlagCode: 'kr',
    assistCountry: '韩国',
    assistPosition: '中场',
  },
  {
    matchId: 2,
    minute: 59,
    team: '捷克',
    scorer: '拉迪斯拉夫·克雷伊奇',
    scorerFlagCode: 'cz',
    scorerCountry: '捷克',
    scorerPosition: '后卫',
  },
]

function make2026Player(
  name: string,
  flagCode: string,
  country: string,
  position: string,
  goals: number,
  assists: number,
  appearances = 1,
  yellowCards = 0,
): PlayerHistoricalStats {
  return {
    name,
    flagCode,
    country,
    position,
    tournaments: [2026],
    goals,
    assists,
    appearances,
    yellowCards,
    redCards: 0,
    minutesPlayed: appearances * 90,
    yearlyStats: {
      2026: { goals, assists, appearances, yellowCards, redCards: 0 },
    },
  }
}

function build2026PlayerStats(events: LivePlayerEvent2026[]): PlayerHistoricalStats[] {
  const players = new Map<string, PlayerHistoricalStats>()

  const ensurePlayer = (name: string, flagCode: string, country: string, position: string) => {
    const existing = players.get(name)
    if (existing) return existing
    const player = make2026Player(name, flagCode, country, position, 0, 0)
    players.set(name, player)
    return player
  }

  events.forEach(event => {
    const scorer = ensurePlayer(event.scorer, event.scorerFlagCode, event.scorerCountry, event.scorerPosition)
    scorer.goals += 1
    scorer.yearlyStats[2026].goals += 1

    if (event.assist && event.assistFlagCode && event.assistCountry && event.assistPosition) {
      const assister = ensurePlayer(event.assist, event.assistFlagCode, event.assistCountry, event.assistPosition)
      assister.assists += 1
      assister.yearlyStats[2026].assists += 1
    }
  })

  return Array.from(players.values()).sort((a, b) =>
    b.yearlyStats[2026].goals - a.yearlyStats[2026].goals
    || b.yearlyStats[2026].assists - a.yearlyStats[2026].assists
    || a.name.localeCompare(b.name, 'zh-Hans')
  )
}

export const PLAYER_STATS_2026: PlayerHistoricalStats[] = build2026PlayerStats(LIVE_PLAYER_EVENTS_2026)

export const LIVE_SCORER_BOARD_2026: PlayerHistoricalStats[] = PLAYER_STATS_2026
  .filter(player => (player.yearlyStats[2026]?.goals ?? 0) > 0)
  .sort((a, b) =>
    b.yearlyStats[2026].goals - a.yearlyStats[2026].goals
    || b.yearlyStats[2026].assists - a.yearlyStats[2026].assists
    || a.name.localeCompare(b.name, 'zh-Hans')
  )

export const LIVE_ASSIST_BOARD_2026: PlayerHistoricalStats[] = PLAYER_STATS_2026
  .filter(player => (player.yearlyStats[2026]?.assists ?? 0) > 0)
  .sort((a, b) =>
    b.yearlyStats[2026].assists - a.yearlyStats[2026].assists
    || b.yearlyStats[2026].goals - a.yearlyStats[2026].goals
    || a.name.localeCompare(b.name, 'zh-Hans')
  )

// ============ 球队历史数据 ============
const BASE_TEAM_HISTORICAL_STATS: TeamHistoricalStats[] = [
  {
    name: '巴西',
    flagCode: 'br',
    tournaments: [2010, 2014, 2018, 2022],
    titles: 0,
    finals: 0,
    semiFinals: 2,
    quarterFinals: 3,
    totalWins: 14,
    totalDraws: 4,
    totalLosses: 4,
    totalGoalsFor: 41,
    totalGoalsAgainst: 20,
    biggestWin: '7-1 海地(2014友谊赛) / 4-1 喀麦隆(2014)',
    biggestLoss: '1-7 德国(2014半决赛)',
    yearlyStats: {
      2010: { position: '八强', played: 5, won: 3, drawn: 1, lost: 1, goalsFor: 9, goalsAgainst: 4, finalRank: 6 },
      2014: { position: '四强', played: 7, won: 3, drawn: 2, lost: 2, goalsFor: 11, goalsAgainst: 14, finalRank: 4 },
      2018: { position: '八强', played: 5, won: 3, drawn: 1, lost: 1, goalsFor: 8, goalsAgainst: 3, finalRank: 6 },
      2022: { position: '八强', played: 5, won: 3, drawn: 0, lost: 2, goalsFor: 8, goalsAgainst: 6, finalRank: 7 },
    }
  },
  {
    name: '德国',
    flagCode: 'de',
    tournaments: [2010, 2014, 2018, 2022],
    titles: 1,
    finals: 1,
    semiFinals: 3,
    quarterFinals: 3,
    totalWins: 16,
    totalDraws: 3,
    totalLosses: 5,
    totalGoalsFor: 47,
    totalGoalsAgainst: 27,
    biggestWin: '7-1 巴西(2014半决赛)',
    biggestLoss: '0-2 韩国(2018小组赛)',
    yearlyStats: {
      2010: { position: '四强', played: 7, won: 4, drawn: 1, lost: 2, goalsFor: 16, goalsAgainst: 5, finalRank: 3 },
      2014: { position: '冠军', played: 7, won: 6, drawn: 1, lost: 0, goalsFor: 18, goalsAgainst: 4, finalRank: 1 },
      2018: { position: '小组赛', played: 3, won: 1, drawn: 0, lost: 2, goalsFor: 2, goalsAgainst: 4, finalRank: 22 },
      2022: { position: '小组赛', played: 3, won: 1, drawn: 1, lost: 1, goalsFor: 6, goalsAgainst: 7, finalRank: 17 },
    }
  },
  {
    name: '阿根廷',
    flagCode: 'ar',
    tournaments: [2010, 2014, 2018, 2022],
    titles: 1,
    finals: 2,
    semiFinals: 2,
    quarterFinals: 3,
    totalWins: 16,
    totalDraws: 5,
    totalLosses: 4,
    totalGoalsFor: 40,
    totalGoalsAgainst: 18,
    biggestWin: '4-1 韩国(2010)',
    biggestLoss: '0-3 克罗地亚(2018)',
    yearlyStats: {
      2010: { position: '八强', played: 5, won: 4, drawn: 0, lost: 1, goalsFor: 10, goalsAgainst: 6, finalRank: 5 },
      2014: { position: '亚军', played: 7, won: 5, drawn: 2, lost: 0, goalsFor: 8, goalsAgainst: 4, finalRank: 2 },
      2018: { position: '十六强', played: 4, won: 1, drawn: 1, lost: 2, goalsFor: 3, goalsAgainst: 6, finalRank: 16 },
      2022: { position: '冠军', played: 7, won: 4, drawn: 2, lost: 1, goalsFor: 15, goalsAgainst: 8, finalRank: 1 },
    }
  },
  {
    name: '法国',
    flagCode: 'fr',
    tournaments: [2010, 2014, 2018, 2022],
    titles: 1,
    finals: 2,
    semiFinals: 2,
    quarterFinals: 2,
    totalWins: 16,
    totalDraws: 4,
    totalLosses: 4,
    totalGoalsFor: 45,
    totalGoalsAgainst: 18,
    biggestWin: '4-2 克罗地亚(2018决赛)',
    biggestLoss: '0-2 墨西哥(2010)',
    yearlyStats: {
      2010: { position: '小组赛', played: 3, won: 0, drawn: 1, lost: 2, goalsFor: 1, goalsAgainst: 4, finalRank: 29 },
      2014: { position: '八强', played: 5, won: 3, drawn: 1, lost: 1, goalsFor: 10, goalsAgainst: 5, finalRank: 7 },
      2018: { position: '冠军', played: 7, won: 6, drawn: 1, lost: 0, goalsFor: 14, goalsAgainst: 6, finalRank: 1 },
      2022: { position: '亚军', played: 7, won: 5, drawn: 0, lost: 2, goalsFor: 16, goalsAgainst: 8, finalRank: 2 },
    }
  },
  {
    name: '西班牙',
    flagCode: 'es',
    tournaments: [2010, 2014, 2018, 2022],
    titles: 1,
    finals: 1,
    semiFinals: 1,
    quarterFinals: 1,
    totalWins: 10,
    totalDraws: 5,
    totalLosses: 6,
    totalGoalsFor: 31,
    totalGoalsAgainst: 21,
    biggestWin: '5-1 荷兰(2010决赛回合反)',
    biggestLoss: '1-5 荷兰(2014小组赛)',
    yearlyStats: {
      2010: { position: '冠军', played: 7, won: 6, drawn: 0, lost: 1, goalsFor: 8, goalsAgainst: 2, finalRank: 1 },
      2014: { position: '小组赛', played: 3, won: 1, drawn: 0, lost: 2, goalsFor: 4, goalsAgainst: 7, finalRank: 23 },
      2018: { position: '十六强', played: 4, won: 1, drawn: 3, lost: 0, goalsFor: 7, goalsAgainst: 6, finalRank: 10 },
      2022: { position: '十六强', played: 4, won: 1, drawn: 1, lost: 2, goalsFor: 9, goalsAgainst: 6, finalRank: 13 },
    }
  },
  {
    name: '荷兰',
    flagCode: 'nl',
    tournaments: [2010, 2014],
    titles: 0,
    finals: 1,
    semiFinals: 1,
    quarterFinals: 1,
    totalWins: 9,
    totalDraws: 5,
    totalLosses: 2,
    totalGoalsFor: 31,
    totalGoalsAgainst: 15,
    biggestWin: '5-1 西班牙(2014小组赛)',
    biggestLoss: '0-1 西班牙(2010决赛)',
    yearlyStats: {
      2010: { position: '亚军', played: 7, won: 6, drawn: 0, lost: 1, goalsFor: 12, goalsAgainst: 6, finalRank: 2 },
      2014: { position: '四强', played: 7, won: 3, drawn: 4, lost: 0, goalsFor: 15, goalsAgainst: 4, finalRank: 3 },
    }
  },
  {
    name: '克罗地亚',
    flagCode: 'hr',
    tournaments: [2014, 2018, 2022],
    titles: 0,
    finals: 1,
    semiFinals: 2,
    quarterFinals: 2,
    totalWins: 10,
    totalDraws: 6,
    totalLosses: 4,
    totalGoalsFor: 29,
    totalGoalsAgainst: 20,
    biggestWin: '3-0 阿根廷(2018小组赛)',
    biggestLoss: '2-4 法国(2018决赛)',
    yearlyStats: {
      2014: { position: '小组赛', played: 3, won: 1, drawn: 0, lost: 2, goalsFor: 6, goalsAgainst: 6, finalRank: 19 },
      2018: { position: '亚军', played: 7, won: 4, drawn: 2, lost: 1, goalsFor: 14, goalsAgainst: 9, finalRank: 2 },
      2022: { position: '四强', played: 7, won: 3, drawn: 2, lost: 2, goalsFor: 8, goalsAgainst: 7, finalRank: 3 },
    }
  },
  {
    name: '英格兰',
    flagCode: 'gb-eng',
    tournaments: [2010, 2014, 2018, 2022],
    titles: 0,
    finals: 0,
    semiFinals: 1,
    quarterFinals: 2,
    totalWins: 11,
    totalDraws: 7,
    totalLosses: 5,
    totalGoalsFor: 30,
    totalGoalsAgainst: 19,
    biggestWin: '6-1 巴拿马(2018)',
    biggestLoss: '1-4 德国(2010十六强)',
    yearlyStats: {
      2010: { position: '十六强', played: 4, won: 1, drawn: 2, lost: 1, goalsFor: 3, goalsAgainst: 5, finalRank: 13 },
      2014: { position: '小组赛', played: 3, won: 0, drawn: 2, lost: 1, goalsFor: 2, goalsAgainst: 4, finalRank: 26 },
      2018: { position: '四强', played: 7, won: 3, drawn: 0, lost: 4, goalsFor: 12, goalsAgainst: 8, finalRank: 4 },
      2022: { position: '八强', played: 5, won: 3, drawn: 1, lost: 1, goalsFor: 13, goalsAgainst: 4, finalRank: 5 },
    }
  },
  {
    name: '比利时',
    flagCode: 'be',
    tournaments: [2014, 2018, 2022],
    titles: 0,
    finals: 0,
    semiFinals: 1,
    quarterFinals: 1,
    totalWins: 9,
    totalDraws: 3,
    totalLosses: 5,
    totalGoalsFor: 26,
    totalGoalsAgainst: 16,
    biggestWin: '5-2 突尼斯(2018)',
    biggestLoss: '0-1 法国(2018半决赛)',
    yearlyStats: {
      2014: { position: '八强', played: 5, won: 4, drawn: 0, lost: 1, goalsFor: 6, goalsAgainst: 3, finalRank: 6 },
      2018: { position: '四强', played: 7, won: 4, drawn: 0, lost: 3, goalsFor: 16, goalsAgainst: 7, finalRank: 3 },
      2022: { position: '小组赛', played: 3, won: 1, drawn: 0, lost: 2, goalsFor: 1, goalsAgainst: 2, finalRank: 23 },
    }
  },
  {
    name: '乌拉圭',
    flagCode: 'uy',
    tournaments: [2010, 2014, 2018, 2022],
    titles: 0,
    finals: 0,
    semiFinals: 1,
    quarterFinals: 2,
    totalWins: 11,
    totalDraws: 5,
    totalLosses: 5,
    totalGoalsFor: 33,
    totalGoalsAgainst: 20,
    biggestWin: '3-0 南非(2010)',
    biggestLoss: '0-2 葡萄牙(2022小组赛)',
    yearlyStats: {
      2010: { position: '四强', played: 7, won: 3, drawn: 2, lost: 2, goalsFor: 11, goalsAgainst: 8, finalRank: 4 },
      2014: { position: '十六强', played: 4, won: 2, drawn: 0, lost: 2, goalsFor: 4, goalsAgainst: 6, finalRank: 12 },
      2018: { position: '八强', played: 5, won: 4, drawn: 0, lost: 1, goalsFor: 7, goalsAgainst: 3, finalRank: 5 },
      2022: { position: '小组赛', played: 3, won: 2, drawn: 0, lost: 1, goalsFor: 4, goalsAgainst: 2, finalRank: 14 },
    }
  },
  {
    name: '葡萄牙',
    flagCode: 'pt',
    tournaments: [2010, 2014, 2018, 2022],
    titles: 0,
    finals: 0,
    semiFinals: 0,
    quarterFinals: 2,
    totalWins: 9,
    totalDraws: 6,
    totalLosses: 5,
    totalGoalsFor: 24,
    totalGoalsAgainst: 16,
    biggestWin: '7-0 朝鲜(2010)',
    biggestLoss: '0-1 西班牙(2018十六强)',
    yearlyStats: {
      2010: { position: '十六强', played: 4, won: 1, drawn: 3, lost: 0, goalsFor: 7, goalsAgainst: 1, finalRank: 11 },
      2014: { position: '小组赛', played: 3, won: 1, drawn: 1, lost: 1, goalsFor: 4, goalsAgainst: 4, finalRank: 18 },
      2018: { position: '十六强', played: 4, won: 1, drawn: 2, lost: 1, goalsFor: 6, goalsAgainst: 6, finalRank: 13 },
      2022: { position: '八强', played: 5, won: 3, drawn: 0, lost: 2, goalsFor: 6, goalsAgainst: 5, finalRank: 8 },
    }
  },
  {
    name: '意大利',
    flagCode: 'it',
    tournaments: [2010, 2014],
    titles: 0,
    finals: 0,
    semiFinals: 0,
    quarterFinals: 0,
    totalWins: 1,
    totalDraws: 4,
    totalLosses: 3,
    totalGoalsFor: 6,
    totalGoalsAgainst: 10,
    biggestWin: '2-0 法国(2010友谊赛)',
    biggestLoss: '1-4 哥斯达黎加(2014)',
    yearlyStats: {
      2010: { position: '小组赛', played: 3, won: 0, drawn: 2, lost: 1, goalsFor: 4, goalsAgainst: 5, finalRank: 26 },
      2014: { position: '小组赛', played: 3, won: 1, drawn: 2, lost: 0, goalsFor: 2, goalsAgainst: 5, finalRank: 22 },
    }
  },
  {
    name: '墨西哥',
    flagCode: 'mx',
    tournaments: [2010, 2014, 2018, 2022],
    titles: 0,
    finals: 0,
    semiFinals: 0,
    quarterFinals: 0,
    totalWins: 7,
    totalDraws: 7,
    totalLosses: 7,
    totalGoalsFor: 25,
    totalGoalsAgainst: 27,
    biggestWin: '3-1 克罗地亚(2014)',
    biggestLoss: '0-3 瑞典(2018)',
    yearlyStats: {
      2010: { position: '十六强', played: 4, won: 1, drawn: 2, lost: 1, goalsFor: 4, goalsAgainst: 5, finalRank: 14 },
      2014: { position: '十六强', played: 4, won: 2, drawn: 1, lost: 1, goalsFor: 5, goalsAgainst: 5, finalRank: 10 },
      2018: { position: '十六强', played: 4, won: 2, drawn: 0, lost: 2, goalsFor: 6, goalsAgainst: 7, finalRank: 12 },
      2022: { position: '小组赛', played: 3, won: 1, drawn: 1, lost: 1, goalsFor: 4, goalsAgainst: 5, finalRank: 22 },
    }
  },
  {
    name: '日本',
    flagCode: 'jp',
    tournaments: [2010, 2014, 2018, 2022],
    titles: 0,
    finals: 0,
    semiFinals: 0,
    quarterFinals: 0,
    totalWins: 6,
    totalDraws: 5,
    totalLosses: 7,
    totalGoalsFor: 18,
    totalGoalsAgainst: 22,
    biggestWin: '2-1 德国(2022)',
    biggestLoss: '1-4 哥伦比亚(2018)',
    yearlyStats: {
      2010: { position: '十六强', played: 4, won: 2, drawn: 1, lost: 1, goalsFor: 4, goalsAgainst: 2, finalRank: 9 },
      2014: { position: '小组赛', played: 3, won: 0, drawn: 1, lost: 2, goalsFor: 2, goalsAgainst: 6, finalRank: 29 },
      2018: { position: '十六强', played: 4, won: 1, drawn: 1, lost: 2, goalsFor: 5, goalsAgainst: 7, finalRank: 15 },
      2022: { position: '十六强', played: 4, won: 2, drawn: 1, lost: 1, goalsFor: 5, goalsAgainst: 4, finalRank: 9 },
    }
  },
  {
    name: '韩国',
    flagCode: 'kr',
    tournaments: [2010, 2014, 2018, 2022],
    titles: 0,
    finals: 0,
    semiFinals: 0,
    quarterFinals: 0,
    totalWins: 4,
    totalDraws: 3,
    totalLosses: 9,
    totalGoalsFor: 14,
    totalGoalsAgainst: 25,
    biggestWin: '2-0 德国(2018)',
    biggestLoss: '0-7 葡萄牙(2010)',
    yearlyStats: {
      2010: { position: '小组赛', played: 3, won: 1, drawn: 0, lost: 2, goalsFor: 5, goalsAgainst: 8, finalRank: 15 },
      2014: { position: '小组赛', played: 3, won: 0, drawn: 1, lost: 2, goalsFor: 3, goalsAgainst: 6, finalRank: 27 },
      2018: { position: '小组赛', played: 3, won: 1, drawn: 1, lost: 1, goalsFor: 3, goalsAgainst: 3, finalRank: 19 },
      2022: { position: '十六强', played: 4, won: 1, drawn: 1, lost: 2, goalsFor: 5, goalsAgainst: 8, finalRank: 16 },
    }
  },
  {
    name: '美国',
    flagCode: 'us',
    tournaments: [2010, 2014, 2022],
    titles: 0,
    finals: 0,
    semiFinals: 0,
    quarterFinals: 0,
    totalWins: 5,
    totalDraws: 4,
    totalLosses: 5,
    totalGoalsFor: 18,
    totalGoalsAgainst: 18,
    biggestWin: '3-0 伊朗(1998)',
    biggestLoss: '1-2 加纳(2010加时)',
    yearlyStats: {
      2010: { position: '十六强', played: 4, won: 1, drawn: 2, lost: 1, goalsFor: 5, goalsAgainst: 5, finalRank: 12 },
      2014: { position: '十六强', played: 4, won: 1, drawn: 2, lost: 1, goalsFor: 5, goalsAgainst: 6, finalRank: 15 },
      2022: { position: '十六强', played: 4, won: 2, drawn: 1, lost: 1, goalsFor: 5, goalsAgainst: 4, finalRank: 9 },
    }
  },
]

const LEGACY_TEAM_HISTORICAL_STATS: TeamHistoricalStats[] = [
  {
    name: '巴西',
    flagCode: 'br',
    tournaments: [1994, 1998, 2002, 2006],
    titles: 2,
    finals: 3,
    semiFinals: 3,
    quarterFinals: 4,
    totalWins: 20,
    totalDraws: 3,
    totalLosses: 3,
    totalGoalsFor: 53,
    totalGoalsAgainst: 19,
    biggestWin: '4-0 中国(2002)',
    biggestLoss: '0-3 法国(1998决赛)',
    yearlyStats: {
      1994: { position: '冠军', played: 7, won: 5, drawn: 2, lost: 0, goalsFor: 11, goalsAgainst: 3, finalRank: 1 },
      1998: { position: '亚军', played: 7, won: 4, drawn: 1, lost: 2, goalsFor: 14, goalsAgainst: 10, finalRank: 2 },
      2002: { position: '冠军', played: 7, won: 7, drawn: 0, lost: 0, goalsFor: 18, goalsAgainst: 4, finalRank: 1 },
      2006: { position: '八强', played: 5, won: 4, drawn: 0, lost: 1, goalsFor: 10, goalsAgainst: 2, finalRank: 5 },
    },
  },
  {
    name: '意大利',
    flagCode: 'it',
    tournaments: [1994, 1998, 2002, 2006],
    titles: 1,
    finals: 2,
    semiFinals: 2,
    quarterFinals: 3,
    totalWins: 13,
    totalDraws: 6,
    totalLosses: 4,
    totalGoalsFor: 33,
    totalGoalsAgainst: 15,
    biggestWin: '3-0 乌克兰(2006八强)',
    biggestLoss: '1-2 韩国(2002十六强)',
    yearlyStats: {
      1994: { position: '亚军', played: 7, won: 4, drawn: 2, lost: 1, goalsFor: 8, goalsAgainst: 5, finalRank: 2 },
      1998: { position: '八强', played: 5, won: 3, drawn: 1, lost: 1, goalsFor: 8, goalsAgainst: 3, finalRank: 5 },
      2002: { position: '十六强', played: 4, won: 1, drawn: 1, lost: 2, goalsFor: 5, goalsAgainst: 5, finalRank: 15 },
      2006: { position: '冠军', played: 7, won: 5, drawn: 2, lost: 0, goalsFor: 12, goalsAgainst: 2, finalRank: 1 },
    },
  },
  {
    name: '德国',
    flagCode: 'de',
    tournaments: [1994, 1998, 2002, 2006],
    titles: 0,
    finals: 1,
    semiFinals: 2,
    quarterFinals: 4,
    totalWins: 16,
    totalDraws: 4,
    totalLosses: 4,
    totalGoalsFor: 45,
    totalGoalsAgainst: 22,
    biggestWin: '8-0 沙特阿拉伯(2002)',
    biggestLoss: '0-3 克罗地亚(1998八强)',
    yearlyStats: {
      1994: { position: '八强', played: 5, won: 3, drawn: 1, lost: 1, goalsFor: 9, goalsAgainst: 7, finalRank: 5 },
      1998: { position: '八强', played: 5, won: 3, drawn: 1, lost: 1, goalsFor: 8, goalsAgainst: 6, finalRank: 7 },
      2002: { position: '亚军', played: 7, won: 5, drawn: 1, lost: 1, goalsFor: 14, goalsAgainst: 3, finalRank: 2 },
      2006: { position: '四强', played: 7, won: 5, drawn: 1, lost: 1, goalsFor: 14, goalsAgainst: 6, finalRank: 3 },
    },
  },
  {
    name: '法国',
    flagCode: 'fr',
    tournaments: [1998, 2002, 2006],
    titles: 1,
    finals: 2,
    semiFinals: 2,
    quarterFinals: 2,
    totalWins: 10,
    totalDraws: 4,
    totalLosses: 3,
    totalGoalsFor: 24,
    totalGoalsAgainst: 8,
    biggestWin: '3-0 巴西(1998决赛)',
    biggestLoss: '0-2 丹麦(2002小组赛)',
    yearlyStats: {
      1998: { position: '冠军', played: 7, won: 6, drawn: 1, lost: 0, goalsFor: 15, goalsAgainst: 2, finalRank: 1 },
      2002: { position: '小组赛', played: 3, won: 0, drawn: 1, lost: 2, goalsFor: 0, goalsAgainst: 3, finalRank: 28 },
      2006: { position: '亚军', played: 7, won: 4, drawn: 2, lost: 1, goalsFor: 9, goalsAgainst: 3, finalRank: 2 },
    },
  },
  {
    name: '阿根廷',
    flagCode: 'ar',
    tournaments: [1994, 1998, 2002, 2006],
    titles: 0,
    finals: 0,
    semiFinals: 0,
    quarterFinals: 2,
    totalWins: 9,
    totalDraws: 4,
    totalLosses: 4,
    totalGoalsFor: 31,
    totalGoalsAgainst: 15,
    biggestWin: '6-0 塞黑(2006)',
    biggestLoss: '1-2 荷兰(1998八强)',
    yearlyStats: {
      1994: { position: '十六强', played: 4, won: 2, drawn: 0, lost: 2, goalsFor: 8, goalsAgainst: 6, finalRank: 10 },
      1998: { position: '八强', played: 5, won: 3, drawn: 1, lost: 1, goalsFor: 10, goalsAgainst: 4, finalRank: 6 },
      2002: { position: '小组赛', played: 3, won: 1, drawn: 1, lost: 1, goalsFor: 2, goalsAgainst: 2, finalRank: 18 },
      2006: { position: '八强', played: 5, won: 3, drawn: 2, lost: 0, goalsFor: 11, goalsAgainst: 3, finalRank: 6 },
    },
  },
  {
    name: '荷兰',
    flagCode: 'nl',
    tournaments: [1994, 1998, 2006],
    titles: 0,
    finals: 0,
    semiFinals: 1,
    quarterFinals: 2,
    totalWins: 8,
    totalDraws: 4,
    totalLosses: 4,
    totalGoalsFor: 24,
    totalGoalsAgainst: 15,
    biggestWin: '5-0 韩国(1998)',
    biggestLoss: '1-2 巴西(1994八强)',
    yearlyStats: {
      1994: { position: '八强', played: 5, won: 3, drawn: 0, lost: 2, goalsFor: 8, goalsAgainst: 6, finalRank: 7 },
      1998: { position: '四强', played: 7, won: 3, drawn: 3, lost: 1, goalsFor: 13, goalsAgainst: 7, finalRank: 4 },
      2006: { position: '十六强', played: 4, won: 2, drawn: 1, lost: 1, goalsFor: 3, goalsAgainst: 2, finalRank: 11 },
    },
  },
  {
    name: '克罗地亚',
    flagCode: 'hr',
    tournaments: [1998, 2002, 2006],
    titles: 0,
    finals: 0,
    semiFinals: 1,
    quarterFinals: 1,
    totalWins: 6,
    totalDraws: 2,
    totalLosses: 5,
    totalGoalsFor: 15,
    totalGoalsAgainst: 11,
    biggestWin: '3-0 德国(1998八强)',
    biggestLoss: '0-1 厄瓜多尔(2002)',
    yearlyStats: {
      1998: { position: '四强', played: 7, won: 5, drawn: 0, lost: 2, goalsFor: 11, goalsAgainst: 5, finalRank: 3 },
      2002: { position: '小组赛', played: 3, won: 1, drawn: 0, lost: 2, goalsFor: 2, goalsAgainst: 3, finalRank: 23 },
      2006: { position: '小组赛', played: 3, won: 0, drawn: 2, lost: 1, goalsFor: 2, goalsAgainst: 3, finalRank: 22 },
    },
  },
  {
    name: '英格兰',
    flagCode: 'gb-eng',
    tournaments: [1998, 2002, 2006],
    titles: 0,
    finals: 0,
    semiFinals: 0,
    quarterFinals: 2,
    totalWins: 7,
    totalDraws: 5,
    totalLosses: 2,
    totalGoalsFor: 19,
    totalGoalsAgainst: 9,
    biggestWin: '3-0 丹麦(2002十六强)',
    biggestLoss: '1-2 巴西(2002八强)',
    yearlyStats: {
      1998: { position: '十六强', played: 4, won: 2, drawn: 1, lost: 1, goalsFor: 7, goalsAgainst: 4, finalRank: 9 },
      2002: { position: '八强', played: 5, won: 2, drawn: 2, lost: 1, goalsFor: 6, goalsAgainst: 3, finalRank: 6 },
      2006: { position: '八强', played: 5, won: 3, drawn: 2, lost: 0, goalsFor: 6, goalsAgainst: 2, finalRank: 7 },
    },
  },
  {
    name: '西班牙',
    flagCode: 'es',
    tournaments: [1994, 1998, 2002, 2006],
    titles: 0,
    finals: 0,
    semiFinals: 0,
    quarterFinals: 2,
    totalWins: 9,
    totalDraws: 5,
    totalLosses: 3,
    totalGoalsFor: 37,
    totalGoalsAgainst: 19,
    biggestWin: '6-1 保加利亚(1998)',
    biggestLoss: '1-3 法国(2006十六强)',
    yearlyStats: {
      1994: { position: '八强', played: 5, won: 2, drawn: 2, lost: 1, goalsFor: 10, goalsAgainst: 6, finalRank: 8 },
      1998: { position: '小组赛', played: 3, won: 1, drawn: 1, lost: 1, goalsFor: 8, goalsAgainst: 4, finalRank: 17 },
      2002: { position: '八强', played: 5, won: 3, drawn: 2, lost: 0, goalsFor: 10, goalsAgainst: 5, finalRank: 5 },
      2006: { position: '十六强', played: 4, won: 3, drawn: 0, lost: 1, goalsFor: 9, goalsAgainst: 4, finalRank: 9 },
    },
  },
  {
    name: '葡萄牙',
    flagCode: 'pt',
    tournaments: [2002, 2006],
    titles: 0,
    finals: 0,
    semiFinals: 1,
    quarterFinals: 1,
    totalWins: 5,
    totalDraws: 1,
    totalLosses: 4,
    totalGoalsFor: 13,
    totalGoalsAgainst: 9,
    biggestWin: '4-0 波兰(2002)',
    biggestLoss: '0-1 法国(2006半决赛)',
    yearlyStats: {
      2002: { position: '小组赛', played: 3, won: 1, drawn: 0, lost: 2, goalsFor: 6, goalsAgainst: 4, finalRank: 21 },
      2006: { position: '四强', played: 7, won: 4, drawn: 1, lost: 2, goalsFor: 7, goalsAgainst: 5, finalRank: 4 },
    },
  },
  {
    name: '墨西哥',
    flagCode: 'mx',
    tournaments: [1994, 1998, 2002, 2006],
    titles: 0,
    finals: 0,
    semiFinals: 0,
    quarterFinals: 0,
    totalWins: 5,
    totalDraws: 6,
    totalLosses: 5,
    totalGoalsFor: 21,
    totalGoalsAgainst: 20,
    biggestWin: '3-1 厄瓜多尔(2002)',
    biggestLoss: '1-2 阿根廷(2006十六强)',
    yearlyStats: {
      1994: { position: '十六强', played: 4, won: 1, drawn: 2, lost: 1, goalsFor: 4, goalsAgainst: 4, finalRank: 13 },
      1998: { position: '十六强', played: 4, won: 1, drawn: 2, lost: 1, goalsFor: 8, goalsAgainst: 7, finalRank: 13 },
      2002: { position: '十六强', played: 4, won: 2, drawn: 1, lost: 1, goalsFor: 4, goalsAgainst: 4, finalRank: 11 },
      2006: { position: '十六强', played: 4, won: 1, drawn: 1, lost: 2, goalsFor: 5, goalsAgainst: 5, finalRank: 15 },
    },
  },
  {
    name: '美国',
    flagCode: 'us',
    tournaments: [1994, 1998, 2002, 2006],
    titles: 0,
    finals: 0,
    semiFinals: 0,
    quarterFinals: 1,
    totalWins: 3,
    totalDraws: 3,
    totalLosses: 9,
    totalGoalsFor: 13,
    totalGoalsAgainst: 22,
    biggestWin: '3-2 葡萄牙(2002)',
    biggestLoss: '0-3 捷克(2006)',
    yearlyStats: {
      1994: { position: '十六强', played: 4, won: 1, drawn: 1, lost: 2, goalsFor: 3, goalsAgainst: 4, finalRank: 14 },
      1998: { position: '小组赛', played: 3, won: 0, drawn: 0, lost: 3, goalsFor: 1, goalsAgainst: 5, finalRank: 32 },
      2002: { position: '八强', played: 5, won: 2, drawn: 1, lost: 2, goalsFor: 7, goalsAgainst: 7, finalRank: 8 },
      2006: { position: '小组赛', played: 3, won: 0, drawn: 1, lost: 2, goalsFor: 2, goalsAgainst: 6, finalRank: 25 },
    },
  },
  {
    name: '日本',
    flagCode: 'jp',
    tournaments: [1998, 2002, 2006],
    titles: 0,
    finals: 0,
    semiFinals: 0,
    quarterFinals: 0,
    totalWins: 2,
    totalDraws: 2,
    totalLosses: 6,
    totalGoalsFor: 8,
    totalGoalsAgainst: 14,
    biggestWin: '2-0 突尼斯(2002)',
    biggestLoss: '1-4 巴西(2006)',
    yearlyStats: {
      1998: { position: '小组赛', played: 3, won: 0, drawn: 0, lost: 3, goalsFor: 1, goalsAgainst: 4, finalRank: 31 },
      2002: { position: '十六强', played: 4, won: 2, drawn: 1, lost: 1, goalsFor: 5, goalsAgainst: 3, finalRank: 9 },
      2006: { position: '小组赛', played: 3, won: 0, drawn: 1, lost: 2, goalsFor: 2, goalsAgainst: 7, finalRank: 28 },
    },
  },
  {
    name: '韩国',
    flagCode: 'kr',
    tournaments: [1994, 1998, 2002, 2006],
    titles: 0,
    finals: 0,
    semiFinals: 1,
    quarterFinals: 1,
    totalWins: 4,
    totalDraws: 6,
    totalLosses: 6,
    totalGoalsFor: 17,
    totalGoalsAgainst: 24,
    biggestWin: '2-1 意大利(2002十六强)',
    biggestLoss: '0-5 荷兰(1998)',
    yearlyStats: {
      1994: { position: '小组赛', played: 3, won: 0, drawn: 2, lost: 1, goalsFor: 4, goalsAgainst: 5, finalRank: 20 },
      1998: { position: '小组赛', played: 3, won: 0, drawn: 1, lost: 2, goalsFor: 2, goalsAgainst: 9, finalRank: 30 },
      2002: { position: '四强', played: 7, won: 3, drawn: 2, lost: 2, goalsFor: 8, goalsAgainst: 6, finalRank: 4 },
      2006: { position: '小组赛', played: 3, won: 1, drawn: 1, lost: 1, goalsFor: 3, goalsAgainst: 4, finalRank: 17 },
    },
  },
  {
    name: '土耳其',
    flagCode: 'tr',
    tournaments: [2002],
    titles: 0,
    finals: 0,
    semiFinals: 1,
    quarterFinals: 1,
    totalWins: 4,
    totalDraws: 1,
    totalLosses: 2,
    totalGoalsFor: 10,
    totalGoalsAgainst: 6,
    biggestWin: '3-2 韩国(2002三四名)',
    biggestLoss: '0-1 巴西(2002半决赛)',
    yearlyStats: {
      2002: { position: '四强', played: 7, won: 4, drawn: 1, lost: 2, goalsFor: 10, goalsAgainst: 6, finalRank: 3 },
    },
  },
  {
    name: '瑞典',
    flagCode: 'se',
    tournaments: [1994, 2002, 2006],
    titles: 0,
    finals: 0,
    semiFinals: 1,
    quarterFinals: 1,
    totalWins: 5,
    totalDraws: 7,
    totalLosses: 3,
    totalGoalsFor: 23,
    totalGoalsAgainst: 15,
    biggestWin: '4-0 保加利亚(1994三四名)',
    biggestLoss: '0-2 德国(2006十六强)',
    yearlyStats: {
      1994: { position: '四强', played: 7, won: 3, drawn: 3, lost: 1, goalsFor: 15, goalsAgainst: 8, finalRank: 3 },
      2002: { position: '十六强', played: 4, won: 1, drawn: 2, lost: 1, goalsFor: 5, goalsAgainst: 5, finalRank: 13 },
      2006: { position: '十六强', played: 4, won: 1, drawn: 2, lost: 1, goalsFor: 3, goalsAgainst: 2, finalRank: 14 },
    },
  },
  {
    name: '保加利亚',
    flagCode: 'bg',
    tournaments: [1994, 1998],
    titles: 0,
    finals: 0,
    semiFinals: 1,
    quarterFinals: 1,
    totalWins: 3,
    totalDraws: 1,
    totalLosses: 6,
    totalGoalsFor: 10,
    totalGoalsAgainst: 18,
    biggestWin: '4-0 希腊(1994)',
    biggestLoss: '1-6 西班牙(1998)',
    yearlyStats: {
      1994: { position: '四强', played: 7, won: 3, drawn: 1, lost: 3, goalsFor: 10, goalsAgainst: 11, finalRank: 4 },
      1998: { position: '小组赛', played: 3, won: 0, drawn: 0, lost: 3, goalsFor: 0, goalsAgainst: 7, finalRank: 29 },
    },
  },
]

function mergeTeamHistoricalStats(
  baseStats: TeamHistoricalStats[],
  legacyStats: TeamHistoricalStats[],
): TeamHistoricalStats[] {
  const byName = new Map<string, TeamHistoricalStats>()

  baseStats.forEach(team => {
    byName.set(team.name, {
      ...team,
      tournaments: [...team.tournaments],
      yearlyStats: { ...team.yearlyStats },
    })
  })

  legacyStats.forEach(legacy => {
    const existing = byName.get(legacy.name)
    if (!existing) {
      byName.set(legacy.name, {
        ...legacy,
        tournaments: [...legacy.tournaments],
        yearlyStats: { ...legacy.yearlyStats },
      })
      return
    }

    existing.tournaments = Array.from(new Set([...legacy.tournaments, ...existing.tournaments])).sort((a, b) => b - a)
    existing.titles += legacy.titles
    existing.finals += legacy.finals
    existing.semiFinals += legacy.semiFinals
    existing.quarterFinals += legacy.quarterFinals
    existing.totalWins += legacy.totalWins
    existing.totalDraws += legacy.totalDraws
    existing.totalLosses += legacy.totalLosses
    existing.totalGoalsFor += legacy.totalGoalsFor
    existing.totalGoalsAgainst += legacy.totalGoalsAgainst
    existing.biggestWin = legacy.biggestWin
    existing.biggestLoss = legacy.biggestLoss
    existing.yearlyStats = { ...legacy.yearlyStats, ...existing.yearlyStats }
  })

  return Array.from(byName.values())
}

export const TEAM_HISTORICAL_STATS: TeamHistoricalStats[] = mergeTeamHistoricalStats(
  BASE_TEAM_HISTORICAL_STATS,
  LEGACY_TEAM_HISTORICAL_STATS,
)

// 可选的年份列表
export const AVAILABLE_YEARS = [2026, 2022, 2018, 2014, 2010, 2006, 2002, 1998, 1994]

// 球员统计排序字段
export type PlayerSortField = 'goals' | 'assists' | 'appearances' | 'yellowCards' | 'redCards'

// 球队统计排序字段
export type TeamSortField = 'totalWins' | 'totalGoalsFor' | 'totalGoalsAgainst' | 'titles' | 'winRate'
