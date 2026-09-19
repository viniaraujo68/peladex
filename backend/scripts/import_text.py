import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select  # noqa: E402

from app import models, parser, schemas, writes  # noqa: E402
from app.db import engine, init_db  # noqa: E402

SOURCE_FILE = "peladas.txt"
GROUP_SLUG = "pelada-da-quinta"
CREATE_MISSING_PLAYERS = True
REPLACE_EXISTING = False
APPLY = False


def main() -> None:
    text = Path(SOURCE_FILE).read_text(encoding="utf-8")
    init_db()

    with Session(engine) as db:
        group = db.exec(select(models.Group).where(models.Group.slug == GROUP_SLUG)).first()
        if group is None:
            sys.exit(f"Nenhuma pelada com slug '{GROUP_SLUG}'.")

        known = list(db.exec(
            select(models.Player.name).where(models.Player.group_id == group.id)
        ).all())
        result = parser.parse(text, known)

        for issue in result.issues:
            print(f"  [{issue.severity:<7}] linha {issue.line}: {issue.message}")

        print(f"\n{len(result.matchdays)} dia(s) lido(s), {len(result.new_players)} jogador(es) novo(s).")
        for day in result.matchdays:
            existing = db.exec(select(models.Matchday).where(
                models.Matchday.group_id == group.id,
                models.Matchday.date == day.date,
                models.Matchday.deleted_at == None,  # noqa: E711
            )).first()
            mark = "substitui" if existing else "cria"
            print(f"  {day.date}  {mark}  {len(day.teams)} times, {len(day.matches)} partidas")

        if not result.ok:
            sys.exit("\nO texto tem erros. Corrija antes de aplicar.")
        if result.new_players and not CREATE_MISSING_PLAYERS:
            sys.exit("\nHá jogadores novos e CREATE_MISSING_PLAYERS está desligado.")
        if not APPLY:
            print("\nAPPLY = False — nada foi gravado.")
            return

        players = {
            parser.normalize(p.name): p
            for p in db.exec(
                select(models.Player).where(models.Player.group_id == group.id)
            ).all()
        }
        for name in result.new_players:
            key = parser.normalize(name)
            if key in players:
                continue
            player = models.Player(group_id=group.id, name=name)
            db.add(player)
            db.flush()
            players[key] = player

        venues = {
            parser.normalize(v.name): v
            for v in db.exec(
                select(models.Venue).where(models.Venue.group_id == group.id)
            ).all()
        }

        written = 0
        for day in result.matchdays:
            venue_id = None
            if day.venue:
                key = parser.normalize(day.venue)
                venue = venues.get(key)
                if venue is None:
                    venue = models.Venue(group_id=group.id, name=day.venue)
                    db.add(venue)
                    db.flush()
                    venues[key] = venue
                venue_id = venue.id

            mvp = players.get(parser.normalize(day.mvp)) if day.mvp else None
            team_index = {team.name: index for index, team in enumerate(day.teams)}
            payload = schemas.MatchdayCreate(
                date=day.date,
                venue_id=venue_id,
                mvp_player_id=mvp.id if mvp else None,
                notes=day.notes,
                teams=[
                    schemas.TeamIn(
                        name=team.name,
                        player_ids=[players[parser.normalize(n)].id for n in team.players],
                    )
                    for team in day.teams
                ],
                matches=[
                    schemas.MatchIn(
                        home_team_index=team_index[match.home_team],
                        away_team_index=team_index[match.away_team],
                        home_score=match.home_score,
                        away_score=match.away_score,
                        goals=[
                            schemas.GoalIn(
                                player_id=players[parser.normalize(g.player)].id,
                                own_goal=g.own_goal,
                            )
                            for g in match.goals
                        ],
                    )
                    for match in day.matches
                ],
            )
            writes.validate_payload(db, group.id, payload)

            existing = db.exec(select(models.Matchday).where(
                models.Matchday.group_id == group.id,
                models.Matchday.date == day.date,
                models.Matchday.deleted_at == None,  # noqa: E711
            )).first()
            if existing is not None:
                if not REPLACE_EXISTING:
                    print(f"  pulando {day.date}: já existe e REPLACE_EXISTING está desligado")
                    continue
                writes.clear_children(db, existing.id)
                db.expire(existing)
                writes.apply_payload(db, existing, payload)
            else:
                writes.apply_payload(db, models.Matchday(group_id=group.id, date=day.date), payload)
            written += 1

        db.commit()
        print(f"\n{written} dia(s) gravado(s) em '{group.name}'.")


if __name__ == "__main__":
    main()
