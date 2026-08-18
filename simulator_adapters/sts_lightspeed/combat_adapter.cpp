#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <nlohmann/json.hpp>
#include <pybind11/pybind11.h>

#include "combat/BattleContext.h"
#include "constants/Cards.h"
#include "constants/MonsterIds.h"
#include "constants/MonsterStatusEffects.h"
#include "constants/PlayerStatusEffects.h"
#include "constants/Potions.h"
#include "constants/Relics.h"
#include "game/Game.h"
#include "game/GameContext.h"
#include "sim/search/Action.h"
#include "sim/search/SimpleAgent.h"

namespace py = pybind11;
using json = nlohmann::json;

#define STS_COMBAT_ADAPTER_STRINGIFY_INNER(value) #value
#define STS_COMBAT_ADAPTER_STRINGIFY(value) STS_COMBAT_ADAPTER_STRINGIFY_INNER(value)

namespace {

constexpr const char *ADAPTER_API_VERSION = "sts-lightspeed-combat-adapter-v3";
constexpr const char *STATE_SCHEMA_VERSION = "sts-lightspeed-combat-state-v3";
constexpr const char *SOURCE_TYPE = "sts_lightspeed_combat_simulation";
constexpr const char *BASELINE_POLICY = "native_simple_agent_v1";
constexpr int RL_ACTION_DIM = 133;
constexpr int RL_TARGET_SLOTS = 6;
constexpr int RL_POTION_OFFSET = 60;
constexpr int RL_END_TURN_ACTION = 90;
constexpr int MAX_CARD_SELECT_SETTLEMENTS = 8;
constexpr int MAX_BATTLE_INDEX = 63;
constexpr int MAX_OUT_OF_COMBAT_ACTIONS = 10000;
constexpr int MAX_PRIOR_BATTLE_ACTIONS = 5000;

constexpr std::array<sts::CardSelectTask, 14> SUPPORTED_CARD_SELECT_TASKS = {
    sts::CardSelectTask::ARMAMENTS,
    sts::CardSelectTask::CODEX,
    sts::CardSelectTask::DISCOVERY,
    sts::CardSelectTask::DUAL_WIELD,
    sts::CardSelectTask::EXHAUST_ONE,
    sts::CardSelectTask::EXHAUST_MANY,
    sts::CardSelectTask::EXHUME,
    sts::CardSelectTask::FORETHOUGHT,
    sts::CardSelectTask::GAMBLE,
    sts::CardSelectTask::HEADBUTT,
    sts::CardSelectTask::LIQUID_MEMORIES_POTION,
    sts::CardSelectTask::SECRET_TECHNIQUE,
    sts::CardSelectTask::SECRET_WEAPON,
    sts::CardSelectTask::WARCRY,
};

std::string cardSelectTaskName(sts::CardSelectTask task) {
    const auto index = static_cast<std::size_t>(task);
    const auto count = sizeof(sts::cardSelectTaskStrings) /
                       sizeof(sts::cardSelectTaskStrings[0]);
    return index < count ? sts::cardSelectTaskStrings[index] :
                           "NATIVE_CARD_SELECT_TASK_" + std::to_string(index);
}

bool isSupportedCardSelectTask(sts::CardSelectTask task) {
    return std::find(
        SUPPORTED_CARD_SELECT_TASKS.begin(),
        SUPPORTED_CARD_SELECT_TASKS.end(),
        task) != SUPPORTED_CARD_SELECT_TASKS.end();
}

json supportedCardSelectTasksJson() {
    json result = json::array();
    for (const auto task : SUPPORTED_CARD_SELECT_TASKS) {
        result.push_back(cardSelectTaskName(task));
    }
    return result;
}

const char *battleOutcomeName(sts::Outcome outcome) {
    switch (outcome) {
        case sts::Outcome::PLAYER_VICTORY: return "player_victory";
        case sts::Outcome::PLAYER_LOSS: return "player_loss";
        default: return "undecided";
    }
}

std::string inputStateName(sts::InputState state) {
    switch (state) {
        case sts::InputState::PLAYER_NORMAL: return "PLAYER_NORMAL";
        case sts::InputState::CARD_SELECT: return "CARD_SELECT";
        case sts::InputState::EXECUTING_ACTIONS: return "EXECUTING_ACTIONS";
        case sts::InputState::CHOOSE_STANCE_ACTION: return "CHOOSE_STANCE_ACTION";
        case sts::InputState::CHOOSE_TOOLBOX_COLORLESS_CARD:
            return "CHOOSE_TOOLBOX_COLORLESS_CARD";
        case sts::InputState::CHOOSE_EXHAUST_POTION_CARDS:
            return "CHOOSE_EXHAUST_POTION_CARDS";
        case sts::InputState::CHOOSE_GAMBLING_CARDS: return "CHOOSE_GAMBLING_CARDS";
        case sts::InputState::CHOOSE_ENTROPIC_BREW_DISCARD_POTIONS:
            return "CHOOSE_ENTROPIC_BREW_DISCARD_POTIONS";
        case sts::InputState::CHOOSE_DISCARD_CARDS: return "CHOOSE_DISCARD_CARDS";
        case sts::InputState::SCRY: return "SCRY";
        default:
            return "NATIVE_INPUT_STATE_" + std::to_string(static_cast<int>(state));
    }
}

std::string encounterName(sts::MonsterEncounter encounter) {
    const auto index = static_cast<std::size_t>(encounter);
    const auto count = sizeof(sts::monsterEncounterEnumNames) /
                       sizeof(sts::monsterEncounterEnumNames[0]);
    return index < count ? sts::monsterEncounterEnumNames[index] : "INVALID";
}

int playerPower(const sts::Player &player, PlayerStatus status) {
    return player.getStatusRuntime(status);
}

json playerPowers(const sts::Player &player) {
    return {
        {"Artifact", playerPower(player, PS::ARTIFACT)},
        {"Confused", playerPower(player, PS::CONFUSED)},
        {"Dexterity", playerPower(player, PS::DEXTERITY)},
        {"Frail", playerPower(player, PS::FRAIL)},
        {"Intangible", playerPower(player, PS::INTANGIBLE)},
        {"Mantra", playerPower(player, PS::MANTRA)},
        {"Metallicize", playerPower(player, PS::METALLICIZE)},
        {"PlatedArmor", playerPower(player, PS::PLATED_ARMOR)},
        {"Poison", 0},
        {"Regen", playerPower(player, PS::REGEN)},
        {"Ritual", playerPower(player, PS::RITUAL)},
        {"Strength", playerPower(player, PS::STRENGTH)},
        {"Thorns", playerPower(player, PS::THORNS)},
        {"Vigor", playerPower(player, PS::VIGOR)},
        {"Vulnerable", playerPower(player, PS::VULNERABLE)},
        {"Weak", playerPower(player, PS::WEAK)},
    };
}

int monsterPower(const sts::Monster &monster, sts::MonsterStatus status) {
    return monster.getStatusInternal(status);
}

json monsterPowers(const sts::Monster &monster) {
    return {
        {"Artifact", monsterPower(monster, sts::MS::ARTIFACT)},
        {"Confused", 0},
        {"Dexterity", 0},
        {"Frail", 0},
        {"Intangible", monsterPower(monster, sts::MS::INTANGIBLE)},
        {"Mantra", 0},
        {"Metallicize", monsterPower(monster, sts::MS::METALLICIZE)},
        {"PlatedArmor", monsterPower(monster, sts::MS::PLATED_ARMOR)},
        {"Poison", monsterPower(monster, sts::MS::POISON)},
        {"Regen", monsterPower(monster, sts::MS::REGEN)},
        {"Ritual", monsterPower(monster, sts::MS::RITUAL)},
        {"Strength", monsterPower(monster, sts::MS::STRENGTH)},
        {"Thorns", monsterPower(monster, sts::MS::THORNS)},
        {"Vigor", 0},
        {"Vulnerable", monsterPower(monster, sts::MS::VULNERABLE)},
        {"Weak", monsterPower(monster, sts::MS::WEAK)},
    };
}

struct Candidate {
    std::string actionId;
    std::string kind;
    int rlActionIndex = -1;
    int sourceSlot = -1;
    int targetSlot = 0;
    int nativeTarget = -1;
    std::uint32_t bits = 0;

