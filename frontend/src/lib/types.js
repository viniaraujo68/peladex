/**
 * @typedef {object} User
 * @property {number} id
 * @property {string} username
 */

/**
 * @typedef {object} Group
 * @property {number} id
 * @property {string} name
 * @property {string} slug
 * @property {string} description
 * @property {'public'|'private'} visibility
 * @property {string|null} share_token
 * @property {number} win_points
 * @property {number} draw_points
 * @property {number} loss_points
 * @property {boolean} track_scorers
 * @property {boolean} track_assists
 * @property {boolean} show_ratings
 * @property {number|null} default_venue_id
 * @property {string|null} default_venue_name
 * @property {number} matchday_count
 * @property {number} player_count
 */

/**
 * @typedef {object} Named
 * @property {number} id
 * @property {string} name
 */

/**
 * @typedef {object} Player
 * @property {number} id
 * @property {string} name
 * @property {boolean} active
 */

/**
 * @typedef {object} TeamMember
 * @property {number} player_id
 * @property {string} name
 */

/**
 * @typedef {object} Standing
 * @property {number} team_id
 * @property {string} name
 * @property {string} color
 * @property {number} played
 * @property {number} wins
 * @property {number} draws
 * @property {number} losses
 * @property {number} goals_for
 * @property {number} goals_against
 * @property {number} goal_diff
 * @property {number} points
 * @property {number} win_rate
 * @property {TeamMember[]} members
 */

/**
 * @typedef {object} Goal
 * @property {number} id
 * @property {number} player_id
 * @property {string} player_name
 * @property {number} team_id
 * @property {boolean} own_goal
 * @property {number|null} assist_player_id
 * @property {string|null} assist_name
 */

/**
 * @typedef {object} Match
 * @property {number} id
 * @property {number} sort_index
 * @property {number} home_team_id
 * @property {string} home_team_name
 * @property {number} away_team_id
 * @property {string} away_team_name
 * @property {number} home_score
 * @property {number} away_score
 * @property {Goal[]} goals
 */

/**
 * @typedef {object} Scorer
 * @property {number} player_id
 * @property {string} name
 * @property {number} goals
 */

/**
 * @typedef {object} Assister
 * @property {number} player_id
 * @property {string} name
 * @property {number} assists
 */

/**
 * @typedef {object} Matchday
 * @property {number} id
 * @property {string} date
 * @property {number|null} venue_id
 * @property {string|null} venue_name
 * @property {number|null} mvp_player_id
 * @property {string|null} mvp_name
 * @property {string} notes
 * @property {Standing[]} standings
 * @property {Match[]} matches
 * @property {number|null} champion_team_id
 * @property {Scorer[]} top_scorers
 * @property {Assister[]} top_assisters
 * @property {number} total_goals
 * @property {number} total_assists
 * @property {boolean} goal_mismatch
 */

/**
 * @typedef {object} MatchdayPayload
 * @property {string} date
 * @property {number|null} venue_id
 * @property {number|null} mvp_player_id
 * @property {string} notes
 * @property {{ name: string, color: string, player_ids: number[] }[]} teams
 * @property {{ home_team_index: number, away_team_index: number, home_score: number,
 *   away_score: number,
 *   goals: { player_id: number, own_goal: boolean, assist_player_id: number|null }[]
 * }[]} matches
 */

/**
 * @typedef {object} PlayerRow
 * @property {number} player_id
 * @property {string} name
 * @property {number} matchdays
 * @property {number} matches
 * @property {number} wins
 * @property {number} draws
 * @property {number} losses
 * @property {number} points
 * @property {number} win_rate
 * @property {number} goals
 * @property {number} own_goals
 * @property {number} assists
 * @property {number} contributions
 * @property {number} goals_per_matchday
 * @property {number} assists_per_matchday
 * @property {number} contributions_per_matchday
 * @property {number} goals_per_match
 * @property {number} assists_per_match
 * @property {number} contributions_per_match
 * @property {number} team_goals
 * @property {number|null} goal_share
 * @property {number|null} assist_share
 * @property {number|null} contribution_share
 * @property {number} mvp_count
 * @property {number} titles
 * @property {number} title_rate
 * @property {number} presence
 * @property {boolean} qualified
 * @property {number|null} recent_win_rate
 * @property {number} title_streak
 * @property {number} best_title_streak
 * @property {number|null} rating
 * @property {boolean} rating_provisional
 */

/**
 * @typedef {object} RatingComponent
 * @property {'results'|'team_attack'|'team_defense'|'scoring'|'mvp'} code
 * @property {number} contribution
 * @property {number} rate
 * @property {number} group_rate
 */

/**
 * @typedef {object} PlayerRating
 * @property {number} note
 * @property {boolean} provisional
 * @property {number} appearances
 * @property {RatingComponent[]} components
 */

