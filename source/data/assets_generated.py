# ==========================================
# AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
# Run asset_builder.py to update this file. 
# ==========================================
from source.engine.search_region import SearchRegion
from source.engine.target import Target, MatchResult
from .asset_library import AssetLibrary

class MainMenuElements:
    def __init__(self, registry: AssetLibrary):
        self.drive: SearchRegion = registry.get('MainMenu', 'drive')
        self.mirror_dungeon: SearchRegion = registry.get('MainMenu', 'mirror_dungeon')
        self.start: SearchRegion = registry.get('MainMenu', 'start')
        self.resume: SearchRegion = registry.get('MainMenu', 'resume')
        self.enter_invert: SearchRegion = registry.get('MainMenu', 'enter_invert')
        self.confirm_team: SearchRegion = registry.get('MainMenu', 'confirm_team')
        self.enter_bonus: SearchRegion = registry.get('MainMenu', 'enter_bonus')
        self.starlight: SearchRegion = registry.get('MainMenu', 'starlight')
        self.refuse: SearchRegion = registry.get('MainMenu', 'refuse')
        self.gift_search: SearchRegion = registry.get('MainMenu', 'gift_search')
        self.claim: SearchRegion = registry.get('MainMenu', 'claim')
        self.confirm_invert: SearchRegion = registry.get('MainMenu', 'confirm_invert')
        self.claim_invert: SearchRegion = registry.get('MainMenu', 'claim_invert')
        self.victory: SearchRegion = registry.get('MainMenu', 'victory')
        self.defeat: SearchRegion = registry.get('MainMenu', 'defeat')
        self.give_up: SearchRegion = registry.get('MainMenu', 'give_up')
        self.confirm_run: SearchRegion = registry.get('MainMenu', 'confirm_run')
        self.server_error: SearchRegion = registry.get('MainMenu', 'server_error')
        self.event_effect: SearchRegion = registry.get('MainMenu', 'event_effect')
        self.bonus: SearchRegion = registry.get('MainMenu', 'bonus')
        self.bonus_off: SearchRegion = registry.get('MainMenu', 'bonus_off')
        self.hard_bonus: SearchRegion = registry.get('MainMenu', 'hard_bonus')
        self.hard_bonus_off: SearchRegion = registry.get('MainMenu', 'hard_bonus_off')
        self.confirm_enkeph: SearchRegion = registry.get('MainMenu', 'confirm_enkeph')
        self.infinite_off: SearchRegion = registry.get('MainMenu', 'infinite_off')
        self.out_of_fuel: SearchRegion = registry.get('MainMenu', 'out_of_fuel')
        self.money_R: SearchRegion = registry.get('MainMenu', 'money_R')
        self.gifts_R: SearchRegion = registry.get('MainMenu', 'gifts_R')
        self.selected_R: SearchRegion = registry.get('MainMenu', 'selected_R')
        self.full_R: SearchRegion = registry.get('MainMenu', 'full_R')

class BattleMenuElements:
    def __init__(self, registry: AssetLibrary):
        self.to_battle: SearchRegion = registry.get('BattleMenu', 'to_battle')
        self.winrate: SearchRegion = registry.get('BattleMenu', 'winrate')
        self.pause: SearchRegion = registry.get('BattleMenu', 'pause')
        self.confirm_alt: SearchRegion = registry.get('BattleMenu', 'confirm_alt')
        self.arrow: SearchRegion = registry.get('BattleMenu', 'arrow')
        self.ego_warning: SearchRegion = registry.get('BattleMenu', 'ego_warning')
        self.ego_usage: SearchRegion = registry.get('BattleMenu', 'ego_usage')
        self.retry_stage: SearchRegion = registry.get('BattleMenu', 'retry_stage')
        self.confirm_retry: SearchRegion = registry.get('BattleMenu', 'confirm_retry')
        self.teams_R: SearchRegion = registry.get('BattleMenu', 'teams_R')
        self.current_team_R: SearchRegion = registry.get('BattleMenu', 'current_team_R')
        self.skip_yap_R: SearchRegion = registry.get('BattleMenu', 'skip_yap_R')

