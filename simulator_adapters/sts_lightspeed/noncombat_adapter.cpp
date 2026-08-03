#include <algorithm>
#include <cctype>
#include <cstdint>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <pybind11/pybind11.h>
#include <nlohmann/json.hpp>

#include "combat/BattleContext.h"
#include "constants/Events.h"
#include "constants/MonsterEncounters.h"
#include "constants/Potions.h"
#include "constants/Relics.h"
#include "constants/Rooms.h"
#include "game/Game.h"
#include "game/GameContext.h"
#include "sim/search/GameAction.h"
#include "sim/search/ScumSearchAgent2.h"
#include "sim/search/SimpleAgent.h"

namespace py = pybind11;
using json = nlohmann::json;

#define STS_ADAPTER_STRINGIFY_INNER(value) #value
#define STS_ADAPTER_STRINGIFY(value) STS_ADAPTER_STRINGIFY_INNER(value)

namespace {

constexpr const char *ADAPTER_API_VERSION = "sts-lightspeed-noncombat-adapter-v3";
constexpr const char *STATE_SCHEMA_VERSION = "sts-lightspeed-state-v1";
constexpr const char *BASELINE_POLICY_ID = "sts_lightspeed_simple_agent_no_potions_v1";
constexpr const char *NATIVE_BASELINE_ACTION_SCHEMA_VERSION =
    "sts-lightspeed-native-baseline-action-v1";
constexpr const char *NATIVE_TARGET_POLICY_ID = "sts_lightspeed_simple_agent_target_v1";

std::string normalizeId(const std::string &value) {
    std::string result;
    bool pendingSeparator = false;
    for (unsigned char c : value) {
        if (std::isalnum(c)) {
            if (pendingSeparator && !result.empty()) {
                result.push_back('_');
            }
            result.push_back(static_cast<char>(std::tolower(c)));
            pendingSeparator = false;
        } else {
            pendingSeparator = true;
        }
    }
    return result;
}

const char *screenStateName(sts::ScreenState state) {
    switch (state) {
        case sts::ScreenState::EVENT_SCREEN: return "EVENT_SCREEN";
        case sts::ScreenState::REWARDS: return "REWARDS";
        case sts::ScreenState::BOSS_RELIC_REWARDS: return "BOSS_RELIC_REWARDS";
        case sts::ScreenState::CARD_SELECT: return "CARD_SELECT";
        case sts::ScreenState::MAP_SCREEN: return "MAP_SCREEN";
        case sts::ScreenState::TREASURE_ROOM: return "TREASURE_ROOM";
        case sts::ScreenState::REST_ROOM: return "REST_ROOM";
        case sts::ScreenState::SHOP_ROOM: return "SHOP_ROOM";
        case sts::ScreenState::BATTLE: return "BATTLE";
        default: return "INVALID";
    }
}

const char *outcomeName(sts::GameOutcome outcome) {
    switch (outcome) {
        case sts::GameOutcome::PLAYER_LOSS: return "player_loss";
        case sts::GameOutcome::PLAYER_VICTORY: return "player_victory";
        default: return "undecided";
    }
}

std::string eventName(sts::Event event) {
    const auto idx = static_cast<std::size_t>(event);
    const auto count = sizeof(sts::eventGameNames) / sizeof(sts::eventGameNames[0]);
    return idx < count ? sts::eventGameNames[idx] : "INVALID";
}

std::string encounterName(sts::MonsterEncounter encounter) {
    const auto idx = static_cast<std::size_t>(encounter);
    const auto count = sizeof(sts::monsterEncounterEnumNames) /
                       sizeof(sts::monsterEncounterEnumNames[0]);
    return idx < count ? sts::monsterEncounterEnumNames[idx] : "INVALID";
}

json cardJson(const sts::Card &card, int slot = -1) {
    json value = {
        {"id", sts::getCardEnumName(card.getId())},
        {"name", card.getName()},
        {"upgraded", card.isUpgraded()},
        {"upgrade_count", card.getUpgraded()},
        {"misc", card.misc},
    };
    if (slot >= 0) {
        value["slot"] = slot;
    }
    return value;
}

bool shopItemIsVisible(int price, const char *kind, int slot) {
    if (price < -1) {
        throw std::runtime_error(
            "shop " + std::string(kind) + " slot " + std::to_string(slot) +
            " has invalid negative price");
    }
    return price != -1;
}

struct Candidate {
    enum class Mode {
        GAME_ACTION,
        CARD_SKIP,
        CARD_BOWL,
    };