/**
 * @typedef {object} Stats
 * @property {PlayerRow[]} ranking
 * @property {number} total_matchdays
 * @property {number} min_matchdays
 * @property {number} total_matches
 * @property {number} total_goals
 * @property {number} total_assists
 * @property {number} draw_rate
 * @property {string|null} first_date
 * @property {string|null} last_date
 */

/**
 * @typedef {object} PairLeaderRow
 * @property {number} player_a_id
 * @property {string} player_a
 * @property {number} player_b_id
 * @property {string} player_b
 * @property {number} days
 * @property {number} win_rate
 * @property {number} delta
 */

/**
 * @typedef {object} PairLeaderboard
 * @property {PairLeaderRow[]} together
 * @property {PairLeaderRow[]} apart
 * @property {number} min_days
 */

/**
 * @typedef {object} ComboResult
 * @property {number} days
 * @property {number} matches
 * @property {number} wins
 * @property {number} draws
 * @property {number} losses
 * @property {number} points
 * @property {number} goals_for
 * @property {number} goals_against
 * @property {number} win_rate
 * @property {number} baseline
 * @property {number} delta
 * @property {string[]} dates
 * @property {string[]} together_names
 * @property {string[]} against_names
 */

/**
 * @typedef {object} AssistLink
 * @property {number} assist_player_id
 * @property {string} assist_name
 * @property {number} scorer_player_id
 * @property {string} scorer_name
 * @property {number} goals
 */

/**
 * @typedef {object} AssistNetwork
 * @property {AssistLink[]} links
 * @property {number} total_assisted_goals
 */

/**
 * @typedef {object} EvolutionPoint
 * @property {string} date
 * @property {number|null} win_rate
 * @property {number|null} points
 * @property {number|null} goals
 * @property {number|null} assists
 * @property {number|null} matches
 * @property {number|null} matchdays
 */

/**
 * @typedef {object} TimelinePoint
 * @property {string} date
 * @property {number} matches
 * @property {number} goals
 * @property {number} assists
 * @property {number} goals_per_match
 * @property {number} players
 */

/**
 * @typedef {object} ScorelineRow
 * @property {string} label
 * @property {number} count
 * @property {number} share
 */

/**
 * @typedef {object} Timeline
 * @property {TimelinePoint[]} points
 * @property {ScorelineRow[]} scorelines
 * @property {number} goals_per_match
 * @property {number} goals_per_matchday
 * @property {number} assists_per_matchday
 */

/**
 * @typedef {object} EvolutionSeries
 * @property {number} player_id
 * @property {string} name
 * @property {EvolutionPoint[]} points
 */

/**
 * @typedef {object} Evolution
 * @property {string[]} dates
 * @property {EvolutionSeries[]} series
 */

/**
 * @typedef {object} PairRow
 * @property {number} player_id
 * @property {string} name
 * @property {number} days
 * @property {number} win_rate
 * @property {number} days_without
 * @property {number|null} win_rate_without
 * @property {number|null} delta
 */

/**
 * @typedef {object} PlayerMatchdayRow
 * @property {number} matchday_id
 * @property {string} date
 * @property {string} team_name
 * @property {number} position
 * @property {number} teams
 * @property {number} played
 * @property {number} wins
 * @property {number} draws
 * @property {number} losses
 * @property {number} win_rate
 * @property {number} goals
 * @property {number} assists
 * @property {boolean} champion
 * @property {boolean} mvp
 */

/**
 * @typedef {object} PlayerDetail
 * @property {number} player_id
 * @property {string} name
 * @property {PlayerRow} summary
 * @property {PlayerRating|null} rating
 * @property {PlayerMatchdayRow[]} history
 * @property {PairRow[]} partners
 * @property {PairRow[]} opponents
 * @property {number} min_days
 */

/**
 * @typedef {object} ImportIssue
 * @property {number} line
 * @property {'error'|'warning'} severity
 * @property {string} code
 * @property {string} message
 * @property {string} text
 */

/**
 * @typedef {object} ImportPreview
 * @property {boolean} ok
 * @property {ImportIssue[]} issues
 * @property {string[]} new_players
 * @property {{ date: string|null, venue: string|null, mvp: string|null, notes: string,
 *   teams: { name: string, players: string[] }[],
 *   matches: { home_team: string, away_team: string, home_score: number, away_score: number,
 *     goals: { player: string, team: string, own_goal: boolean, assist: string|null }[] }[],
 *   already_exists: boolean,
 *   standings: Record<string, any>[] }[]} matchdays
 */

/**
 * @typedef {object} PublicGroupSummary
 * @property {string} name
 * @property {string} slug
 * @property {string} description
 * @property {number} matchday_count
 * @property {number} player_count
 */

/**
 * @typedef {object} PublicGroup
 * @property {string} name
 * @property {string} slug
 * @property {string} description
 * @property {boolean} track_scorers
 * @property {boolean} track_assists
 * @property {boolean} show_ratings
 * @property {Stats} stats
 * @property {Evolution} evolution
 * @property {Matchday[]} matchdays
 */

export {};