    json toJson() const {
        return {
            {"action_id", actionId},
            {"available", true},
            {"kind", kind},
            {"native_target", nativeTarget},
            {"rl_action_index", rlActionIndex},
            {"source_slot", sourceSlot},
            {"target_slot", targetSlot},
        };
    }
};

class CombatEnvironment {
public:
    CombatEnvironment(std::uint64_t seed, int ascension, int battleIndex)
        : gc_(sts::CharacterClass::IRONCLAD, seed, ascension),
          requestedBattleIndex_(battleIndex) {
        if (ascension < 0 || ascension > 20) {
            throw std::invalid_argument("ascension must be in range 0..20");
        }
        if (battleIndex < 0 || battleIndex > MAX_BATTLE_INDEX) {
            throw std::invalid_argument(
                "battle_index must be in range 0.." +
                std::to_string(MAX_BATTLE_INDEX));
        }
        gc_.info.encounter = sts::MonsterEncounter::INVALID;
        configureAgent();
        advanceToBattle();
    }

    CombatEnvironment(const CombatEnvironment &other)
        : gc_(other.gc_), battle_(other.battle_), baselineAgent_(other.baselineAgent_),
          decisionCount_(other.decisionCount_),
          lastCardSelectSettlementCount_(other.lastCardSelectSettlementCount_),
          lastCardSelectTasks_(other.lastCardSelectTasks_),
          cardSelectSettlementFailureReason_(other.cardSelectSettlementFailureReason_),
          requestedBattleIndex_(other.requestedBattleIndex_),
          reachedBattleIndex_(other.reachedBattleIndex_) {
        if (other.gc_.map) {
            gc_.map = std::make_shared<sts::Map>(*other.gc_.map);
        }
        configureAgent();
    }