    std::string actionId;
    std::string category;
    std::string kind;
    std::string label;
    json raw = json::object();
    Mode mode = Mode::GAME_ACTION;
    std::uint32_t bits = 0;
    int rewardIdx = -1;
    int cardIdx = -1;

    json toJson() const {
        return {
            {"action_id", actionId},
            {"available", true},
            {"category", category},
            {"kind", kind},
            {"label", label},
            {"raw", raw},
        };
    }
};

class NoncombatEnvironment {
public:
    NoncombatEnvironment(std::uint64_t seed, int ascension)
        : gc_(sts::CharacterClass::IRONCLAD, seed, ascension) {
        gc_.info.encounter = sts::MonsterEncounter::INVALID;
        configureAgents();
        advanceToDecision();
    }

    NoncombatEnvironment(const NoncombatEnvironment &other)
        : gc_(other.gc_), baselineAgent_(other.baselineAgent_),
          baselineHistory_(other.baselineHistory_), decisionCount_(other.decisionCount_),
          nativeBaselineContinuationValid_(other.nativeBaselineContinuationValid_) {
        if (other.gc_.map) {
            gc_.map = std::make_shared<sts::Map>(*other.gc_.map);
        }
        configureAgents();
    }

    std::unique_ptr<NoncombatEnvironment> clone() const {
        return std::make_unique<NoncombatEnvironment>(*this);
    }

    std::string category() const {
        if (gc_.outcome != sts::GameOutcome::UNDECIDED) {
            return "";
        }
        switch (gc_.screenState) {
            case sts::ScreenState::MAP_SCREEN:
                return "route";
            case sts::ScreenState::SHOP_ROOM:
                return "shop";
            case sts::ScreenState::EVENT_SCREEN:
                if (gc_.curEvent != sts::Event::NEOW &&
                    gc_.curEvent != sts::Event::INVALID) {
                    return "event";
                }
                return "";
            case sts::ScreenState::REWARDS:
                return gc_.info.rewardsContainer.cardRewardCount > 0
                    ? "card_reward"
                    : "";
            default:
                return "";
        }
    }

    bool terminal() const {
        return gc_.outcome != sts::GameOutcome::UNDECIDED;
    }

    std::string snapshotJson() const {
        assertSupportedCurrentDecision();
        json state = {
            {"act", gc_.act},
            {"ascension", gc_.ascension},
            {"blue_key", gc_.blueKey},
            {"boss", encounterName(gc_.boss)},
            {"cur_hp", gc_.curHp},
            {"cur_map_node", {{"x", gc_.curMapNodeX}, {"y", gc_.curMapNodeY}}},
            {"cur_room", sts::roomStrings[static_cast<int>(gc_.curRoom)]},
            {"encounter", encounterName(gc_.info.encounter)},
            {"floor", gc_.floorNum},
            {"gold", gc_.gold},
            {"green_key", gc_.greenKey},
            {"max_hp", gc_.maxHp},
            {"outcome", outcomeName(gc_.outcome)},
            {"red_key", gc_.redKey},
            {"screen_state", screenStateName(gc_.screenState)},
            {"seed", std::to_string(gc_.seed)},
        };

        state["deck"] = json::array();
        for (int i = 0; i < gc_.deck.cards.size(); ++i) {
            state["deck"].push_back(cardJson(gc_.deck.cards[i], i));
        }

        state["relics"] = json::array();
        for (const auto &relic : gc_.relics.relics) {
            state["relics"].push_back({
                {"data", relic.data},
                {"id", sts::relicEnumNames[static_cast<int>(relic.id)]},
                {"name", sts::getRelicName(relic.id)},
            });
        }

        state["potions"] = json::array();
        for (int i = 0; i < gc_.potionCapacity; ++i) {
            state["potions"].push_back({
                {"id", sts::potionEnumNames[static_cast<int>(gc_.potions[i])]},
                {"name", sts::getPotionName(gc_.potions[i])},
                {"slot", i},
            });
        }

        appendMap(state);
        appendDecisionContext(state);

        const json payload = {
            {"adapter_api_version", ADAPTER_API_VERSION},
            {"baseline_control", {
                {"history", baselineHistory_},
                {"policy_id", BASELINE_POLICY_ID},
            }},
            {"category", category().empty() ? json(nullptr) : json(category())},
            {"decision_count", decisionCount_},
            {"schema_version", STATE_SCHEMA_VERSION},
            {"source_type", "sts_lightspeed_simulation"},
            {"state", state},
            {"terminal", terminal()},
        };
        return payload.dump();
    }

