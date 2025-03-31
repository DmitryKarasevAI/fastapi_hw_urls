#!/usr/bin/env bash
# wait-for-it.sh


TIMEOUT=5
QUIET=0

echoerr() {
    if [ "$QUIET" -ne 1 ]; then echo "$@" 1>&2; fi
}

usage() {
    echo "Usage: $0 host:port [-t timeout] [-- command args]"
    exit 1
}

if [ -z "$1" ]; then
    usage
fi
HOST=$(echo "$1" | cut -d: -f1)
PORT=$(echo "$1" | cut -d: -f2)
shift

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --)
            shift
            break
            ;;
        *)
            break
            ;;
    esac
done

echo "Waiting for $HOST:$PORT (timeout: $TIMEOUT seconds)..."

start_ts=$(date +%s)
while true; do
    if timeout 1 bash -c "</dev/tcp/$HOST/$PORT" 2>/dev/null; then
        echo "$HOST:$PORT is available"
        break
    fi

    sleep 1
    now_ts=$(date +%s)
    if [ $(( now_ts - start_ts )) -ge $TIMEOUT ]; then
        echoerr "Timeout after waiting $TIMEOUT seconds for $HOST:$PORT"
        exit 1
    fi
done

if [ "$#" -gt 0 ]; then
    exec "$@"
else
    exit 0
fi