    std::unique_ptr<CombatEnvironment> clone() const {
        return std::make_unique<CombatEnvironment>(*this);
    }

    bool terminal() const {
        return battle_.outcome != sts::Outcome::UNDECIDED;
    }

    bool supported() const {
        return !terminal() && battle_.inputState == sts::InputState::PLAYER_NORMAL;
    }

    std::string unsupportedReason() const {
        if (terminal() || supported()) {
            return "";
        }
        if (!cardSelectSettlementFailureReason_.empty()) {
            return cardSelectSettlementFailureReason_;
        }
        return "unsupported_input_state:" + inputStateName(battle_.inputState);
    }

    json cardSelectSettlementJson() const {
        return {
            {"count", lastCardSelectSettlementCount_},
            {"tasks", lastCardSelectTasks_},
        };
    }

    json progressionJson() const {
        return {
            {"act", gc_.act},
            {"baseline_policy", BASELINE_POLICY},
            {"deck_size", gc_.deck.size()},
            {"encounter", encounterName(battle_.encounter)},
            {"floor", battle_.floorNum},
            {"player_current_hp", battle_.player.curHp},
            {"player_max_hp", battle_.player.maxHp},
            {"reached_battle_index", reachedBattleIndex_},
            {"relic_count", gc_.relics.relics.size()},
            {"requested_battle_index", requestedBattleIndex_},
        };
    }

    std::string statusJson() const {
        return json({
            {"card_select_settlement", cardSelectSettlementJson()},
            {"decision_count", decisionCount_},
            {"input_state", inputStateName(battle_.inputState)},
            {"outcome", battleOutcomeName(battle_.outcome)},
            {"progression", progressionJson()},
            {"supported", supported()},
            {"terminal", terminal()},
            {"unsupported_reason", unsupportedReason()},
        }).dump();
    }