    std::string legalActionsJson() const {
        const auto candidates = legalCandidates();
        json result = json::array();
        for (const auto &candidate : candidates) {
            result.push_back(candidate.toJson());
        }
        return result.dump();
    }

    std::string nativeBaselineActionJson() const {
        const auto actionId = probeNativeBaselineAction(nullptr);
        return json({
            {"action_id", actionId},
            {"category", category()},
            {"policy_id", NATIVE_TARGET_POLICY_ID},
            {"schema_version", NATIVE_BASELINE_ACTION_SCHEMA_VERSION},
        }).dump();
    }

    std::string stepNativeBaseline() {
        if (terminal()) {
            throw std::runtime_error("cannot act in a terminal simulator state");
        }
        sts::search::SimpleAgent agentAfter = baselineAgent_;
        const auto actionId = probeNativeBaselineAction(&agentAfter);
        const auto candidates = legalCandidates();
        const auto it = std::find_if(candidates.begin(), candidates.end(),
            [&](const Candidate &candidate) { return candidate.actionId == actionId; });
        if (it == candidates.end()) {
            throw std::runtime_error("native baseline action is not a current candidate");
        }

        baselineAgent_.mapPath = agentAfter.mapPath;
        applyCandidate(*it);
        ++decisionCount_;
        advanceToDecision();
        return actionId;
    }

    void step(const std::string &actionId) {
        if (terminal()) {
            throw std::runtime_error("cannot act in a terminal simulator state");
        }
        const auto candidates = legalCandidates();
        const auto it = std::find_if(candidates.begin(), candidates.end(),
            [&](const Candidate &candidate) { return candidate.actionId == actionId; });
        if (it == candidates.end()) {
            throw std::invalid_argument("action is not legal in the current target decision: " + actionId);
        }

        nativeBaselineContinuationValid_ = false;
        applyCandidate(*it);
        ++decisionCount_;
        advanceToDecision();
    }

private:
    sts::GameContext gc_;
    sts::search::SimpleAgent baselineAgent_;
    std::vector<std::string> baselineHistory_;
    int decisionCount_ = 0;
    bool nativeBaselineContinuationValid_ = true;

    void configureAgents() {
        baselineAgent_.print = false;
        baselineAgent_.curGameContext = &gc_;
    }

    void assertSupportedCurrentDecision() const {
        if (category() == "shop" && gc_.hasRelic(sts::RelicId::THE_COURIER)) {
            throw std::runtime_error("unsupported_shop_courier_restock_semantics");
        }
    }

    bool shopPotionPurchaseSupported() const {
        return !gc_.hasRelic(sts::RelicId::SOZU) &&
            gc_.potionCount < gc_.potionCapacity;
    }

