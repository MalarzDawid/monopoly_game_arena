"""
CLI for analyzing Monopoly games.
"""

import argparse
import sys
from pathlib import Path
from analyzer.game_analyzer import MonopolyGameAnalyzer
from analyzer.report_generator import ReportGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Analyze saved Monopoly games from JSONL files"
    )
    parser.add_argument(
        "file",
        type=str,
        help="Path to JSONL game file"
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=10,
        help="How many initial turns to show in detailed report (default: 10)"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Show full report"
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary only"
    )
    parser.add_argument(
        "--players",
        action="store_true",
        help="Show player statistics only"
    )
    parser.add_argument(
        "--properties",
        action="store_true",
        help="Show property analysis only"
    )
    parser.add_argument(
        "--turn-range",
        type=str,
        help="Turn range to show (e.g. '10-20')"
    )

    args = parser.parse_args()

    # Check if file exists
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ File does not exist: {args.file}")
        sys.exit(1)

    # Load and analyze game
    print(f"📂 Loading game from: {args.file}")
    print(f"⏳ Analyzing...")

    analyzer = MonopolyGameAnalyzer(args.file)
    report_gen = ReportGenerator(analyzer)

    print(f"✅ Loaded {len(analyzer.events)} events\n")

    # Generate appropriate report
    if args.full:
        print(report_gen.generate_full_report(max_turns=args.turns))
    elif args.summary:
        print(report_gen.generate_summary_report())
    elif args.players:
        print(report_gen.generate_summary_report())
        print(report_gen.generate_player_stats_report())
    elif args.properties:
        print(report_gen.generate_property_analysis())
    elif args.turn_range:
        try:
            start, end = map(int, args.turn_range.split('-'))
            print(report_gen.generate_turn_by_turn_report(start, end))
        except ValueError:
            print("❌ Invalid turn range format. Use: --turn-range 10-20")
            sys.exit(1)
    else:
        # Default: summary + stats + first N turns
        print(report_gen.generate_summary_report())
        print(report_gen.generate_player_stats_report())
        print(report_gen.generate_turn_by_turn_report(0, args.turns))


if __name__ == "__main__":
    main()