class EventMenuElements:
    def __init__(self, registry: AssetLibrary):
        self.text_ego: SearchRegion = registry.get('EventMenu', 'text_ego')
        self.text_new: SearchRegion = registry.get('EventMenu', 'text_new')
        self.text_lvl: SearchRegion = registry.get('EventMenu', 'text_lvl')
        self.text_win: SearchRegion = registry.get('EventMenu', 'text_win')
        self.event_skip: SearchRegion = registry.get('EventMenu', 'event_skip')
        self.check: SearchRegion = registry.get('EventMenu', 'check')
        self.choices: SearchRegion = registry.get('EventMenu', 'choices')
        self.proceed: SearchRegion = registry.get('EventMenu', 'proceed')
        self.commence: SearchRegion = registry.get('EventMenu', 'commence')
        self.continue_: SearchRegion = registry.get('EventMenu', 'continue_')
        self.commence_battle: SearchRegion = registry.get('EventMenu', 'commence_battle')
        self.probs_R: SearchRegion = registry.get('EventMenu', 'probs_R')

class GrabMenuElements:
    def __init__(self, registry: AssetLibrary):
        self.encounter_reward: SearchRegion = registry.get('GrabMenu', 'encounter_reward')
        self.confirm_ego: SearchRegion = registry.get('GrabMenu', 'confirm_ego')
        self.cancel: SearchRegion = registry.get('GrabMenu', 'cancel')
        self.ego_bin: SearchRegion = registry.get('GrabMenu', 'ego_bin')
        self.owned: SearchRegion = registry.get('GrabMenu', 'owned')
        self.confirm_card: SearchRegion = registry.get('GrabMenu', 'confirm_card')
        self.trials: SearchRegion = registry.get('GrabMenu', 'trials')
        self.adversity: SearchRegion = registry.get('GrabMenu', 'adversity')
        self.projection: SearchRegion = registry.get('GrabMenu', 'projection')
        self.select_count_R: SearchRegion = registry.get('GrabMenu', 'select_count_R')
        self.card_R: SearchRegion = registry.get('GrabMenu', 'card_R')
        self.ego_R: SearchRegion = registry.get('GrabMenu', 'ego_R')
        self.ego_tier_R: SearchRegion = registry.get('GrabMenu', 'ego_tier_R')
        self.reward_count_R: SearchRegion = registry.get('GrabMenu', 'reward_count_R')
        self.buffs_R: SearchRegion = registry.get('GrabMenu', 'buffs_R')

class MoveMenuElements:
    def __init__(self, registry: AssetLibrary):
        self.move: SearchRegion = registry.get('MoveMenu', 'move')
        self.enter: SearchRegion = registry.get('MoveMenu', 'enter')
        self.superposition: SearchRegion = registry.get('MoveMenu', 'superposition')
        self.secret_encounter: SearchRegion = registry.get('MoveMenu', 'secret_encounter')
        self.skip_encounter: SearchRegion = registry.get('MoveMenu', 'skip_encounter')
        self.directions_R: SearchRegion = registry.get('MoveMenu', 'directions_R')

class PackMenuElements:
    def __init__(self, registry: AssetLibrary):
        self.pack_choice: SearchRegion = registry.get('PackMenu', 'pack_choice')
        self.pack_pull: SearchRegion = registry.get('PackMenu', 'pack_pull')
        self.hard_difficulty: SearchRegion = registry.get('PackMenu', 'hard_difficulty')
        self.sift_search_R: SearchRegion = registry.get('PackMenu', 'sift_search_R')
        self.lvl_R: SearchRegion = registry.get('PackMenu', 'lvl_R')

