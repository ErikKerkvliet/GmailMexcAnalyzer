import json
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SimulationResult:
    """Holds the results of a single strategy's average performance."""
    stop_loss_roi: float
    take_profit_roi: float
    avg_roi: float = 0.0
    win_rate: float = 0.0
    risk_reward_ratio: float = 0.0


class PositionOptimizer:
    """
    Analyzes trading positions to recommend or simulate SL/TP ROI levels.
    """

    def __init__(self, position_data: List[Dict]):
        if not isinstance(position_data, list):
            raise TypeError("position_data must be a list of order dicts.")
        self.orders = position_data
        self.total_positions = len(self.orders)

    def _simulate_single_order(self, order: Dict, sl_roi_pct: float, tp_roi_pct: float) -> float:
        """Simulates a single trade, returning the ROI. Uses float('inf') for unused SL/TP."""
        direction = order.get("direction", "long")
        leverage = float(order.get('leverage', '1x').replace('x', '')) or 1
        sl_price_pct, tp_price_pct = sl_roi_pct / leverage, tp_roi_pct / leverage
        entry_price = order['entry']

        sl_price = entry_price * (1 - sl_price_pct / 100.0) if direction == 'long' else entry_price * (
                    1 + sl_price_pct / 100.0)
        tp_price = entry_price * (1 + tp_price_pct / 100.0) if direction == 'long' else entry_price * (
                    1 - tp_price_pct / 100.0)

        for candle in order['price_data']:
            if direction == 'long':
                if candle['low'] <= sl_price: return -sl_roi_pct
                if candle['high'] >= tp_price: return tp_roi_pct
            else:  # Short
                if candle['high'] >= sl_price: return -sl_roi_pct
                if candle['low'] <= tp_price: return tp_roi_pct

        return order.get('pnl_pct', 0.0) * leverage

    def simulate_average_performance(self, sl_roi_pct: float, tp_roi_pct: float) -> SimulationResult:
        """Calculates the average performance of a strategy across all trades."""
        result = SimulationResult(stop_loss_roi=sl_roi_pct, take_profit_roi=tp_roi_pct)
        roi_results = [self._simulate_single_order(o, sl_roi_pct, tp_roi_pct) for o in self.orders]
        if not roi_results: return result

        wins = sum(1 for r in roi_results if r > 0)
        result.win_rate = (wins / self.total_positions) * 100
        result.avg_roi = np.mean(roi_results)
        if sl_roi_pct > 0 and sl_roi_pct != float('inf'):
            result.risk_reward_ratio = tp_roi_pct / sl_roi_pct
        return result

    def get_recommendations(self) -> Dict[str, SimulationResult]:
        """Performs a grid search to find optimal ROI strategies based on average performance."""
        sl_range, tp_range = np.arange(10, 101, 5), np.arange(10, 201, 10)
        results = [self.simulate_average_performance(sl, tp) for sl in sl_range for tp in tp_range if tp / sl >= 1.0]
        if not results: return {}

        results.sort(key=lambda r: (r.win_rate * 0.6) + (r.avg_roi * 0.4), reverse=True)
        optimal = results[0]
        conservative = sorted([r for r in results if r.win_rate >= 80], key=lambda r: r.win_rate, reverse=True)
        aggressive = sorted([r for r in results if r.avg_roi > 0], key=lambda r: r.risk_reward_ratio, reverse=True)

        return {
            "optimal": optimal,
            "conservative": conservative[0] if conservative else results[0],
            "aggressive": aggressive[0] if aggressive else results[-1]
        }


