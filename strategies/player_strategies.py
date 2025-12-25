"""
Player strategy implementations for Even/Odd game
"""
import random
from typing import List, Dict, Optional


def choose_parity_random() -> str:
    """Random strategy: randomly choose even or odd"""
    return random.choice(["even", "odd"])


def choose_parity_alternating(last_choice: Optional[str]) -> str:
    """Alternating strategy: alternate between even and odd"""
    if last_choice is None:
        return random.choice(["even", "odd"])
    return "odd" if last_choice == "even" else "even"


def choose_parity_history(game_history: List[Dict], last_choice: Optional[str]) -> str:
    """History-based strategy: choose based on past winning choices"""
    if not game_history:
        return random.choice(["even", "odd"])

    # Count recent outcomes (last 10 games)
    recent_history = game_history[-10:]
    even_wins = sum(1 for h in recent_history
                   if h.get('result') == 'win' and h.get('my_choice') == 'even')
    odd_wins = sum(1 for h in recent_history
                  if h.get('result') == 'win' and h.get('my_choice') == 'odd')

    # If no clear pattern, use alternating
    if even_wins == odd_wins:
        return choose_parity_alternating(last_choice)

    return "even" if even_wins > odd_wins else "odd"
