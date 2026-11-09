"""One authorized embedding request; save only sanitized verification metadata."""
import argparse
import asyncio
from datetime import datetime
import json
import logging
import math
from pathlib import Path
import sys
import time
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ai-module"))
from src.core.config import load_settings
from src.core.embeddings import open_embeddings



async def main(destination: Path):
    report = {
        "time_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
        "input_type": "one synthetic sentence, no course material",
        "input_count": 1,
        "request_attempts": 0,
        "sdk_max_retries": 0,
        "success": False,
    }
    start = time.perf_counter()
    try:
        settings = load_settings()
        report["model"] = settings.embedding_model
        async with open_embeddings(settings) as embeddings:
            original_create = embeddings.async_client.create

            async def measured_create(*args, **kwargs):
                report["request_attempts"] += 1
                response = await original_create(*args, **kwargs)
                report["returned_model"] = response.model
                report["usage"] = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                return response

            with patch.object(embeddings.async_client, "create", side_effect=measured_create):
                vectors = await embeddings.aembed_documents([
                    "This is a synthetic sentence for an embedding connection test."
                ])
            report["vector_count"] = len(vectors)
            report["dimensions"] = [len(vector) for vector in vectors]
            report["all_values_finite"] = all(math.isfinite(value) for vector in vectors for value in vector)
            report["nonzero_vector"] = bool(vectors) and any(value != 0 for value in vectors[0])
            report["success"] = (
                len(vectors) == 1 and report["dimensions"] == [1536]
                and report["all_values_finite"] and report["nonzero_vector"]
                and report["returned_model"] == settings.embedding_model
            )
    except Exception as error:
        # Never include exception message, response body, headers, or key.
        report["error_type"] = type(error).__name__
        status = getattr(error, "status_code", None)
        if isinstance(status, int):
            report["http_status"] = status
    report["elapsed_seconds"] = round(time.perf_counter() - start, 3)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live embedding smoke test: sends synthetic text and may incur API charges.")
    parser.add_argument("--run-live", action="store_true", help="Run the real API request(s); no retries.")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "ai-module/data/smoke-results/embedding.json",
                        help="Local JSON output; default path is Git-ignored.")
    args = parser.parse_args()
    if not args.run_live:
        parser.print_help()
        sys.exit(0)
    logging.disable(logging.CRITICAL)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    try:
        exit_code = asyncio.run(main(args.output))
    except Exception as error:
        # Configuration and file errors must not print credentials or full traces.
        print(json.dumps({"success": False, "error_type": type(error).__name__}))
        exit_code = 1
    sys.exit(exit_code)
