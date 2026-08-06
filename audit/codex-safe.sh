#!/bin/bash
# codex-safe.sh — strip credentials before invoking an external agent CLI.
#
# See review-loops.md §4. A hardcoded unset-list silently rots as new secrets
# are added to your .env, so this strips by NAME PATTERN first and then unsets
# the known-name exceptions that don't match a pattern (e.g. DATABASE_URL).
set -euo pipefail

# Any var whose name looks credential-bearing.
PATTERN='(SECRET|TOKEN|API_?KEY|PASSWORD|PASSWD|CREDENTIAL|PRIVATE_KEY|ACCESS_KEY|AUTH)'

# Explicit names that carry secrets but don't match the pattern above.
EXTRA=(
  DATABASE_URL TEST_DATABASE_URL REDIS_URL
  AUTH_GOOGLE_ID AWS_SESSION_TOKEN
)

unset_args=()
while IFS='=' read -r name _; do
  [[ "$name" =~ $PATTERN ]] && unset_args+=(-u "$name")
done < <(env)

for name in "${EXTRA[@]}"; do
  unset_args+=(-u "$name")
done

exec env "${unset_args[@]}" codex "$@"