    void appendMap(json &state) const {
        if (!gc_.map) {
            state["map"] = nullptr;
            return;
        }
        json nodes = json::array();
        for (int y = 0; y < 15; ++y) {
            for (int x = 0; x < 7; ++x) {
                const auto &node = gc_.map->getNode(x, y);
                if (node.room == sts::Room::NONE && node.edgeCount == 0 && node.parentCount == 0) {
                    continue;
                }
                json edges = json::array();
                for (int i = 0; i < node.edgeCount; ++i) {
                    edges.push_back({{"x", node.edges[i]}, {"y", y + 1}});
                }
                nodes.push_back({
                    {"edges", edges},
                    {"room", sts::roomStrings[static_cast<int>(node.room)]},
                    {"symbol", std::string(1, sts::getRoomSymbol(node.room))},
                    {"x", x},
                    {"y", y},
                });
            }
        }
        state["map"] = {
            {"burning_elite", {
                {"buff", gc_.map->burningEliteBuff},
                {"x", gc_.map->burningEliteX},
                {"y", gc_.map->burningEliteY},
            }},
            {"nodes", nodes},
        };
    }

    void appendDecisionContext(json &state) const {
        state["decision_context"] = json::object();
        if (category() == "event") {
            state["decision_context"] = {
                {"event_data", gc_.info.eventData},
                {"event_id", sts::eventIdStrings[static_cast<int>(gc_.curEvent)]},
                {"event_name", eventName(gc_.curEvent)},
            };
            if (gc_.curEvent == sts::Event::NLOTH) {
                json offeredRelics = json::array();
                const auto appendOffer = [&](int simulatorChoiceIndex, int relicSlot) {
                    if (relicSlot < 0 || relicSlot >= gc_.relics.size()) {
                        throw std::runtime_error("N'loth offered relic slot is invalid");
                    }
                    const auto &relic = gc_.relics.relics[relicSlot];
                    offeredRelics.push_back({
                        {"relic_id", sts::relicEnumNames[static_cast<int>(relic.id)]},
                        {"relic_name", sts::getRelicName(relic.id)},
                        {"relic_slot", relicSlot},
                        {"simulator_choice_index", simulatorChoiceIndex},
                    });
                };
                appendOffer(0, gc_.info.relicIdx0);
                appendOffer(1, gc_.info.relicIdx1);
                state["decision_context"]["offered_relics"] =
                    std::move(offeredRelics);
            }
        } else if (category() == "shop") {
            json cards = json::array();
            json relics = json::array();
            json potions = json::array();
            for (int i = 0; i < 7; ++i) {
                const int price = gc_.info.shop.cardPrice(i);
                if (!shopItemIsVisible(price, "card", i)) {
                    continue;
                }
                auto card = cardJson(gc_.info.shop.cards[i], i);
                card["price"] = price;
                cards.push_back(card);
            }
            for (int i = 0; i < 3; ++i) {
                const int price = gc_.info.shop.relicPrice(i);
                if (!shopItemIsVisible(price, "relic", i)) {
                    continue;
                }
                relics.push_back({
                    {"id", sts::relicEnumNames[static_cast<int>(gc_.info.shop.relics[i])]},
                    {"name", sts::getRelicName(gc_.info.shop.relics[i])},
                    {"price", price},
                    {"slot", i},
                });
            }
            for (int i = 0; i < 3; ++i) {
                const int price = gc_.info.shop.potionPrice(i);
                if (!shopItemIsVisible(price, "potion", i)) {
                    continue;
                }
                potions.push_back({
                    {"id", sts::potionEnumNames[static_cast<int>(gc_.info.shop.potions[i])]},
                    {"name", sts::getPotionName(gc_.info.shop.potions[i])},
                    {"price", price},
                    {"slot", i},
                });
            }
            state["decision_context"] = {
                {"cards", cards},
                {"potions", potions},
                {"relics", relics},
                {"remove_cost", gc_.info.shop.removeCost},
            };
        } else if (category() == "card_reward") {
            const auto &rewards = gc_.info.rewardsContainer;
            const int rewardIdx = rewards.cardRewardCount - 1;
            json cards = json::array();
            for (int i = 0; i < rewards.cardRewards[rewardIdx].size(); ++i) {
                cards.push_back(cardJson(rewards.cardRewards[rewardIdx][i], i));
            }
            state["decision_context"] = {
                {"cards", cards},
                {"has_singing_bowl", gc_.hasRelic(sts::RelicId::SINGING_BOWL)},
                {"reward_index", rewardIdx},
            };
        }
    }

