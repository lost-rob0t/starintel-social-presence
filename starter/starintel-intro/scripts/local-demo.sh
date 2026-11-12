#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cli="$root/bin/starintel"
op="${1:-intro-demo}"
# Re-running an existing operation intentionally fails rather than overwriting it.
bash "$cli" op create "$op" --mission 'Learn StarIntel using synthetic data' --phase 'learn=Create and inspect a note'
bash "$cli" doc submit "$op" training document --id intro-note --data "@$root/examples/note.json"
bash "$cli" doc get "$op" intro-note --dataset training
bash "$cli" search synthetic --op "$op" --dtype document
bash "$cli" view create training-notes --op "$op" --match '{"dtype":"document","dataset":"training"}'
bash "$cli" view use training-notes --op "$op"
bash "$cli" doc update "$op" intro-note --dataset training --patch '{"rawContent":"A synthetic training note, revised locally."}'
bash "$cli" doc history "$op" intro-note --dataset training
bash "$cli" ingest submit "$op" training --host local
