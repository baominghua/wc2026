"""数据库初始化脚本 - 创建表并填充种子数据"""
import asyncio
from datetime import datetime
from database.connection import init_db, async_session
from models.database import Team, Player, Match
from sqlalchemy import select

# 48支参赛球队种子数据
SEED_TEAMS = [
    # A组
    {"name": "United States", "code": "USA", "group_name": "A", "fifa_rank": 11, "elo_rating": 1850, "confederation": "CONCACAF", "coach": "Gregg Berhalter", "world_cup_titles": 0, "flag_emoji": "🇺🇸"},
    {"name": "Mexico", "code": "MEX", "group_name": "A", "fifa_rank": 15, "elo_rating": 1800, "confederation": "CONCACAF", "coach": "Jaime Lozano", "world_cup_titles": 0, "flag_emoji": "🇲🇽"},
    {"name": "Argentina", "code": "ARG", "group_name": "A", "fifa_rank": 1, "elo_rating": 2100, "confederation": "CONMEBOL", "coach": "Lionel Scaloni", "world_cup_titles": 3, "flag_emoji": "🇦🇷"},
    {"name": "New Zealand", "code": "NZL", "group_name": "A", "fifa_rank": 95, "elo_rating": 1500, "confederation": "OFC", "coach": "Danny Hay", "world_cup_titles": 0, "flag_emoji": "🇳🇿"},
    # B组
    {"name": "England", "code": "ENG", "group_name": "B", "fifa_rank": 4, "elo_rating": 2000, "confederation": "UEFA", "coach": "Thomas Tuchel", "world_cup_titles": 1, "flag_emoji": "🏴"},
    {"name": "Netherlands", "code": "NED", "group_name": "B", "fifa_rank": 8, "elo_rating": 1920, "confederation": "UEFA", "coach": "Ronald Koeman", "world_cup_titles": 0, "flag_emoji": "🇳🇱"},
    {"name": "Senegal", "code": "SEN", "group_name": "B", "fifa_rank": 18, "elo_rating": 1720, "confederation": "CAF", "coach": "Aliou Cissé", "world_cup_titles": 0, "flag_emoji": "🇸🇳"},
    {"name": "Iran", "code": "IRN", "group_name": "B", "fifa_rank": 20, "elo_rating": 1700, "confederation": "AFC", "coach": "Amir Ghalenoei", "world_cup_titles": 0, "flag_emoji": "🇮🇷"},
    # C组
    {"name": "Spain", "code": "ESP", "group_name": "C", "fifa_rank": 5, "elo_rating": 1980, "confederation": "UEFA", "coach": "Luis de la Fuente", "world_cup_titles": 1, "flag_emoji": "🇪🇸"},
    {"name": "Uruguay", "code": "URU", "group_name": "C", "fifa_rank": 12, "elo_rating": 1830, "confederation": "CONMEBOL", "coach": "Marcelo Bielsa", "world_cup_titles": 2, "flag_emoji": "🇺🇾"},
    {"name": "Colombia", "code": "COL", "group_name": "C", "fifa_rank": 14, "elo_rating": 1810, "confederation": "CONMEBOL", "coach": "Néstor Lorenzo", "world_cup_titles": 0, "flag_emoji": "🇨🇴"},
    {"name": "Australia", "code": "AUS", "group_name": "C", "fifa_rank": 25, "elo_rating": 1680, "confederation": "AFC", "coach": "Tony Popovic", "world_cup_titles": 0, "flag_emoji": "🇦🇺"},
    # D组
    {"name": "France", "code": "FRA", "group_name": "D", "fifa_rank": 2, "elo_rating": 2050, "confederation": "UEFA", "coach": "Didier Deschamps", "world_cup_titles": 2, "flag_emoji": "🇫🇷"},
    {"name": "Brazil", "code": "BRA", "group_name": "D", "fifa_rank": 3, "elo_rating": 2080, "confederation": "CONMEBOL", "coach": "Dorival Júnior", "world_cup_titles": 5, "flag_emoji": "🇧🇷"},
    {"name": "Switzerland", "code": "SUI", "group_name": "D", "fifa_rank": 17, "elo_rating": 1750, "confederation": "UEFA", "coach": "Murat Yakin", "world_cup_titles": 0, "flag_emoji": "🇨🇭"},
    {"name": "Cameroon", "code": "CMR", "group_name": "D", "fifa_rank": 40, "elo_rating": 1620, "confederation": "CAF", "coach": "Marc Brys", "world_cup_titles": 0, "flag_emoji": "🇨🇲"},
    # E组
    {"name": "Germany", "code": "DEU", "group_name": "E", "fifa_rank": 6, "elo_rating": 1960, "confederation": "UEFA", "coach": "Julian Nagelsmann", "world_cup_titles": 4, "flag_emoji": "🇩🇪"},
    {"name": "Portugal", "code": "POR", "group_name": "E", "fifa_rank": 7, "elo_rating": 1950, "confederation": "UEFA", "coach": "Roberto Martínez", "world_cup_titles": 0, "flag_emoji": "🇵🇹"},
    {"name": "Croatia", "code": "CRO", "group_name": "E", "fifa_rank": 10, "elo_rating": 1860, "confederation": "UEFA", "coach": "Zlatko Dalić", "world_cup_titles": 0, "flag_emoji": "🇭🇷"},
    {"name": "Ghana", "code": "GHA", "group_name": "E", "fifa_rank": 55, "elo_rating": 1560, "confederation": "CAF", "coach": "Otto Addo", "world_cup_titles": 0, "flag_emoji": "🇬🇭"},
    # F组
    {"name": "Belgium", "code": "BEL", "group_name": "F", "fifa_rank": 9, "elo_rating": 1900, "confederation": "UEFA", "coach": "Domenico Tedesco", "world_cup_titles": 0, "flag_emoji": "🇧🇪"},
    {"name": "Italy", "code": "ITA", "group_name": "F", "fifa_rank": 13, "elo_rating": 1820, "confederation": "UEFA", "coach": "Luciano Spalletti", "world_cup_titles": 4, "flag_emoji": "🇮🇹"},
    {"name": "Serbia", "code": "SRB", "group_name": "F", "fifa_rank": 32, "elo_rating": 1650, "confederation": "UEFA", "coach": "Dragan Stojković", "world_cup_titles": 0, "flag_emoji": "🇷🇸"},
    {"name": "Ecuador", "code": "ECU", "group_name": "F", "fifa_rank": 35, "elo_rating": 1630, "confederation": "CONMEBOL", "coach": "Sebastián Beccacece", "world_cup_titles": 0, "flag_emoji": "🇪🇨"},
    # G组
    {"name": "South Korea", "code": "KOR", "group_name": "G", "fifa_rank": 23, "elo_rating": 1690, "confederation": "AFC", "coach": "Hong Myung-bo", "world_cup_titles": 0, "flag_emoji": "🇰🇷"},
    {"name": "Japan", "code": "JPN", "group_name": "G", "fifa_rank": 19, "elo_rating": 1710, "confederation": "AFC", "coach": "Hajime Moriyasu", "world_cup_titles": 0, "flag_emoji": "🇯🇵"},
    {"name": "Morocco", "code": "MAR", "group_name": "G", "fifa_rank": 16, "elo_rating": 1790, "confederation": "CAF", "coach": "Walid Regragui", "world_cup_titles": 0, "flag_emoji": "🇲🇦"},
    {"name": "Canada", "code": "CAN", "group_name": "G", "fifa_rank": 50, "elo_rating": 1580, "confederation": "CONCACAF", "coach": "Jesse Marsch", "world_cup_titles": 0, "flag_emoji": "🇨🇦"},
]

