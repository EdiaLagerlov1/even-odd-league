"""
Core League Manager methods for standings, stats, and match updates
"""
from typing import Dict, List, Optional, Any
from models.league_models import MatchStatus
import uuid
import logging

logger = logging.getLogger(__name__)


class LeagueManagerCore:
    """Mixin class for LeagueManager with additional methods"""

    def update_match_result(self, match_id: str, result: Dict[str, Any]):
        """
        Process match result from referee and update league standings.

        Updates match status, player win/loss/draw records, points, and broadcasts
        standings updates. Also checks for round and league completion.

        Args:
            match_id: ID of the completed match
            result: Result dictionary containing:
                - winner: Player ID of winner or None for draw
                - score: Dict mapping player IDs to points earned
                - details: Additional game information
        """
        # Find the match in league schedule
        match = self.matches.get(match_id)
        if not match:
            raise ValueError(f"Match {match_id} not found")

        # Mark match as completed and store result
        match.status = MatchStatus.COMPLETED
        match.result = result

        # Extract result data
        winner = result.get("winner")
        player1_id = match.player1_id
        player2_id = match.player2_id

        # Get player objects to update their stats
        player1 = self.players[player1_id]
        player2 = self.players[player2_id]

        # Update win/loss/draw counts based on match outcome
        if winner == player1_id:
            # Player 1 wins
            player1.wins += 1
            player2.losses += 1
        elif winner == player2_id:
            # Player 2 wins
            player2.wins += 1
            player1.losses += 1
        elif winner is None:
            # Draw - both players get a draw
            player1.draws += 1
            player2.draws += 1

        # Update points from score dictionary (3 for win, 1 for draw, 0 for loss)
        score = result.get("score", {})
        if player1_id in score:
            player1.total_points_earned += score[player1_id]
        if player2_id in score:
            player2.total_points_earned += score[player2_id]

        logger.info(f"Match {match_id} completed: {result}")

        # Broadcast updated standings to all participants
        from utils.league_utils import create_base_message
        standings_message = create_base_message("LEAGUE_STANDINGS_UPDATE", str(uuid.uuid4()))
        standings_message["league_id"] = "league_2025_even_odd"
        standings_message["round_id"] = match.round_id
        standings_message["standings"] = self.get_standings()
        self.broadcast_to_all(standings_message)

        # Check if all matches in this round are complete
        if self.check_round_complete(match.round_id):
            # Count total matches in this round
            round_matches = [m for m in self.schedule if m.round_id == match.round_id]
            matches_played = len(round_matches)

            # Determine if there's a next round (None if this was the last round)
            next_round_id = match.round_id + 1 if match.round_id < self.total_rounds else None

            # Broadcast ROUND_COMPLETED notification
            round_complete_message = create_base_message("ROUND_COMPLETED", str(uuid.uuid4()))
            round_complete_message["league_id"] = "league_2025_even_odd"
            round_complete_message["round_id"] = match.round_id
            round_complete_message["matches_played"] = matches_played
            round_complete_message["next_round_id"] = next_round_id
            self.broadcast_to_all(round_complete_message)
            logger.info(f"Round {match.round_id} completed")

        # Check if all matches in the league are complete
        if self.check_league_complete() and not self.league_completed:
            self.league_completed = True

            # Get full standings with all player statistics
            full_standings = self.get_standings()

            # Extract champion information (first place player)
            champion = None
            if full_standings:
                top_player = full_standings[0]  # Standings are already sorted
                champion = {
                    "player_id": top_player["player_id"],
                    "display_name": top_player["display_name"],
                    "points": top_player["points"]
                }

            # Create simplified final standings (only rank, player_id, points)
            # This is a condensed version of the full standings
            final_standings = [
                {
                    "rank": standing["rank"],
                    "player_id": standing["player_id"],
                    "points": standing["points"]
                }
                for standing in full_standings
            ]

            # Broadcast LEAGUE_COMPLETED notification with final results
            league_complete_message = create_base_message("LEAGUE_COMPLETED", str(uuid.uuid4()))
            league_complete_message["league_id"] = "league_2025_even_odd"
            league_complete_message["total_rounds"] = self.total_rounds
            league_complete_message["total_matches"] = len(self.schedule)
            league_complete_message["champion"] = champion
            league_complete_message["final_standings"] = final_standings
            self.broadcast_to_all(league_complete_message)
            logger.info("League completed")

    def get_standings(self) -> List[Dict[str, Any]]:
        """
        Calculate and return current league standings sorted by performance.

        Creates a list of player standings with statistics, sorted by:
        1. Total points (primary)
        2. Wins (tiebreaker)
        3. Draws (secondary tiebreaker)

        Returns:
            List of dictionaries, each containing:
                - rank: Player's position (1-indexed)
                - player_id: Unique player identifier
                - display_name: Player's display name
                - played: Total matches played
                - wins: Number of wins
                - draws: Number of draws
                - losses: Number of losses
                - points: Total points earned
        """
        standings = []

        # Build standings list with player statistics
        for player_id, player in self.players.items():
            # Calculate total matches played
            played = player.wins + player.losses + player.draws

            standings.append({
                "player_id": player_id,
                "display_name": player.metadata.display_name,
                "played": played,
                "wins": player.wins,
                "draws": player.draws,
                "losses": player.losses,
                "points": player.total_points_earned
            })

        # Sort standings: primary by points, then by wins, then by draws (all descending)
        # Higher points = better rank, more wins breaks ties, more draws breaks further ties
        standings.sort(key=lambda x: (x["points"], x["wins"], x["draws"]), reverse=True)

        # Assign rank based on sorted position (1 = first place)
        for rank, standing in enumerate(standings, start=1):
            standing["rank"] = rank

        return standings

    def get_schedule_data(self) -> List[Dict[str, Any]]:
        """Get schedule data"""
        schedule_data = []
        for match in self.schedule:
            schedule_data.append({
                "match_id": match.match_id,
                "round_id": match.round_id,
                "player1_id": match.player1_id,
                "player2_id": match.player2_id,
                "referee_id": match.referee_id,
                "status": match.status.value
            })
        return schedule_data

    def get_next_match(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Get next pending match for a player"""
        for match in self.schedule:
            if match.status == MatchStatus.PENDING:
                if match.player1_id == player_id or match.player2_id == player_id:
                    return {
                        "match_id": match.match_id,
                        "round_id": match.round_id,
                        "player1_id": match.player1_id,
                        "player2_id": match.player2_id,
                        "referee_id": match.referee_id
                    }
        return None

    def get_player_stats(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific player"""
        player = self.players.get(player_id)
        if not player:
            return None

        return {
            "player_id": player_id,
            "display_name": player.metadata.display_name,
            "wins": player.wins,
            "losses": player.losses,
            "draws": player.draws,
            "total_points_earned": player.total_points_earned,
            "total_points_lost": player.total_points_lost,
            "total_games": player.wins + player.losses + player.draws
        }

    def is_round_completed(self, round_id: int) -> bool:
        """Check if all matches in a round are completed"""
        round_matches = [m for m in self.schedule if m.round_id == round_id]
        return all(m.status == MatchStatus.COMPLETED for m in round_matches)

    def is_league_completed(self) -> bool:
        """Check if all matches are completed"""
        return all(m.status == MatchStatus.COMPLETED for m in self.schedule)