class ShopMenuElements:
    def __init__(self, registry: AssetLibrary):
        self.shop: SearchRegion = registry.get('ShopMenu', 'shop')
        self.supershop: SearchRegion = registry.get('ShopMenu', 'supershop')
        self.sell: SearchRegion = registry.get('ShopMenu', 'sell')
        self.purchase: SearchRegion = registry.get('ShopMenu', 'purchase')
        self.power: SearchRegion = registry.get('ShopMenu', 'power')
        self.confirm_fuse: SearchRegion = registry.get('ShopMenu', 'confirm_fuse')
        self.confirm_sell: SearchRegion = registry.get('ShopMenu', 'confirm_sell')
        self.keyword_sel: SearchRegion = registry.get('ShopMenu', 'keyword_sel')
        self.keyword_ref: SearchRegion = registry.get('ShopMenu', 'keyword_ref')
        self.fuse: SearchRegion = registry.get('ShopMenu', 'fuse')
        self.scroll: SearchRegion = registry.get('ShopMenu', 'scroll')
        self.scroll_low: SearchRegion = registry.get('ShopMenu', 'scroll_low')
        self.wishmaking: SearchRegion = registry.get('ShopMenu', 'wishmaking')
        self.replace: SearchRegion = registry.get('ShopMenu', 'replace')
        self.purchased: SearchRegion = registry.get('ShopMenu', 'purchased')
        self.no_hp: SearchRegion = registry.get('ShopMenu', 'no_hp')
        self.return_: SearchRegion = registry.get('ShopMenu', 'return_')
        self.select: SearchRegion = registry.get('ShopMenu', 'select')
        self.buy_s3_R: SearchRegion = registry.get('ShopMenu', 'buy_s3_R')
        self.buy_shelf_R: SearchRegion = registry.get('ShopMenu', 'buy_shelf_R')
        self.fuse_shelf_R: SearchRegion = registry.get('ShopMenu', 'fuse_shelf_R')
        self.fuse_shelf_low_R: SearchRegion = registry.get('ShopMenu', 'fuse_shelf_low_R')
        self.affinity_R: SearchRegion = registry.get('ShopMenu', 'affinity_R')
        self.revenue_R: SearchRegion = registry.get('ShopMenu', 'revenue_R')
        self.forecast_R: SearchRegion = registry.get('ShopMenu', 'forecast_R')

class UtilsMenuElements:
    def __init__(self, registry: AssetLibrary):
        self.all_dead: SearchRegion = registry.get('UtilsMenu', 'all_dead')
        self.forfeit: SearchRegion = registry.get('UtilsMenu', 'forfeit')
        self.connecting: SearchRegion = registry.get('UtilsMenu', 'connecting')
        self.loading: SearchRegion = registry.get('UtilsMenu', 'loading')

class LuxMenuElements:
    def __init__(self, registry: AssetLibrary):
        self.lux: SearchRegion = registry.get('LuxMenu', 'lux')
        self.exp: SearchRegion = registry.get('LuxMenu', 'exp')
        self.window: SearchRegion = registry.get('LuxMenu', 'window')
        self.settings: SearchRegion = registry.get('LuxMenu', 'settings')
        self.pass_missions: SearchRegion = registry.get('LuxMenu', 'pass_missions')
        self.daily: SearchRegion = registry.get('LuxMenu', 'daily')
        self.collect: SearchRegion = registry.get('LuxMenu', 'collect')
        self.pick_R: SearchRegion = registry.get('LuxMenu', 'pick_R')
        self.thd_R: SearchRegion = registry.get('LuxMenu', 'thd_R')

class UIDatabase:
    def __init__(self, registry: AssetLibrary):
        self.point = Target(None, MatchResult(), registry.controller)
        self.MainMenu = MainMenuElements(registry)
        self.BattleMenu = BattleMenuElements(registry)
        self.EventMenu = EventMenuElements(registry)
        self.GrabMenu = GrabMenuElements(registry)
        self.MoveMenu = MoveMenuElements(registry)
        self.PackMenu = PackMenuElements(registry)
        self.ShopMenu = ShopMenuElements(registry)
        self.UtilsMenu = UtilsMenuElements(registry)
        self.LuxMenu = LuxMenuElements(registry)