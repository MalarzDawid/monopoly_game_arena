"""LLM-powered agent for Monopoly using OpenAI-compatible API (vLLM/Ollama)."""

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

from core.game.game import ActionType, GameState
from core.game.rules import Action
from core.game.spaces import PropertySpace, RailroadSpace, UtilitySpace

from core.agents.base import Agent
from core.exceptions import LLMError
from settings import get_llm_settings

logger = logging.getLogger(__name__)

# Template directory (project root / templates)
TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"

# Central LLM configuration
_llm_settings = get_llm_settings()

DEFAULT_LLM_BASE_URL = _llm_settings.base_url or "http://localhost:11434/v1"
DEFAULT_LLM_MODEL = _llm_settings.model
DEFAULT_LLM_API_KEY = (
    _llm_settings.api_key.get_secret_value() if _llm_settings.api_key is not None else None
)

# Timeouts and limits
LLM_TIMEOUT_SECONDS = float(_llm_settings.timeout_seconds)
MAX_TOKENS = int(_llm_settings.max_tokens)


class LLMAgent(Agent):
    """
    LLM-powered agent that uses a language model via OpenAI-compatible API.

    Supports both vLLM and Ollama backends through their OpenAI-compatible
    endpoints (/v1/chat/completions).

    The agent:
    1. Serializes the current game state into a compact JSON format
    2. Constructs a prompt with system instructions, strategy, state, and legal actions
    3. Queries the LLM via OpenAI-compatible API
    4. Parses the JSON response and validates the action
    5. Falls back to a safe action if parsing/validation fails

    Configuration via environment variables:
        LLM_BASE_URL: Base URL for API (default: http://localhost:11434/v1 for Ollama)
        LLM_MODEL: Model name (default: gemma3:4b)
        LLM_TIMEOUT: Request timeout in seconds (default: 30)
        LLM_MAX_TOKENS: Max response tokens (default: 512)

    Attributes:
        player_id: The player's index in the game.
        name: The player's display name.
        model_name: The LLM model name.
        strategy: Strategy template name (aggressive, balanced, defensive).
        base_url: Base URL for the OpenAI-compatible API.
        decision_callback: Optional callback for logging decisions to DB.
    """

    # Valid strategies
    STRATEGIES = {"aggressive", "balanced", "defensive"}

    def __init__(
        self,
        player_id: int,
        name: str,
        model_name: str = None,
        strategy: str = "balanced",
        base_url: str = None,
        api_key: Optional[str] = None,
        decision_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize the LLM agent.

        Args:
            player_id: The player's index in the game.
            name: The player's display name.
            model_name: The LLM model to use (default from LLM settings).
            strategy: Strategy template (aggressive, balanced, defensive).
            base_url: Base URL for OpenAI-compatible API (default from LLM settings).
            api_key: Optional API key for providers that require authentication.
            decision_callback: Optional callback(decision_data) for DB logging.
        """
        super().__init__(player_id, name)
        self.model_name = model_name or DEFAULT_LLM_MODEL
        self.strategy = strategy if strategy in self.STRATEGIES else "balanced"
        self.base_url = base_url or DEFAULT_LLM_BASE_URL
        self.api_key = api_key if api_key is not None else DEFAULT_LLM_API_KEY
        self.decision_callback = decision_callback
        # Allow injected client; fallback to lazy creation
        self._client: Optional[httpx.Client] = None

        # Load templates
        self._system_prompt = self._load_template("system_prompt.txt")
        self._strategy_prompt = self._load_template(f"{self.strategy}.txt")

        # Decision counter for sequence numbers
        self._decision_count = 0

    def _load_template(self, filename: str) -> str:
        """Load a template file."""
        path = TEMPLATES_DIR / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        logger.warning(f"Template not found: {path}")
        return ""

    def choose_action(self, game: GameState, legal_actions: List[Action]) -> Action:
        """
        Choose an action using LLM reasoning.

        Args:
            game: The current game state.
            legal_actions: List of legal actions available to the player.

        Returns:
            The chosen action to execute.
        """
        if not legal_actions:
            return None

        start_time = time.time()
        self._decision_count += 1

        # Serialize game state for prompt
        game_state_json = self._serialize_game_state(game)
        player_state_json = self._serialize_player_state(game)
        actions_json = self._serialize_legal_actions(legal_actions)

        # Build prompt
        prompt = self._build_prompt(game_state_json, player_state_json, actions_json)

        # Query LLM
        raw_response = ""
        error_msg = None
        chosen_action = None
        rationale = ""
        used_fallback = False

        try:
            raw_response = self._query_llm(prompt)
            chosen_action, rationale = self._parse_response(raw_response, legal_actions)
        except Exception as e:
            llm_error = LLMError(str(e))
            error_msg = str(llm_error)
            logger.warning("LLM error for player %s: %s", self.player_id, error_msg)

        # Fallback if parsing failed or action invalid
        if chosen_action is None:
            chosen_action = self._get_fallback_action(legal_actions)
            used_fallback = True
            rationale = f"Fallback due to: {error_msg or 'invalid response'}"

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Log decision (for DB callback)
        if self.decision_callback:
            decision_data = {
                "player_id": self.player_id,
                "turn_number": game.turn_number,
                "sequence_number": self._decision_count,
                "game_state": game_state_json,
                "player_state": player_state_json,
                "available_actions": {"actions": actions_json},
                "prompt": prompt,
                "raw_response": raw_response,
                "reasoning": rationale,
                "chosen_action": {
                    "action_type": chosen_action.action_type.value,
                    "params": chosen_action.params,
                },
                "used_fallback": used_fallback,
                "error": error_msg,
                "processing_time_ms": processing_time_ms,
                "model_version": self.model_name,
                "strategy": self.strategy,
            }
            try:
                self.decision_callback(decision_data)
            except Exception as cb_err:
                logger.error("Decision callback error: %s", cb_err)

        logger.info(
            f"LLM Player {self.player_id} chose {chosen_action.action_type.value} "
            f"(fallback={used_fallback}, time={processing_time_ms}ms)"
        )

        return chosen_action

    def _serialize_game_state(self, game: GameState) -> Dict[str, Any]:
        """Serialize game state for the prompt (compact format)."""
        # Opponents summary
        opponents = []
        for pid, pstate in game.players.items():
            if pid == self.player_id:
                continue
            # Count monopolies
            monopolies = []
            for color, positions in game.board.color_groups.items():
                if all(
                    game.property_ownership.get(pos)
                    and game.property_ownership[pos].owner_id == pid
                    for pos in positions
                ):
                    monopolies.append(color)

            opponents.append({
                "id": pid,
                "name": pstate.name,
                "cash": pstate.cash,
                "position": pstate.position,
                "properties": len(pstate.properties),
                "monopolies": monopolies,
                "bankrupt": pstate.is_bankrupt,
                "in_jail": pstate.in_jail,
            })

        # Auction info
        auction = None
        if game.active_auction:
            a = game.active_auction
            auction = {
                "property": a.property_name,
                "position": a.property_position,
                "current_bid": a.current_bid,
                "high_bidder": a.high_bidder,
                "active_bidders": list(a.active_bidders),
            }

        # Pending payments
        pending = {}
        if game.pending_rent_payment:
            payer_id, owner_id, amount = game.pending_rent_payment
            pending["rent"] = {"amount": amount, "to_player": owner_id}
        if game.pending_tax_payment:
            payer_id, amount = game.pending_tax_payment
            pending["tax"] = {"amount": amount}

        return {
            "turn": game.turn_number,
            "current_player": game.get_current_player().player_id,
            "opponents": opponents,
            "auction": auction,
            "pending_payments": pending if pending else None,
            "bank_houses": game.bank.houses_available,
            "bank_hotels": game.bank.hotels_available,
        }

    def _serialize_player_state(self, game: GameState) -> Dict[str, Any]:
        """Serialize current player's state."""
        player = game.players[self.player_id]

        # Detailed property info
        properties = []
        for pos in sorted(player.properties):
            space = game.board.get_space(pos)
            ownership = game.property_ownership.get(pos)

            prop_info = {
                "position": pos,
                "name": space.name,
                "houses": ownership.houses if ownership else 0,
                "mortgaged": ownership.is_mortgaged if ownership else False,
            }

            if isinstance(space, PropertySpace):
                prop_info["color"] = space.color_group
                prop_info["price"] = space.price
                prop_info["rent_base"] = space.rent_base
            elif isinstance(space, RailroadSpace):
                prop_info["type"] = "railroad"
                prop_info["price"] = space.price
            elif isinstance(space, UtilitySpace):
                prop_info["type"] = "utility"
                prop_info["price"] = space.price

            properties.append(prop_info)

        # Check monopolies
        monopolies = []
        for color, positions in game.board.color_groups.items():
            if all(
                game.property_ownership.get(pos)
                and game.property_ownership[pos].owner_id == self.player_id
                for pos in positions
            ):
                monopolies.append(color)

        # Current space info
        current_space = game.board.get_space(player.position)

        return {
            "player_id": self.player_id,
            "name": player.name,
            "cash": player.cash,
            "position": player.position,
            "current_space": current_space.name,
            "in_jail": player.in_jail,
            "jail_turns": player.jail_turns,
            "jail_cards": player.get_out_of_jail_cards,
            "properties": properties,
            "monopolies": monopolies,
            "property_count": len(player.properties),
        }

    def _serialize_legal_actions(self, legal_actions: List[Action]) -> List[Dict[str, Any]]:
        """Serialize legal actions for the prompt."""
        actions = []
        for action in legal_actions:
            actions.append({
                "action_type": action.action_type.value,
                "params": action.params,
            })
        return actions

    def _build_prompt(
        self,
        game_state: Dict[str, Any],
        player_state: Dict[str, Any],
        legal_actions: List[Dict[str, Any]],
    ) -> str:
        """Build the full prompt for the LLM."""
        prompt_parts = [
            self._system_prompt,
            "",
            self._strategy_prompt,
            "",
            "## Current Game State",
            "```json",
            json.dumps(game_state, indent=2),
            "```",
            "",
            "## Your Player State",
            "```json",
            json.dumps(player_state, indent=2),
            "```",
            "",
            "## Legal Actions",
            "```json",
            json.dumps(legal_actions, indent=2),
            "```",
            "",
            "Choose your action. Respond with ONLY the JSON object:",
        ]
        return "\n".join(prompt_parts)

    def _query_llm(self, prompt: str) -> str:
        """Query the LLM using OpenAI-compatible chat completions API."""
        url = f"{self.base_url.rstrip('/')}/chat/completions"

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": 0.3,
            "stop": ["\n\n", "```"],
        }

        headers: Dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        client = self._client or httpx.Client(timeout=LLM_TIMEOUT_SECONDS)
        response = client.post(
            url,
            json=payload,
            headers=headers or None,
            timeout=LLM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        result = response.json()

        # OpenAI-compatible API returns choices[0].message.content
        if "choices" in result and len(result["choices"]) > 0:
            message = result["choices"][0].get("message", {})
            return message.get("content", "").strip()

        raise ValueError("Invalid LLM response format")

    def _parse_response(
        self,
        raw_response: str,
        legal_actions: List[Action]
    ) -> Tuple[Optional[Action], str]:
        """
        Parse LLM response and validate the action.

        Returns:
            Tuple of (Action or None, rationale string)
        """
        if not raw_response:
            return None, "Empty response"

        # Clean up response - extract JSON
        text = raw_response.strip()

        # Try to find JSON in the response
        json_start = text.find("{")
        json_end = text.rfind("}") + 1

        if json_start == -1 or json_end == 0:
            return None, f"No JSON found in response: {text[:100]}"

        json_str = text[json_start:json_end]

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return None, f"JSON parse error: {e}"

        # Validate required fields
        action_type_str = data.get("action_type")
        params = data.get("params", {})
        rationale = data.get("rationale", "")

        if not action_type_str:
            return None, "Missing action_type in response"

        # Convert to ActionType (normalize to lowercase)
        try:
            action_type = ActionType(action_type_str.lower())
        except ValueError:
            return None, f"Invalid action_type: {action_type_str}"

        # Validate action is in legal actions
        legal_action = None
        for la in legal_actions:
            if la.action_type == action_type:
                # Check if params match (for position-specific actions)
                if "position" in la.params and "position" in params:
                    if la.params["position"] == params.get("position"):
                        legal_action = la
                        break
                elif "position" not in la.params:
                    legal_action = la
                    break

        if legal_action is None:
            return None, f"Action {action_type_str} not in legal actions"

        # Create action with LLM's params (validated)
        result_action = Action(action_type, **params)

        # Ensure required params are present
        if action_type == ActionType.BID:
            if "amount" not in params:
                return None, "BID action requires 'amount' param"
            result_action.params["amount"] = int(params["amount"])

        return result_action, rationale[:200]  # Truncate rationale

    def _get_fallback_action(self, legal_actions: List[Action]) -> Action:
        """Get a safe fallback action when LLM fails."""
        # Priority: END_TURN > ROLL_DICE > PASS_AUCTION > first available
        priority = [
            ActionType.END_TURN,
            ActionType.ROLL_DICE,
            ActionType.PASS_AUCTION,
            ActionType.DECLINE_PURCHASE,
            ActionType.PAY_JAIL_FINE,
        ]

        for action_type in priority:
            for action in legal_actions:
                if action.action_type == action_type:
                    return action

        # Last resort: first legal action
        return legal_actions[0]

    def close(self):
        """Clean up resources."""
        if self._client:
            self._client.close()

    def __del__(self):
        """Destructor to clean up HTTP client."""
        try:
            self.close()
        except Exception:
            pass