SEED_MATCHES = [
    {"home_team_code": "USA", "away_team_code": "MEX", "group_name": "A", "round": "Group Stage", "match_date": "2026-06-13T20:00:00Z", "venue": "SoFi Stadium", "city": "Los Angeles", "country": "USA"},
    {"home_team_code": "ARG", "away_team_code": "NZL", "group_name": "A", "round": "Group Stage", "match_date": "2026-06-14T19:00:00Z", "venue": "MetLife Stadium", "city": "New York", "country": "USA"},
    {"home_team_code": "ENG", "away_team_code": "IRN", "group_name": "B", "round": "Group Stage", "match_date": "2026-06-14T20:00:00Z", "venue": "Lumen Field", "city": "Seattle", "country": "USA"},
    {"home_team_code": "FRA", "away_team_code": "CMR", "group_name": "D", "round": "Group Stage", "match_date": "2026-06-15T19:00:00Z", "venue": "MetLife Stadium", "city": "New York", "country": "USA"},
    {"home_team_code": "BRA", "away_team_code": "SUI", "group_name": "D", "round": "Group Stage", "match_date": "2026-06-16T20:00:00Z", "venue": "AT&T Stadium", "city": "Dallas", "country": "USA"},
    {"home_team_code": "ESP", "away_team_code": "AUS", "group_name": "C", "round": "Group Stage", "match_date": "2026-06-17T20:00:00Z", "venue": "Hard Rock Stadium", "city": "Miami", "country": "USA"},
    {"home_team_code": "DEU", "away_team_code": "GHA", "group_name": "E", "round": "Group Stage", "match_date": "2026-06-18T19:00:00Z", "venue": "BMO Field", "city": "Toronto", "country": "Canada"},
    {"home_team_code": "KOR", "away_team_code": "CAN", "group_name": "G", "round": "Group Stage", "match_date": "2026-06-19T20:00:00Z", "venue": "Estadio Azteca", "city": "Mexico City", "country": "Mexico"},
]


async def seed_data():
    """填充种子数据"""
    await init_db()
    
    async with async_session() as session:
        # 检查是否已有数据
        result = await session.execute(select(Team).limit(1))
        if result.scalar():
            print("Database already seeded, skipping...")
            return
        
        # 插入球队
        team_map = {}
        for team_data in SEED_TEAMS:
            team = Team(**team_data)
            session.add(team)
            await session.flush()
            team_map[team.code] = team.id
            print(f"  Added team: {team.name} ({team.code})")
        
        # 插入比赛
        for match_data in SEED_MATCHES:
            home_id = team_map.get(match_data["home_team_code"])
            away_id = team_map.get(match_data["away_team_code"])
            if home_id and away_id:
                match = Match(
                    home_team_id=home_id,
                    away_team_id=away_id,
                    group_name=match_data["group_name"],
                    round=match_data["round"],
                    match_date=datetime.fromisoformat(match_data["match_date"].replace("Z", "+00:00")),
                    venue=match_data["venue"],
                    city=match_data["city"],
                    country=match_data["country"],
                    status="upcoming"
                )
                session.add(match)
                print(f"  Added match: {match_data['home_team_code']} vs {match_data['away_team_code']}")
        
        await session.commit()
        print(f"\nSeeding complete! {len(SEED_TEAMS)} teams and {len(SEED_MATCHES)} matches added.")


if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(seed_data())