    std::vector<Candidate> legalCandidates() const {
        const auto currentCategory = category();
        assertSupportedCurrentDecision();
        if (currentCategory.empty()) {
            return {};
        }
        if (currentCategory == "card_reward") {
            return cardRewardCandidates();
        }

        std::vector<Candidate> result;
        for (const auto &action : sts::search::GameAction::getAllActionsInState(gc_)) {
            Candidate candidate;
            candidate.bits = action.bits;
            candidate.category = currentCategory;
            candidate.raw = {
                {"bits", action.bits},
                {"idx1", action.getIdx1()},
                {"idx2", action.getIdx2()},
            };

            if (currentCategory == "route") {
                const int nextY = gc_.curMapNodeY + 1;
                const int x = action.getIdx1();
                const bool boss = gc_.curMapNodeY == 14;
                const auto room = boss ? sts::Room::BOSS : gc_.map->getNode(x, nextY).room;
                candidate.kind = "map_node";
                candidate.label = std::string(1, sts::getRoomSymbol(room)) + "@" +
                    std::to_string(x) + "," + std::to_string(nextY);
                candidate.actionId = "route:map_node:" + std::to_string(x) + ":" +
                    std::to_string(nextY);
                candidate.raw["room"] = sts::roomStrings[static_cast<int>(room)];
                candidate.raw["x"] = x;
                candidate.raw["y"] = nextY;
            } else if (currentCategory == "event") {
                candidate.kind = "event_option";
                candidate.label = eventName(gc_.curEvent) + " option " +
                    std::to_string(action.getIdx1());
                candidate.actionId = "event:" + normalizeId(eventName(gc_.curEvent)) +
                    ":option:" + std::to_string(action.getIdx1());
                candidate.raw["event_id"] = sts::eventIdStrings[static_cast<int>(gc_.curEvent)];
                candidate.raw["follow_up_control"] = "baseline";
            } else {
                using Type = sts::search::GameAction::RewardsActionType;
                if (action.getRewardsActionType() == Type::POTION &&
                    !shopPotionPurchaseSupported()) {
                    continue;
                }
                appendShopCandidate(action, candidate);
            }
            result.push_back(std::move(candidate));
        }
        return result;
    }

    std::vector<Candidate> cardRewardCandidates() const {
        std::vector<Candidate> result;
        const auto &rewards = gc_.info.rewardsContainer;
        const int rewardIdx = rewards.cardRewardCount - 1;
        const auto &cards = rewards.cardRewards[rewardIdx];
        for (int cardIdx = 0; cardIdx < cards.size(); ++cardIdx) {
            Candidate candidate;
            candidate.category = "card_reward";
            candidate.kind = "take";
            candidate.label = cards[cardIdx].getName();
            candidate.rewardIdx = rewardIdx;
            candidate.cardIdx = cardIdx;
            candidate.bits = sts::search::GameAction(
                sts::search::GameAction::RewardsActionType::CARD,
                rewardIdx,
                cardIdx).bits;
            candidate.actionId = "card_reward:take:" + std::to_string(rewardIdx) + ":" +
                std::to_string(cardIdx) + ":" + normalizeId(candidate.label);
            candidate.raw = cardJson(cards[cardIdx], cardIdx);
            candidate.raw["reward_index"] = rewardIdx;
            result.push_back(std::move(candidate));
        }

        Candidate skip;
        skip.category = "card_reward";
        skip.rewardIdx = rewardIdx;
        skip.bits = sts::search::GameAction(
            sts::search::GameAction::RewardsActionType::CARD,
            rewardIdx,
            5).bits;
        if (gc_.hasRelic(sts::RelicId::SINGING_BOWL)) {
            skip.actionId = "card_reward:bowl:" + std::to_string(rewardIdx);
            skip.kind = "bowl";
            skip.label = "gain 2 max hp";
            skip.mode = Candidate::Mode::CARD_BOWL;
        } else {
            skip.actionId = "card_reward:skip:" + std::to_string(rewardIdx);
            skip.kind = "skip";
            skip.label = "skip";
            skip.mode = Candidate::Mode::CARD_SKIP;
        }
        skip.raw = {{"reward_index", rewardIdx}};
        result.push_back(std::move(skip));
        return result;
    }