    std::string snapshotJson() const {
        json state = {
            {"act", gc_.act},
            {"ascension", battle_.ascension},
            {"battle_index", reachedBattleIndex_},
            {"decision_count", decisionCount_},
            {"deck_size", gc_.deck.size()},
            {"encounter", encounterName(battle_.encounter)},
            {"floor", battle_.floorNum},
            {"input_state", inputStateName(battle_.inputState)},
            {"outcome", battleOutcomeName(battle_.outcome)},
            {"seed", std::to_string(battle_.seed)},
            {"relic_count", gc_.relics.relics.size()},
            {"turn", battle_.turn},
        };

        state["player"] = {
            {"block", battle_.player.block},
            {"character", "IRONCLAD"},
            {"current_hp", battle_.player.curHp},
            {"energy", battle_.player.energy},
            {"max_hp", battle_.player.maxHp},
            {"powers", playerPowers(battle_.player)},
        };

        state["piles"] = {
            {"discard", battle_.cards.discardPile.size()},
            {"draw", battle_.cards.drawPile.size()},
            {"exhaust", battle_.cards.exhaustPile.size()},
        };

        state["hand"] = json::array();
        for (int slot = 0; slot < battle_.cards.cardsInHand; ++slot) {
            const auto &card = battle_.cards.hand[slot];
            state["hand"].push_back({
                {"card_type", sts::cardTypeStrings[static_cast<int>(card.getType())]},
                {"cost", card.cost},
                {"cost_for_turn", card.costForTurn},
                {"id", sts::getCardEnumName(card.getId())},
                {"name", card.getName()},
                {"playable", card.canUseOnAnyTarget(battle_)},
                {"requires_target", card.requiresTarget()},
                {"slot", slot},
                {"upgrade_count", card.getUpgradeCount()},
                {"upgraded", card.isUpgraded()},
            });
        }

        state["monsters"] = json::array();
        for (int slot = 0; slot < battle_.monsters.monsterCount; ++slot) {
            const auto &monster = battle_.monsters.arr[slot];
            const auto damage = monster.getMoveBaseDamage(battle_);
            const int adjustedDamage = damage.damage > 0
                ? monster.calculateDamageToPlayer(battle_, damage.damage)
                : 0;
            state["monsters"].push_back({
                {"block", monster.block},
                {"current_hp", monster.curHp},
                {"half_dead", monster.halfDead},
                {"id", sts::monsterIdStrings[static_cast<int>(monster.id)]},
                {"intent", monster.isAttacking() ? "ATTACK" : "UNKNOWN"},
                {"is_gone", monster.isDeadOrEscaped()},
                {"max_hp", monster.maxHp},
                {"move_adjusted_damage", adjustedDamage},
                {"move_hits", damage.attackCount},
                {"name", monster.getName()},
                {"native_slot", slot},
                {"powers", monsterPowers(monster)},
                {"targetable", monster.isTargetable()},
            });
        }

        state["potions"] = json::array();
        for (int slot = 0; slot < std::min(battle_.potionCapacity, 5); ++slot) {
            const auto potion = battle_.potions[slot];
            state["potions"].push_back({
                {"empty", potion == sts::Potion::EMPTY_POTION_SLOT},
                {"id", sts::potionIds[static_cast<int>(potion)]},
                {"name", sts::getPotionName(potion)},
                {"requires_target", sts::potionRequiresTarget(potion)},
                {"slot", slot},
            });
        }

        state["relics"] = json::array();
        for (int slot = 0; slot < gc_.relics.relics.size(); ++slot) {
            const auto &relic = gc_.relics.relics[slot];
            state["relics"].push_back({
                {"id", sts::relicIds[static_cast<int>(relic.id)]},
                {"name", sts::getRelicName(relic.id)},
                {"slot", slot},
            });
        }

        return json({
            {"adapter_api_version", ADAPTER_API_VERSION},
            {"card_select_settlement", cardSelectSettlementJson()},
            {"progression", progressionJson()},
            {"rl_action_dim", RL_ACTION_DIM},
            {"schema_version", STATE_SCHEMA_VERSION},
            {"source_type", SOURCE_TYPE},
            {"state", state},
            {"supported", supported()},
            {"terminal", terminal()},
            {"unsupported_reason", unsupportedReason()},
        }).dump();
    }

    std::string legalActionsJson() const {
        json result = json::array();
        for (const auto &candidate : legalCandidates()) {
            result.push_back(candidate.toJson());
        }
        return result.dump();
    }