def run_and_print_portfolio_simulation(optimizer: PositionOptimizer, capital: float, cost: float, sl_roi: float,
                                       tp_roi: float, max_order_ratio: float):
    """Performs a sequential, compounding portfolio backtest and prints the results."""
    print("\n" + "=" * 70 + "\nPORTFOLIO SIMULATION REPORT\n" + "=" * 70)
    sl_text = f"{sl_roi:.2f}%" if sl_roi != float('inf') else "N/A"
    tp_text = f"{tp_roi:.2f}%" if tp_roi != float('inf') else "N/A"
    print(f"Strategy: SL ROI @ {sl_text} | TP ROI @ {tp_text}")
    print(f"Initial Capital: ${capital:,.2f}")
    print(f"Max Capital per Order: {max_order_ratio:.2f}%")
    print("-" * 70)

    current_capital, wins, losses = capital, 0, 0
    total_trades = len(optimizer.orders)

    for i, order in enumerate(optimizer.orders):
        if current_capital <= 0:
            print(f"Portfolio wiped out after trade {i}. Simulation stopped.")
            break

        capital_at_risk = current_capital * (max_order_ratio / 100.0)
        trade_roi = optimizer._simulate_single_order(order, sl_roi, tp_roi)
        net_pnl_usdt = (capital_at_risk * (trade_roi / 100.0)) - cost
        current_capital += net_pnl_usdt

        if net_pnl_usdt > 0:
            wins += 1
        else:
            losses += 1

    print(f"Trades Simulated: {total_trades}\nWins: {wins} | Losses: {losses}")
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    print(f"Win Rate: {win_rate:.2f}%")

    net_gain_loss = current_capital - capital
    total_return_pct = (net_gain_loss / capital) * 100 if capital > 0 else 0

    print(f"\nFinal Capital: ${current_capital:,.2f}")
    print(f"Net Gain/Loss: ${net_gain_loss:,.2f} ({total_return_pct:+.2f}%)")
    print("=" * 70)


def print_recommendations(recs: Dict, capital: float, cost: float):
    """Prints the strategy recommendations found by the grid search."""
    print("\n" + "=" * 70 + "\nOPTIMIZER STRATEGY RECOMMENDATIONS (THEORETICAL)\n" + "=" * 70)
    print(
        "These strategies are based on average ROI. Use them as a starting point\nand test them with the portfolio simulator.\n")
    for name, result in recs.items():
        print(f"--- {name.upper()} STRATEGY ---")
        print(f"  Stop-Loss ROI:      {result.stop_loss_roi:.2f}%")
        print(f"  Take-Profit ROI:    {result.take_profit_roi:.2f}%")
        print(f"  Risk/Reward:        {result.risk_reward_ratio:.2f}:1")
        print(f"  Win Rate:           {result.win_rate:.2f}%")
        cost_impact_pct = (cost / (
                    capital * 0.1)) * 100 if capital > 0 else 0  # Assume 10% capital per trade for estimation
        net_avg_roi = result.avg_roi - cost_impact_pct
        print(f"  Est. Avg Net ROI:   {net_avg_roi:+.2f}% per trade")
        print("-" * 25)


def import_position_data(file_path: str) -> List[Dict]:
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data.get('orders', [data])
    except (FileNotFoundError, json.JSONDecodeError, TypeError) as e:
        print(f"Error loading data file: {e}");
        return []


def run_analysis(file_path: str, capital: float, cost: float, sl_roi: Optional[float], tp_roi: Optional[float],
                 max_order_ratio: Optional[float]):
    position_data = import_position_data(file_path)
    if not position_data: return
    optimizer = PositionOptimizer(position_data)

    # If any strategy parameter is provided, run the detailed portfolio simulation.
    if sl_roi is not None or tp_roi is not None or max_order_ratio is not None:
        print("Mode: Running portfolio simulation...")
        sl = abs(sl_roi) if sl_roi is not None else float('inf')
        tp = abs(tp_roi) if tp_roi is not None else float('inf')
        ratio = max_order_ratio if max_order_ratio is not None and max_order_ratio > 0 else 10.0
        if max_order_ratio is None:
            print(f"Info: 'Max Order Ratio' not set, defaulting to {ratio:.2f}% for simulation.")
        run_and_print_portfolio_simulation(optimizer, capital, cost, sl, tp, ratio)

    # Otherwise, run the grid search to find strategy recommendations.
    else:
        print("Mode: Running grid search to find optimal strategies...")
        recommendations = optimizer.get_recommendations()
        if recommendations:
            print_recommendations(recommendations, capital, cost)
        else:
            print("Could not generate recommendations.")


if __name__ == "__main__":
    run_analysis(
        file_path='order_rates/your_data.json',
        capital=1000.0,
        cost=1.0,
        sl_roi=None,
        tp_roi=None,
        max_order_ratio=None  # This triggers optimization mode
    )