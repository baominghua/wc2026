from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Team(Base):
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(3), nullable=False)
    group_name = Column(String(1), nullable=False)  # A-L (12组)
    fifa_rank = Column(Integer, nullable=True)
    elo_rating = Column(Float, default=1500.0)
    confederation = Column(String(10), nullable=True)  # AFC, CAF, CONCACAF, CONMEBOL, OFC, UEFA
    coach = Column(String(100), nullable=True)
    world_cup_titles = Column(Integer, default=0)
    flag_emoji = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    players = relationship("Player", back_populates="team")
    home_matches = relationship("Match", foreign_keys="Match.home_team_id", back_populates="home_team")
    away_matches = relationship("Match", foreign_keys="Match.away_team_id", back_populates="away_team")


class Player(Base):
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    position = Column(String(5), nullable=False)  # GK, DF, MF, FW
    jersey_number = Column(Integer, nullable=True)
    age = Column(Integer, nullable=True)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    caps = Column(Integer, default=0)  # 出场次数
    xg = Column(Float, default=0.0)  # 预期进球
    market_value = Column(Float, nullable=True)  # 身价（万欧元）
    is_key_player = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    team = relationship("Team", back_populates="players")


class Match(Base):
    __tablename__ = "matches"
    
    id = Column(Integer, primary_key=True, index=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    group_name = Column(String(1), nullable=True)  # 小组赛有组别，淘汰赛为null
    round = Column(String(20), nullable=True)  # Group Stage, Round of 32, Round of 16, QF, SF, Final
    match_date = Column(DateTime, nullable=False)
    venue = Column(String(200), nullable=True)
    city = Column(String(100), nullable=True)
    country = Column(String(50), nullable=True)  # USA, Canada, Mexico
    status = Column(String(20), default="upcoming")  # upcoming, live, completed, postponed
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    home_formation = Column(String(10), nullable=True)
    away_formation = Column(String(10), nullable=True)
    weather = Column(String(100), nullable=True)
    attendance = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    prediction = relationship("Prediction", back_populates="match", uselist=False)


class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, unique=True)
    home_win_prob = Column(Float, nullable=False)
    draw_prob = Column(Float, nullable=False)
    away_win_prob = Column(Float, nullable=False)
    predicted_home_score = Column(Integer, nullable=True)
    predicted_away_score = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=False)
    model_version = Column(String(50), default="美加墨世界杯AI预测模型 26.4")
    model_type = Column(String(30), default="baseline")  # baseline, form_weighted, monte_carlo
    factors = Column(JSON, nullable=True)  # JSON格式的因素列表
    scenario_settings = Column(JSON, nullable=True)  # 场景设置
    xg_timeline = Column(JSON, nullable=True)  # xG时间线数据
    created_at = Column(DateTime, default=datetime.utcnow)
    
    match = relationship("Match", back_populates="prediction")
