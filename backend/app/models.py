from datetime import date, datetime, timezone

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    created_at: datetime = Field(default_factory=utcnow)


class UserSession(SQLModel, table=True):
    __tablename__ = "session"

    token_hash: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    expires_at: datetime
    created_at: datetime = Field(default_factory=utcnow)


class GroupOwner(SQLModel, table=True):
    group_id: int = Field(foreign_key="group.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)


class Group(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    slug: str = Field(unique=True, index=True)
    description: str = ""
    visibility: str = "private"
    share_token: str | None = Field(default=None, index=True)
    win_points: int = 3
    draw_points: int = 1
    loss_points: int = 0
    track_scorers: bool = True
    track_assists: bool = False
    created_at: datetime = Field(default_factory=utcnow)

    players: list["Player"] = Relationship(back_populates="group")
    venues: list["Venue"] = Relationship(back_populates="group")
    matchdays: list["Matchday"] = Relationship(back_populates="group")


class Player(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("group_id", "name", name="uq_player_group_name"),)
    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.id", index=True)
    name: str
    active: bool = True
    created_at: datetime = Field(default_factory=utcnow)

    group: Group | None = Relationship(back_populates="players")


class Venue(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("group_id", "name", name="uq_venue_group_name"),)
    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.id", index=True)
    name: str

    group: Group | None = Relationship(back_populates="venues")


class Matchday(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    group_id: int = Field(foreign_key="group.id", index=True)
    date: date
    venue_id: int | None = Field(default=None, foreign_key="venue.id")
    mvp_player_id: int | None = Field(default=None, foreign_key="player.id")
    notes: str = ""
    created_at: datetime = Field(default_factory=utcnow)
    deleted_at: datetime | None = None

    group: Group | None = Relationship(back_populates="matchdays")
    teams: list["Team"] = Relationship(
        back_populates="matchday",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    matches: list["Match"] = Relationship(
        back_populates="matchday",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    matchday_id: int = Field(foreign_key="matchday.id", index=True)
    name: str
    color: str = ""
    sort_index: int = 0

    matchday: Matchday | None = Relationship(back_populates="teams")
    members: list["TeamMember"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class TeamMember(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    player_id: int = Field(foreign_key="player.id", index=True)

    team: Team | None = Relationship(back_populates="members")


class Match(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    matchday_id: int = Field(foreign_key="matchday.id", index=True)
    sort_index: int = 0
    home_team_id: int = Field(foreign_key="team.id", index=True)
    away_team_id: int = Field(foreign_key="team.id", index=True)
    home_score: int = 0
    away_score: int = 0

    matchday: Matchday | None = Relationship(back_populates="matches")
    goals: list["Goal"] = Relationship(
        back_populates="match",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Goal(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    match_id: int = Field(foreign_key="match.id", index=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    team_id: int = Field(foreign_key="team.id", index=True)
    own_goal: bool = False
    assist_player_id: int | None = Field(default=None, foreign_key="player.id", index=True)

    match: Match | None = Relationship(back_populates="goals")