    void step(const std::string &actionId) {
        if (terminal()) {
            throw std::runtime_error("cannot act in a terminal combat state");
        }
        if (!supported()) {
            throw std::runtime_error(unsupportedReason());
        }
        const auto candidates = legalCandidates();
        const auto it = std::find_if(candidates.begin(), candidates.end(),
            [&](const Candidate &candidate) { return candidate.actionId == actionId; });
        if (it == candidates.end()) {
            throw std::invalid_argument("action is not legal in the current combat state: " + actionId);
        }
        lastCardSelectSettlementCount_ = 0;
        lastCardSelectTasks_.clear();
        cardSelectSettlementFailureReason_.clear();
        const sts::search::Action action(it->bits);
        if (!action.isValidAction(battle_)) {
            throw std::runtime_error("enumerated combat action failed native legality check");
        }
        action.execute(battle_);
        ++decisionCount_;
        settleCardSelect();
    }

private:
    sts::GameContext gc_;
    sts::BattleContext battle_;
    sts::search::SimpleAgent baselineAgent_;
    int decisionCount_ = 0;
    int lastCardSelectSettlementCount_ = 0;
    std::vector<std::string> lastCardSelectTasks_;
    std::string cardSelectSettlementFailureReason_;
    int requestedBattleIndex_ = 0;
    int reachedBattleIndex_ = -1;

    void configureAgent() {
        baselineAgent_.print = false;
        baselineAgent_.curGameContext = &gc_;
    }

    void settleCardSelect() {
        while (!terminal() && battle_.inputState == sts::InputState::CARD_SELECT) {
            const auto task = battle_.cardSelectInfo.cardSelectTask;
            const auto taskName = cardSelectTaskName(task);
            if (lastCardSelectSettlementCount_ >= MAX_CARD_SELECT_SETTLEMENTS) {
                cardSelectSettlementFailureReason_ = "card_select_settlement_bound:" + taskName;
                return;
            }
            if (!isSupportedCardSelectTask(task)) {
                cardSelectSettlementFailureReason_ = "unsupported_card_select_task:" + taskName;
                return;
            }
            const auto actions = sts::search::Action::enumerateCardSelectActions(battle_);
            if (actions.empty()) {
                cardSelectSettlementFailureReason_ =
                    "card_select_no_enumerable_action:" + taskName;
                return;
            }
            const auto historySize = baselineAgent_.actionHistory.size();
            try {
                baselineAgent_.stepBattleCardSelect(battle_);
            } catch (const std::exception &) {
                cardSelectSettlementFailureReason_ = "card_select_settlement_error:" + taskName;
                return;
            }
            if (baselineAgent_.actionHistory.size() <= historySize) {
                cardSelectSettlementFailureReason_ = "card_select_settlement_no_progress:" + taskName;
                return;
            }
            lastCardSelectTasks_.push_back(taskName);
            ++lastCardSelectSettlementCount_;
        }
    }

    void advanceOutOfCombatToBattle(int battleIndex, int &actionCount) {
        while (gc_.outcome == sts::GameOutcome::UNDECIDED &&
               gc_.screenState != sts::ScreenState::BATTLE) {
            if (++actionCount > MAX_OUT_OF_COMBAT_ACTIONS) {
                throw std::runtime_error(
                    "baseline_out_of_combat_action_bound_before_battle:" +
                    std::to_string(battleIndex));
            }
            const auto historySize = baselineAgent_.actionHistory.size();
            baselineAgent_.stepOutOfCombat(gc_);
            if (baselineAgent_.actionHistory.size() <= historySize) {
                throw std::runtime_error(
                    "baseline_out_of_combat_no_progress_before_battle:" +
                    std::to_string(battleIndex));
            }
        }
        if (gc_.screenState != sts::ScreenState::BATTLE) {
            throw std::runtime_error(
                "baseline_run_terminated_before_battle:" +
                std::to_string(battleIndex));
        }
    }

