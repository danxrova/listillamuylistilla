import os

class Settings:
    # File Paths
    INPUT_DIR = os.getenv("INPUT_DIR", "data/inputs")
    OUTPUT_M3U = os.getenv("OUTPUT_M3U", "public/output.m3u")
    STATE_FILE = os.getenv("STATE_FILE", "data/state.json")
    REPORT_FILE = os.getenv("REPORT_FILE", "data/report.md")

    # Stream Evaluation Parameters
    TIMEOUT = int(os.getenv("TIMEOUT", "5"))  # Timeout for stream checks in seconds
    MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "20")) # Max concurrent stream checks

    # Scoring Weights (for StreamSelector)
    WEIGHTS = {
        "availability": float(os.getenv("WEIGHT_AVAILABILITY", "1000")),
        "latency": float(os.getenv("WEIGHT_LATENCY", "-100")),  # Lower latency is better
        "reliability": float(os.getenv("WEIGHT_RELIABILITY", "50")) # Based on success/fail ratio
    }

    # GitHub Actions specific
    GIT_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "github-actions[bot]@users.noreply.github.com")
    GIT_USER_NAME = os.getenv("GIT_USER_NAME", "github-actions[bot]")