    std::string probeNativeBaselineAction(sts::search::SimpleAgent *agentAfter) const {
        assertSupportedCurrentDecision();
        if (!nativeBaselineContinuationValid_) {
            throw std::runtime_error(
                "native baseline query requires a baseline-following target trajectory");
        }
        const auto currentCategory = category();
        if (currentCategory.empty()) {
            throw std::runtime_error("native baseline query requires a target decision");
        }

        NoncombatEnvironment probe(*this);
        probe.baselineAgent_.actionHistory.clear();
        if (currentCategory == "route") {
            probe.baselineAgent_.stepOutOfCombat(probe.gc_);
        } else if (currentCategory == "shop") {
            probe.baselineAgent_.stepShopScreen(probe.gc_);
        } else if (currentCategory == "event") {
            probe.baselineAgent_.stepEventScreen(probe.gc_);
        } else if (currentCategory == "card_reward") {
            probe.baselineAgent_.stepCardReward(probe.gc_);
        } else {
            throw std::runtime_error("unsupported native baseline target category");
        }
        if (probe.baselineAgent_.actionHistory.size() != 1) {
            throw std::runtime_error(
                "native baseline target query did not emit exactly one game action");
        }

        const auto actionBits = static_cast<std::uint32_t>(
            probe.baselineAgent_.actionHistory.front());
        const auto candidates = legalCandidates();
        const Candidate *matched = nullptr;
        for (const auto &candidate : candidates) {
            if (candidate.bits != actionBits) {
                continue;
            }
            if (matched != nullptr) {
                throw std::runtime_error(
                    "native baseline game action maps to multiple adapter candidates");
            }
            matched = &candidate;
        }
        if (matched == nullptr) {
            throw std::runtime_error(
                "native baseline game action is not an adapter candidate");
        }
        if (agentAfter != nullptr) {
            *agentAfter = probe.baselineAgent_;
            agentAfter->curGameContext = nullptr;
        }
        return matched->actionId;
    }

    void appendShopCandidate(const sts::search::GameAction &action, Candidate &candidate) const {
        using Type = sts::search::GameAction::RewardsActionType;
        const int slot = action.getIdx1();
        switch (action.getRewardsActionType()) {
            case Type::CARD: {
                const auto &card = gc_.info.shop.cards[slot];
                candidate.kind = "buy_card";
                candidate.label = card.getName();
                candidate.actionId = "shop:buy_card:" + std::to_string(slot) + ":" +
                    normalizeId(candidate.label);
                candidate.raw.update(cardJson(card, slot));
                candidate.raw["price"] = gc_.info.shop.cardPrice(slot);
                break;
            }
            case Type::RELIC:
                candidate.kind = "buy_relic";
                candidate.label = sts::getRelicName(gc_.info.shop.relics[slot]);
                candidate.actionId = "shop:buy_relic:" + std::to_string(slot) + ":" +
                    normalizeId(candidate.label);
                candidate.raw["price"] = gc_.info.shop.relicPrice(slot);
                candidate.raw["slot"] = slot;
                break;
            case Type::POTION:
                candidate.kind = "buy_potion";
                candidate.label = sts::getPotionName(gc_.info.shop.potions[slot]);
                candidate.actionId = "shop:buy_potion:" + std::to_string(slot) + ":" +
                    normalizeId(candidate.label);
                candidate.raw["price"] = gc_.info.shop.potionPrice(slot);
                candidate.raw["slot"] = slot;
                break;
            case Type::CARD_REMOVE:
                candidate.kind = "remove_card";
                candidate.label = "remove a card";
                candidate.actionId = "shop:remove_card";
                candidate.raw["price"] = gc_.info.shop.removeCost;
                break;
            case Type::SKIP:
                candidate.kind = "leave";
                candidate.label = "leave";
                candidate.actionId = "shop:leave";
                break;
            default:
                throw std::runtime_error("unexpected shop action type");
        }
    }

