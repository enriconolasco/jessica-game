"""Abertura da fase diurna pelos adaptadores, usando a ordem do motor."""
from . import peoples
from .turn import day_order, end_day, start_player_day


def open_day(state):
    pending = next((p for p in state.players if p.city.is_alive()
                    and p.people == peoples.PEOPLE_GNOMOS and p.bets_need_realocacao), None)
    if pending is not None:
        state.active_player_id = pending.id
        return
    order = day_order(state)
    if order:
        state.active_player_id = order[0]
        start_player_day(state, order[0])
    else:
        state.active_player_id = None
        end_day(state)
        from . import night_actions
        if not night_actions.blockers(state):
            night_actions.prepare(state)