    void playPriorBattle(int battleIndex) {
        bool usedPotions = !sts::isBossEncounter(battle_.encounter);
        int actionCount = 0;
        while (battle_.outcome == sts::Outcome::UNDECIDED) {
            if (++actionCount > MAX_PRIOR_BATTLE_ACTIONS) {
                throw std::runtime_error(
                    "baseline_prior_battle_action_bound:" +
                    std::to_string(battleIndex));
            }
            const auto historySize = baselineAgent_.actionHistory.size();
            bool actionExpected = true;
            if (battle_.inputState == sts::InputState::CARD_SELECT) {
                baselineAgent_.stepBattleCardSelect(battle_);
            } else if (battle_.inputState == sts::InputState::PLAYER_NORMAL) {
                if (usedPotions) {
                    baselineAgent_.stepBattleCardPlay(battle_);
                } else {
                    usedPotions = baselineAgent_.playPotion(battle_);
                    actionExpected = !usedPotions;
                }
            } else {
                throw std::runtime_error(
                    "baseline_prior_battle_unsupported_input:" +
                    std::to_string(battleIndex) + ":" +
                    inputStateName(battle_.inputState));
            }
            if (actionExpected && baselineAgent_.actionHistory.size() <= historySize) {
                throw std::runtime_error(
                    "baseline_prior_battle_no_progress:" +
                    std::to_string(battleIndex));
            }
        }
        battle_.exitBattle(gc_);
        if (battle_.outcome != sts::Outcome::PLAYER_VICTORY) {
            throw std::runtime_error(
                "baseline_loss_before_requested_battle:" +
                std::to_string(requestedBattleIndex_));
        }
    }

    void advanceToBattle() {
        int outOfCombatActionCount = 0;
        for (int battleIndex = 0; battleIndex <= requestedBattleIndex_; ++battleIndex) {
            advanceOutOfCombatToBattle(battleIndex, outOfCombatActionCount);
            battle_ = sts::BattleContext();
            battle_.init(gc_);
            if (battleIndex == requestedBattleIndex_) {
                reachedBattleIndex_ = battleIndex;
                if (battle_.outcome == sts::Outcome::UNDECIDED &&
                    battle_.inputState != sts::InputState::PLAYER_NORMAL) {
                    throw std::runtime_error(
                        "requested_battle_not_player_normal:" +
                        std::to_string(battleIndex) + ":" +
                        inputStateName(battle_.inputState));
                }
                return;
            }
            playPriorBattle(battleIndex);
        }
        throw std::runtime_error("requested_battle_not_reached");
    }

    std::vector<std::pair<int, int>> targetSlots() const {
        std::vector<std::pair<int, int>> result;
        int compactSlot = 1;
        for (int nativeSlot = 0; nativeSlot < battle_.monsters.monsterCount; ++nativeSlot) {
            if (battle_.monsters.arr[nativeSlot].isTargetable()) {
                result.emplace_back(compactSlot++, nativeSlot);
            }
        }
        return result;
    }