    void applyCandidate(const Candidate &candidate) {
        if (candidate.mode == Candidate::Mode::CARD_SKIP ||
            candidate.mode == Candidate::Mode::CARD_BOWL) {
            auto &rewards = gc_.info.rewardsContainer;
            if (candidate.mode == Candidate::Mode::CARD_BOWL) {
                gc_.playerIncreaseMaxHp(2);
            }
            rewards.removeCardReward(candidate.rewardIdx);
            return;
        }

        const sts::search::GameAction action(candidate.bits);
        if (!action.isValidAction(gc_)) {
            throw std::runtime_error("adapter candidate failed simulator legality check");
        }
        action.execute(gc_);
    }

    void advanceToDecision() {
        constexpr int MAX_STEPS = 10000;
        int steps = 0;
        while (!terminal() && category().empty()) {
            if (++steps > MAX_STEPS) {
                throw std::runtime_error("simulator baseline exceeded advance step bound");
            }
            if (gc_.screenState == sts::ScreenState::BATTLE) {
                baselineHistory_.push_back("combat:" + encounterName(gc_.info.encounter));
                const auto carriedPotions = gc_.potions;
                const int carriedPotionCount = gc_.potionCount;
                const int carriedPotionCapacity = gc_.potionCapacity;
                sts::BattleContext battle;
                battle.init(gc_);
                battle.potionCount = 0;
                battle.potionCapacity = 0;
                std::fill(
                    battle.potions.begin(),
                    battle.potions.end(),
                    sts::Potion::EMPTY_POTION_SLOT);
                baselineAgent_.curGameContext = &gc_;
                baselineAgent_.playoutBattle(battle);
                battle.exitBattle(gc_);
                gc_.potions = carriedPotions;
                gc_.potionCount = carriedPotionCount;
                gc_.potionCapacity = carriedPotionCapacity;
                continue;
            }
            if (gc_.screenState == sts::ScreenState::REWARDS) {
                resolveNonCardRewards();
                continue;
            }

            baselineHistory_.push_back(std::string("screen:") + screenStateName(gc_.screenState));
            baselineAgent_.curGameContext = &gc_;
            baselineAgent_.stepOutOfCombat(gc_);
        }
    }

