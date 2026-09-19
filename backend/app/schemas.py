from datetime import date

from pydantic import BaseModel, Field

MAX_SCORE = 99


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=6, max_length=200)


class UserOut(BaseModel):
    id: int
    username: str


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=200)


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = ""
    visibility: str = "private"


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    visibility: str | None = None
    win_points: int | None = Field(default=None, ge=0, le=10)
    draw_points: int | None = Field(default=None, ge=0, le=10)
    loss_points: int | None = Field(default=None, ge=0, le=10)


class GroupOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    visibility: str
    share_token: str | None
    win_points: int
    draw_points: int
    loss_points: int
    matchday_count: int = 0
    player_count: int = 0


class NamedCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class NamedOut(BaseModel):
    id: int
    name: str


class PlayerOut(BaseModel):
    id: int
    name: str
    active: bool


class PlayerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    active: bool | None = None


class GoalIn(BaseModel):
    player_id: int
    own_goal: bool = False


class MatchIn(BaseModel):
    home_team_index: int = Field(ge=0)
    away_team_index: int = Field(ge=0)
    home_score: int = Field(default=0, ge=0, le=MAX_SCORE)
    away_score: int = Field(default=0, ge=0, le=MAX_SCORE)
    goals: list[GoalIn] = []


class TeamIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    color: str = ""
    player_ids: list[int] = []


class MatchdayCreate(BaseModel):
    date: date
    venue_id: int | None = None
    mvp_player_id: int | None = None
    notes: str = ""
    teams: list[TeamIn] = []
    matches: list[MatchIn] = []


class GoalOut(BaseModel):
    id: int
    player_id: int
    player_name: str
    team_id: int
    own_goal: bool


class MatchOut(BaseModel):
    id: int
    sort_index: int
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str
    home_score: int
    away_score: int
    goals: list[GoalOut]


class TeamMemberOut(BaseModel):
    player_id: int
    name: str


class TeamStandingOut(BaseModel):
    team_id: int
    name: str
    color: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_diff: int
    points: int
    win_rate: float
    members: list[TeamMemberOut]


class ScorerOut(BaseModel):
    player_id: int
    name: str
    goals: int


class MatchdayOut(BaseModel):
    id: int
    date: date
    venue_id: int | None
    venue_name: str | None
    mvp_player_id: int | None
    mvp_name: str | None
    notes: str
    standings: list[TeamStandingOut]
    matches: list[MatchOut]
    champion_team_id: int | None
    top_scorers: list[ScorerOut]
    total_goals: int
    goal_mismatch: bool


class PlayerRow(BaseModel):
    player_id: int
    name: str
    matchdays: int
    matches: int
    wins: int
    draws: int
    losses: int
    points: int
    win_rate: float
    goals: int
    own_goals: int
    goals_per_matchday: float
    mvp_count: int
    titles: int
    title_rate: float


class Record(BaseModel):
    code: str
    player_name: str | None
    value: float | None
    detail: str = ""
    matchday_date: date | None = None


class StatsOut(BaseModel):
    ranking: list[PlayerRow]
    records: list[Record]
    total_matchdays: int
    total_matches: int
    total_goals: int


class EvolutionPoint(BaseModel):
    date: date
    win_rate: float | None
    points: int | None


class EvolutionSeries(BaseModel):
    player_id: int
    name: str
    points: list[EvolutionPoint]


class EvolutionOut(BaseModel):
    dates: list[date]
    series: list[EvolutionSeries]


class PairRow(BaseModel):
    player_id: int
    name: str
    days: int
    win_rate: float
    delta: float


class PlayerMatchdayRow(BaseModel):
    matchday_id: int
    date: date
    team_name: str
    position: int
    teams: int
    played: int
    wins: int
    draws: int
    losses: int
    win_rate: float
    goals: int
    champion: bool
    mvp: bool


class PlayerDetailOut(BaseModel):
    player_id: int
    name: str
    summary: PlayerRow
    history: list[PlayerMatchdayRow]
    partners: list[PairRow]
    opponents: list[PairRow]
    min_days: int


class ImportIssueOut(BaseModel):
    line: int
    severity: str
    code: str
    message: str
    text: str = ""


class ImportGoalPreview(BaseModel):
    player: str
    team: str
    own_goal: bool


class ImportMatchPreview(BaseModel):
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    goals: list[ImportGoalPreview]


class ImportTeamPreview(BaseModel):
    name: str
    players: list[str]


class ImportMatchdayPreview(BaseModel):
    date: date | None
    venue: str | None
    mvp: str | None
    notes: str
    teams: list[ImportTeamPreview]
    matches: list[ImportMatchPreview]
    already_exists: bool
    standings: list[dict] = []


class ImportPreviewIn(BaseModel):
    text: str = Field(max_length=200_000)


class ImportPreviewOut(BaseModel):
    ok: bool
    matchdays: list[ImportMatchdayPreview]
    issues: list[ImportIssueOut]
    new_players: list[str]


class ImportCommitIn(BaseModel):
    text: str = Field(max_length=200_000)
    create_missing_players: bool = True
    replace_existing: bool = False


class ImportCommitOut(BaseModel):
    created_matchday_ids: list[int]
    replaced: int
    created_players: list[str]
    issues: list[ImportIssueOut]


class PublicGroupSummary(BaseModel):
    name: str
    slug: str
    description: str
    matchday_count: int
    player_count: int


class PublicGroupOut(BaseModel):
    name: str
    slug: str
    description: str
    stats: StatsOut
    evolution: EvolutionOut
    matchdays: list[MatchdayOut]
