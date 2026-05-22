import time
import logging

import source.engine as eg
import source.game_states as st
from source.data import UIDatabase, AssetLibrary, DungeonManager, TeamConfig, RuntimeState, StuckMonitor, ASSETS_DIR
from source_app.data import BotConfig


def main_loop(ctrl: eg.InputController, ui: UIDatabase, team: TeamConfig):
    st.dungeon_start(ctrl, ui, team)
    run_state = RuntimeState()
    monitor = StuckMonitor(timeout=30.0, max_errors=20)
    run_state.reset_dungeon()

    while True:
        activity_detected = False

        try:
            st.resolve_server_error(ctrl, ui)
            st.resolve_event_effect(ctrl, ui)
            st.resolve_extreme_popup(ctrl, ui, team)

            actions = [
                st.handle_packs(ctrl, ui, team, run_state),
                st.handle_move(),
                st.handle_fight(),
                st.handle_event(ctrl, ui, team),
                st.grab_EGO(),
                st.confirm(),
                st.get_adversity(),
                st.grab_card(),
                st.handle_shop()
            ]
            
            if any(actions):
                activity_detected = False
        
        except RuntimeError:
            st.handle_fuckup(ctrl, ui)
            monitor.report_error()
        except eg.PauseException as msg:
            st.pause(ctrl, str(msg))

        if activity_detected:
            monitor.report_progress()
        elif st.dungeon_start(ctrl, ui, team):
            run_state.reset_dungeon()
        elif st.dungeon_fail(ctrl, ui):
            return False
        elif st.dungeon_end(ctrl, ui, team):
            return True
        elif monitor.is_stuck():
            logging.warning("No familiar UI detected for 30s, attempting recovery...")
            st.handle_fuckup(ctrl, ui)
            monitor.report_error()

        time.sleep(0.2)


def execute_me(config: BotConfig, event: eg.BotEvents):
    print("Switch to Limbus Window")
    st.countdown(10)
    logging.info('Script started')
    try:
        win = eg.Window.from_system(config.window_name, event)
        ctrl = eg.InputController(win)
        pth = eg.PathResolver(ASSETS_DIR)
        reg = AssetLibrary(ctrl, pth)
        ui = UIDatabase(reg)

        lux_keys = [key for key in config.teams_selections.keys() if key >= 7]
        if lux_keys:
            print("Entering Lux!")
            st.grind_lux(config.exp_lux_count, config.thread_lux_count, config.teams_selections)
            if event and any(k < 7 for k in config.teams_selections.keys()):
                event.request_lux_hide.emit()
            
        md_manager = DungeonManager(config)
        
        if md_manager.has_runs():
            print("Entering MD!")
            
            for run_index, active_team in md_manager.generate_runs():
                logging.info(f'Iteration {run_index}')
                logging.info(f'Team: {active_team.team_keywords[0]}')
                logging.info(f'Difficulty: {config.difficulty}')
                
                is_completed = False
                while not is_completed:
                    is_completed = main_loop(ctrl, ui, active_team)
                    st.check_enkephalin()

        raise eg.StopExecution

    except eg.StopExecution:
        pass
    except Exception as e:
        raise e
    finally:
        if config.altf4:
            st.close_limbus(ctrl)
        elif event:
            event.request_stop_ui.emit()