    void resolveNonCardRewards() {
        using Action = sts::search::GameAction;
        using Type = Action::RewardsActionType;
        auto &rewards = gc_.info.rewardsContainer;
        if (rewards.cardRewardCount > 0) {
            return;
        }
        if (rewards.goldRewardCount > 0) {
            baselineHistory_.push_back("reward:gold");
            Action(Type::GOLD, 0).execute(gc_);
        } else if (rewards.relicCount > 0) {
            baselineHistory_.push_back("reward:relic");
            Action(Type::RELIC, 0).execute(gc_);
        } else if (rewards.sapphireKey || rewards.emeraldKey) {
            baselineHistory_.push_back("reward:key");
            Action(Type::KEY).execute(gc_);
        } else if (rewards.potionCount > 0 && gc_.potionCount < gc_.potionCapacity) {
            baselineHistory_.push_back("reward:potion");
            Action(Type::POTION, 0).execute(gc_);
        } else if (rewards.potionCount > 0) {
            baselineHistory_.push_back("reward:potion_skipped_full");
            rewards.removePotionReward(0);
        } else {
            baselineHistory_.push_back("reward:leave");
            Action(Type::SKIP).execute(gc_);
        }
    }
};

std::vector<std::string> currentRewardNames(const sts::GameContext &gc) {
    if (gc.screenState != sts::ScreenState::REWARDS ||
        gc.info.rewardsContainer.cardRewardCount <= 0) {
        throw std::runtime_error("historical prefix probe did not reach a card reward");
    }
    const auto &rewards = gc.info.rewardsContainer;
    const auto &cards = rewards.cardRewards[rewards.cardRewardCount - 1];
    std::vector<std::string> names;
    for (const auto &card : cards) {
        names.emplace_back(card.getName());
    }
    std::sort(names.begin(), names.end());
    return names;
}

std::string historicalPrefixJson(
    std::uint64_t seed,
    int ascension,
    const std::string &selectedNeowCard) {
    sts::GameContext gc(sts::CharacterClass::IRONCLAD, seed, ascension);
    sts::search::ScumSearchAgent2 agent;
    agent.simulationCountBase = 1;
    agent.bossSimulationMultiplier = 1;
    agent.pauseOnCardReward = true;
    agent.printActions = false;
    agent.printLogs = false;

    agent.playout(gc);
    const auto neowCards = currentRewardNames(gc);

    auto &rewards = gc.info.rewardsContainer;
    const int rewardIdx = rewards.cardRewardCount - 1;
    int selectedIdx = -1;
    for (int i = 0; i < rewards.cardRewards[rewardIdx].size(); ++i) {
        if (rewards.cardRewards[rewardIdx][i].getName() == selectedNeowCard) {
            selectedIdx = i;
            break;
        }
    }
    if (selectedIdx < 0) {
        throw std::invalid_argument("selected historical Neow card is not offered");
    }
    sts::search::GameAction(
        sts::search::GameAction::RewardsActionType::CARD,
        rewardIdx,
        selectedIdx).execute(gc);

    agent.playout(gc);
    const auto floorOneCards = currentRewardNames(gc);
    return json({
        {"encounter", encounterName(gc.info.encounter)},
        {"floor", gc.floorNum},
        {"floor_one_candidates", floorOneCards},
        {"neow_candidates", neowCards},
        {"selected_neow_card", selectedNeowCard},
    }).dump();
}

std::string buildInfoJson() {
    return json({
        {"adapter_api_version", ADAPTER_API_VERSION},
        {"baseline_policy_id", BASELINE_POLICY_ID},
        {"native_target_policy_id", NATIVE_TARGET_POLICY_ID},
        {"compiler", __VERSION__},
        {"cpp_standard", __cplusplus},
        {"pybind11_version", STS_ADAPTER_STRINGIFY(PYBIND11_VERSION_MAJOR) "."
            STS_ADAPTER_STRINGIFY(PYBIND11_VERSION_MINOR) "."
            STS_ADAPTER_STRINGIFY(PYBIND11_VERSION_PATCH)},
    }).dump();
}

}  // namespace

PYBIND11_MODULE(sts_lightspeed_noncombat_adapter, module) {
    module.doc() = "Offline-only non-combat adapter POC for sts_lightspeed";
    module.def("adapter_api_version", []() { return ADAPTER_API_VERSION; });
    module.def("build_info_json", &buildInfoJson);
    module.def("historical_prefix_json", &historicalPrefixJson);

    py::class_<NoncombatEnvironment>(module, "Environment")
        .def(py::init<std::uint64_t, int>(), py::arg("seed"), py::arg("ascension") = 0)
        .def("category", &NoncombatEnvironment::category)
        .def("clone", &NoncombatEnvironment::clone)
        .def("legal_actions_json", &NoncombatEnvironment::legalActionsJson)
        .def("native_baseline_action_json", &NoncombatEnvironment::nativeBaselineActionJson)
        .def("snapshot_json", &NoncombatEnvironment::snapshotJson)
        .def("step", &NoncombatEnvironment::step)
        .def("step_native_baseline", &NoncombatEnvironment::stepNativeBaseline)
        .def("terminal", &NoncombatEnvironment::terminal);
}
