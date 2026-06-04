# Automated IPTV M3U Manager

This project provides an automated solution for managing IPTV M3U lists, specifically designed for internal, authorized, or self-owned streams. It automatically tests multiple candidate streams for a given channel, selects the best performing one based on configurable criteria, and generates an optimized M3U output file. The entire process is orchestrated using GitHub Actions.

## Features

*   **M3U Parsing:** Reads multiple M3U files from an input directory, grouping streams by channel name using fuzzy matching (normalizing names like "La 1 HD" and "La 1 (TDT)").
*   **Stream Evaluation:** Tests stream availability, latency, connection time, and basic stability.
*   **Intelligent Selection:** Selects the best stream for each channel based on a configurable weighted scoring system.
*   **Fallback Mechanism:** Stores alternative stream URLs for each channel, enabling automatic fallback if the primary stream fails in subsequent checks.
*   **Parallel Processing:** Evaluates multiple streams and channels concurrently with controlled concurrency to avoid saturating the runner.
*   **GitHub Actions Integration:** Automates the entire process on a schedule, manually, or upon changes to the input M3U file. Automatically commits updated M3U and reports.
*   **Detailed Reporting:** Generates a markdown report summarizing stream status, selected streams, and fallback actions.
*   **Configurable:** Parameters like timeouts, concurrency limits, and scoring weights are easily configurable via environment variables.

## Project Structure

```
iptv-m3u-manager/
├── .github/
│   └── workflows/
│       └── main.yml           # GitHub Actions workflow definition
├── src/
│   ├── m3u_parser.py          # Parses input M3U files
│   ├── stream_evaluator.py    # Evaluates stream quality (latency, availability)
│   ├── stream_selector.py     # Selects the best stream based on scores and manages fallback
│   ├── m3u_generator.py       # Generates the optimized output M3U and reports
│   ├── state_manager.py       # Manages persistent state (stream history, scores)
│   └── __init__.py            # Python package initializer
├── data/
│   ├── inputs/                # Directory for input M3U files (user-provided)
│   │   ├── list1.m3u
│   │   └── list2.m3u
│   ├── state.json             # Persistent state storage
│   └── report.md              # Generated stream status report
├── public/
│   └── output.m3u             # Generated optimized M3U file (Publicly accessible)
├── config/
│   └── settings.py            # Configuration settings for the application
├── main.py                    # Main script to run the pipeline
├── .gitignore                 # Git ignore file
├── LICENSE                    # Project license
└── README.md                  # This README file
```

## Getting Started

### Prerequisites

*   A GitHub account.
*   Basic understanding of M3U format and GitHub Actions.

### Installation and Setup

1.  **Fork this repository** to your GitHub account.
2.  **Clone your forked repository** to your local machine:

    ```bash
    git clone https://github.com/YOUR_USERNAME/iptv-m3u-manager.git
    cd iptv-m3u-manager
    ```

3.  **Place your input M3U files** in the `data/inputs/` directory. The system will read all `.m3u` and `.m3u8` files in this folder and group streams that belong to the same channel (e.g., "La 1 HD" and "La 1" will be treated as the same channel).

4.  **Configure GitHub Actions:** The `main.yml` workflow is set to run on a schedule (every 6 hours), manually via `workflow_dispatch`, or when any file in `data/inputs/` is pushed. You can adjust the schedule or triggers in `.github/workflows/main.yml`.

5.  **Environment Variables (Optional):** You can customize the behavior of the script by setting environment variables in your GitHub Actions workflow or locally. These are defined in `config/settings.py`.

    | Variable Name         | Description                                     | Default Value      |
    | :-------------------- | :---------------------------------------------- | :----------------- |
    | `INPUT_DIR`           | Path to the directory containing input M3U files | `data/inputs`      |
    | `OUTPUT_M3U`           | Path for the generated optimized M3U file       | `public/output.m3u` |
    | `STATE_FILE`          | Path for the persistent state JSON file         | `data/state.json`  |
    | `REPORT_FILE`         | Path for the generated markdown report          | `data/report.md`   |
    | `TIMEOUT`             | Timeout for individual stream checks (seconds)  | `5`                |
    | `MAX_CONCURRENT`      | Maximum number of concurrent stream checks      | `20`               |
    | `WEIGHT_AVAILABILITY` | Scoring weight for stream availability          | `1000`             |
    | `WEIGHT_LATENCY`      | Scoring weight for stream latency (negative for better) | `-100`             |
    | `WEIGHT_RELIABILITY`  | Scoring weight for stream reliability           | `50`               |

### Running the Workflow

*   **Manually:** Go to the 
Actions` tab in your GitHub repository, select the `Update IPTV M3U List` workflow, and click `Run workflow`.
*   **Scheduled:** The workflow will automatically run every 6 hours as configured in `.github/workflows/main.yml`.
*   **On Push:** If you modify and push changes to any file in `data/inputs/`, the workflow will automatically trigger.

## How it Works

1.  **M3U Parsing:** The `m3u_parser.py` script scans the `data/inputs/` directory for all M3U files. It normalizes channel names to group candidate streams from different sources together, even if they have slightly different naming conventions.
2.  **Stream Evaluation:** `stream_evaluator.py` uses `aiohttp` to asynchronously check the availability and measure the latency of each candidate stream. It respects `TIMEOUT` and `MAX_CONCURRENT` settings to manage load.
3.  **State Management:** `state_manager.py` loads historical data from `data/state.json`. After evaluation, it updates the success/failure counts and a short history for each stream URL.
4.  **Stream Selection:** `stream_selector.py` calculates a score for each stream based on its current evaluation and historical data, using the `WEIGHTS` defined in `config/settings.py`. It then selects the highest-scoring stream as the primary for each channel and stores all candidates for potential fallback.
5.  **M3U Generation:** `m3u_generator.py` creates `public/output.m3u` with the selected best stream for each channel. It also generates `data/report.md` with a summary of the process, including channel status and fallback information.
6.  **GitHub Actions:** The `main.yml` workflow orchestrates these steps. After execution, it checks if `public/output.m3u`, `data/state.json`, or `data/report.md` have changed. If so, it commits these changes back to the repository and pushes them. The `report.md` is also uploaded as a workflow artifact.

## Example Output

**`public/output.m3u`**

```m3u
#EXTM3U
#EXTINF:-1,La 1
http://stream2.es/stream.ts

#EXTINF:-1,Antena 3
http://stream5.es/stream.ts
```

**`data/report.md`**

```markdown
# IPTV Stream Status Report

| Channel | Status | Best Stream URL | Latency | Candidates |
| --- | --- | --- | --- | --- |
| La 1 | ✅ OK | http://stream2.es/stream.ts | 0.123s | 3 |
| Antena 3 | ✅ OK | http://stream5.es/stream.ts | 0.087s | 2 |
| Canal Test (Invalid) | ❌ DOWN | N/A | N/A | 1 |
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
