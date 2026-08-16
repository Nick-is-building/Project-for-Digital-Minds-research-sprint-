#!/bin/bash
# Checks the stop conditions every 2 minutes and stops the run if any trips.
#
# The run's pid is read from systemd on every pass. Two earlier ways of getting
# it were both wrong: `$!` after `nohup ... &` inside a wrapper shell returns the
# WRAPPER's pid, so the signal would have gone to a bash that was not making API
# calls and the run would have carried on through a tripped stop condition; and
# `pgrep -f` matches the short-lived sandbox subprocesses that fork with the same
# cmdline, so it can return more than one pid. MainPID is unambiguous.
#
# SIGINT and not SIGKILL: run_main.py catches KeyboardInterrupt, so the raw log,
# solutions and observations written so far stay intact and the run is resumable.

cd "$(dirname "$0")" || exit 1

while true; do
    pid=$(systemctl --user show digitalminds-mainrun.service -p MainPID --value)
    if [ -z "$pid" ] || [ "$pid" = "0" ]; then
        echo "=== run not found $(date -Is); watchdog exiting ==="
        exit 0
    fi
    if ! python3 -u monitor_run.py > pilot/out/watchdog_last.txt 2>&1; then
        echo "=== STOP CONDITION TRIPPED $(date -Is) ==="
        cat pilot/out/watchdog_last.txt
        kill -INT "$pid"
        exit 1
    fi
    sleep 120
done
