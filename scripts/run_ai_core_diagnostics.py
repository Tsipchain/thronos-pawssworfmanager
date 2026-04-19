#!/usr/bin/env python3
"""Run live AI Core submit diagnostics and print JSON."""

from __future__ import annotations

import argparse

from thronos_pawssworfmanager.ai_core_probe_runner import diagnostics_to_json, run_upstream_diagnostics


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe AI Core submit endpoint and classify outcomes")
    parser.add_argument("--submit-url", default="https://ai.thronoschain.org/tx/submit")
    parser.add_argument("--attestor-pubkey", default=None)
    args = parser.parse_args()

    diagnostics = run_upstream_diagnostics(args.submit_url, attestor_pubkey=args.attestor_pubkey)
    print(diagnostics_to_json(diagnostics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
