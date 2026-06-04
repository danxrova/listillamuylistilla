import asyncio
import os
import time
from src.m3u_parser import M3UParser
from src.stream_evaluator import StreamEvaluator
from src.stream_selector import StreamSelector
from src.m3u_generator import M3UGenerator
from src.state_manager import StateManager
from config.settings import Settings

async def run_pipeline():
    # Configuration from Settings class
    INPUT_DIR = Settings.INPUT_DIR
    OUTPUT_M3U = Settings.OUTPUT_M3U
    STATE_FILE = Settings.STATE_FILE
    REPORT_FILE = Settings.REPORT_FILE
    TIMEOUT = Settings.TIMEOUT
    MAX_CONCURRENT = Settings.MAX_CONCURRENT

    print(f"Starting IPTV M3U Manager...")
    print(f"Input Directory: {INPUT_DIR}")
    
    # 1. Parse M3U files
    parser = M3UParser(INPUT_DIR)
    channels = parser.parse_all()
    print(f"Parsed {len(channels)} channels.")

    # 2. Evaluate Streams
    evaluator = StreamEvaluator(timeout=TIMEOUT, max_concurrent=MAX_CONCURRENT)
    channels = await evaluator.evaluate_all(channels)
    print(f"Evaluated all streams.")

    # 3. Update State
    state_manager = StateManager(STATE_FILE)
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    for channel in channels:
        for evaluation in channel['evaluations']:
            evaluation['timestamp'] = timestamp
            state_manager.update_stream_history(evaluation['url'], evaluation)
    state_manager.save_state()
    print(f"Updated state history.")

    # 4. Select Best Streams
    selector = StreamSelector(weights=Settings.WEIGHTS)
    channels = selector.select_best_streams(channels, state_manager)
    print(f"Selected best streams.")

    # 5. Generate Output
    generator = M3UGenerator(OUTPUT_M3U)
    generator.generate(channels)
    generator.generate_fallback_report(channels, REPORT_FILE)
    print(f"Generated output M3U and report.")
    print(f"Done! Optimized list saved to {OUTPUT_M3U}")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