    std::vector<Candidate> legalCandidates() const {
        std::vector<Candidate> result;
        if (!supported()) {
            return result;
        }
        const auto targets = targetSlots();

        for (int cardSlot = 0; cardSlot < battle_.cards.cardsInHand; ++cardSlot) {
            const auto &card = battle_.cards.hand[cardSlot];
            if (card.requiresTarget()) {
                for (const auto &[targetSlot, nativeTarget] : targets) {
                    const sts::search::Action action(
                        sts::search::ActionType::CARD, cardSlot, nativeTarget);
                    if (!action.isValidAction(battle_)) {
                        continue;
                    }
                    result.push_back({
                        "play_card:" + std::to_string(cardSlot) + ":" +
                            std::to_string(targetSlot),
                        "play_card",
                        cardSlot * RL_TARGET_SLOTS + targetSlot,
                        cardSlot,
                        targetSlot,
                        nativeTarget,
                        action.bits,
                    });
                }
            } else {
                const sts::search::Action action(sts::search::ActionType::CARD, cardSlot);
                if (action.isValidAction(battle_)) {
                    result.push_back({
                        "play_card:" + std::to_string(cardSlot) + ":0",
                        "play_card",
                        cardSlot * RL_TARGET_SLOTS,
                        cardSlot,
                        0,
                        -1,
                        action.bits,
                    });
                }
            }
        }

        for (int potionSlot = 0; potionSlot < std::min(battle_.potionCapacity, 5);
             ++potionSlot) {
            const auto potion = battle_.potions[potionSlot];
            if (potion == sts::Potion::EMPTY_POTION_SLOT ||
                potion == sts::Potion::INVALID || potion == sts::Potion::FAIRY_POTION) {
                continue;
            }
            if (sts::potionRequiresTarget(potion)) {
                for (const auto &[targetSlot, nativeTarget] : targets) {
                    const sts::search::Action action(
                        sts::search::ActionType::POTION, potionSlot, nativeTarget);
                    if (!action.isValidAction(battle_)) {
                        continue;
                    }
                    result.push_back({
                        "use_potion:" + std::to_string(potionSlot) + ":" +
                            std::to_string(targetSlot),
                        "use_potion",
                        RL_POTION_OFFSET + potionSlot * RL_TARGET_SLOTS + targetSlot,
                        potionSlot,
                        targetSlot,
                        nativeTarget,
                        action.bits,
                    });
                }
            } else {
                const sts::search::Action action(sts::search::ActionType::POTION, potionSlot);
                if (action.isValidAction(battle_)) {
                    result.push_back({
                        "use_potion:" + std::to_string(potionSlot) + ":0",
                        "use_potion",
                        RL_POTION_OFFSET + potionSlot * RL_TARGET_SLOTS,
                        potionSlot,
                        0,
                        -1,
                        action.bits,
                    });
                }
            }
        }

        const sts::search::Action endTurn(sts::search::ActionType::END_TURN);
        if (endTurn.isValidAction(battle_)) {
            result.push_back({
                "end_turn", "end_turn", RL_END_TURN_ACTION, -1, 0, -1, endTurn.bits,
            });
        }
        return result;
    }
};

std::string buildInfoJson() {
    return json({
        {"adapter_api_version", ADAPTER_API_VERSION},
        {"baseline_policy", BASELINE_POLICY},
        {"battle_index_max", MAX_BATTLE_INDEX},
        {"card_select_settlement_max", MAX_CARD_SELECT_SETTLEMENTS},
        {"card_select_settlement_policy", BASELINE_POLICY},
        {"compiler", __VERSION__},
        {"cpp_standard", __cplusplus},
        {"pybind11_version", STS_COMBAT_ADAPTER_STRINGIFY(PYBIND11_VERSION_MAJOR) "."
            STS_COMBAT_ADAPTER_STRINGIFY(PYBIND11_VERSION_MINOR) "."
            STS_COMBAT_ADAPTER_STRINGIFY(PYBIND11_VERSION_PATCH)},
        {"rl_action_dim", RL_ACTION_DIM},
        {"state_schema_version", STATE_SCHEMA_VERSION},
        {"prior_battle_action_max", MAX_PRIOR_BATTLE_ACTIONS},
        {"out_of_combat_action_max", MAX_OUT_OF_COMBAT_ACTIONS},
        {"supported_card_select_tasks", supportedCardSelectTasksJson()},
    }).dump();
}

}  // namespace

PYBIND11_MODULE(sts_lightspeed_combat_adapter, module) {
    module.doc() = "Offline-only combat adapter POC for sts_lightspeed";
    module.def("adapter_api_version", []() { return ADAPTER_API_VERSION; });
    module.def("build_info_json", &buildInfoJson);

    py::class_<CombatEnvironment>(module, "Environment")
        .def(py::init<std::uint64_t, int, int>(), py::arg("seed"),
             py::arg("ascension") = 0, py::arg("battle_index") = 0)
        .def("clone", &CombatEnvironment::clone)
        .def("legal_actions_json", &CombatEnvironment::legalActionsJson)
        .def("snapshot_json", &CombatEnvironment::snapshotJson)
        .def("status_json", &CombatEnvironment::statusJson)
        .def("step", &CombatEnvironment::step)
        .def("terminal", &CombatEnvironment::terminal);
}
