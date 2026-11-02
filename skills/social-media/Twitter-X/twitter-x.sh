#!/usr/bin/env bash
# ============================================================================
# twitter-x — X/Twitter via Cookie Authentication
# ============================================================================
# Usage: twitter-x <command> [args]
#
# Cookie: <skill_dir>/cookie.json
# Auto-login jika cookie expired (opsi 1: default, opsi 2: Tor + verifikasi)
# ============================================================================

set -euo pipefail

# Path otomatis — bisa dipake di mana saja
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COOKIE_FILE="$SKILL_DIR/cookie.json"
BEARER_TOKEN="AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
BASE_URL="https://x.com/i/api"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

die() { echo -e "${RED}✗ $*${NC}" >&2; exit 1; }
ok()  { echo -e "${GREEN}✓ $*${NC}"; }
info(){ echo -e "${CYAN}ℹ $*${NC}"; }
warn(){ echo -e "${YELLOW}⚠ $*${NC}"; }

# ──────────────────────────────────────────────────────────────
# Cookie check + auto-login
# ──────────────────────────────────────────────────────────────
ensure_cookie() {
    if [ -f "$COOKIE_FILE" ]; then
        local auth ct0 created age_days
        auth=$(jq -r '.auth_token // empty' "$COOKIE_FILE" 2>/dev/null)
        ct0=$(jq -r '.ct0 // empty' "$COOKIE_FILE" 2>/dev/null)
        created=$(jq -r '.created_at // empty' "$COOKIE_FILE" 2>/dev/null)

        if [ -n "$auth" ] && [ -n "$ct0" ]; then
            if [ -n "$created" ]; then
                local created_ts now_ts
                created_ts=$(date -d "$created" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$created" +%s 2>/dev/null || echo 0)
                now_ts=$(date +%s)
                age_days=$(( (now_ts - created_ts) / 86400 ))
                if [ "$age_days" -gt 90 ]; then
                    warn "Cookie sudah ${age_days} hari, perlu refresh"
                    auto_login
                    return
                fi
            fi
            info "Cookie valid (${age_days:-0} hari)"
            return
        fi
    fi

    warn "Cookie tidak ditemukan atau invalid"
    auto_login
}

auto_login() {
    local script_dir="$SKILL_DIR/script"
    local script1="$script_dir/x-login.js"
    local script2="$script_dir/x-login-tor-ip.js"

    # Opsi 1: Default (tanpa proxy)
    if [ -f "$script1" ]; then
        info "Opsi 1: Login default..."
        local result
        result=$(node "$script1" 2>&1) || true
        local exit_code=$?

        if [ $exit_code -eq 0 ]; then
            ok "Login berhasil (default)"
            return
        fi

        # Jika verifikasi diperlukan atau rate limited, coba opsi 2
        if echo "$result" | grep -q "VERIFICATION_DIPERLUKAN\|RATE_LIMITED"; then
            warn "Opsi 1 gagal: $(echo "$result" | tail -1)"

            # Opsi 2: Tor + auto-verifikasi
            if [ -f "$script2" ]; then
                info "Opsi 2: Login via Tor + auto-verifikasi..."
                result=$(node "$script2" 2>&1) || true
                exit_code=$?

                if [ $exit_code -eq 0 ]; then
                    ok "Login berhasil (Tor + verifikasi)"
                    return
                fi

                die "Login gagal: $(echo "$result" | tail -1)"
            else
                die "Script opsi 2 tidak ditemukan: $script2"
            fi
        else
            die "Login gagal: $(echo "$result" | tail -1)"
        fi
    else
        die "Login script tidak ditemukan: $script1"
    fi
}

# ──────────────────────────────────────────────────────────────
# API helpers
# ──────────────────────────────────────────────────────────────
load_cookies() {
    AUTH_TOKEN=$(jq -r '.auth_token' "$COOKIE_FILE" 2>/dev/null)
    CT0=$(jq -r '.ct0' "$COOKIE_FILE" 2>/dev/null)
    [ -n "$AUTH_TOKEN" ] && [ "$AUTH_TOKEN" != "null" ] || die "auth_token invalid"
    [ -n "$CT0" ] && [ "$CT0" != "null" ] || die "ct0 invalid"
}

api_get() {
    load_cookies
    curl -sS "$BASE_URL$1" \
        -H "Cookie: auth_token=$AUTH_TOKEN; ct0=$CT0" \
        -H "X-Csrf-Token: $CT0" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" \
        -H "Content-Type: application/json" "${@:2}"
}

api_post() {
    load_cookies
    curl -sS -X POST "$BASE_URL$1" \
        -H "Cookie: auth_token=$AUTH_TOKEN; ct0=$CT0" \
        -H "X-Csrf-Token: $CT0" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" \
        -H "Content-Type: application/json" \
        -d "$2"
}

extract_user_id() {
    local handle="${1#@}"
    load_cookies
    local result
    result=$(curl -sS -X POST "https://x.com/i/api/graphql/G3KGOASz96M-Qu0nwmGXNg" \
        -H "Cookie: auth_token=$AUTH_TOKEN; ct0=$CT0" \
        -H "X-Csrf-Token: $CT0" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"variables\":{\"screen_name\":\"$handle\",\"withSafetyModeUserFields\":true}}")
    echo "$result" | jq -r '.data.user.result.rest_id // empty'
}

# ──────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────
cmd_auth_status() {
    if [ ! -f "$COOKIE_FILE" ]; then
        warn "Cookie tidak ada"
        info "Jalankan: twitter-x login"
        return 1
    fi
    load_cookies
    echo -e "${GREEN}✓ Cookie tersedia${NC}"
    echo -e "  auth_token: ${AUTH_TOKEN:0:10}...${AUTH_TOKEN: -4}"
    echo -e "  ct0: ${CT0:0:10}...${CT0: -4}"

    local me
    me=$(api_get "/1.1/account/verify_credentials.json" 2>/dev/null) || true
    local name
    name=$(echo "$me" | jq -r '.screen_name // empty' 2>/dev/null) || true
    if [ -n "$name" ]; then
        echo -e "  ${GREEN}✓ Login: @$name${NC}"
    else
        echo -e "  ${YELLOW}⚠ Cookie mungkin expired${NC}"
    fi
}

cmd_login() {
    auto_login
    cmd_auth_status
}

cmd_post() {
    local text="$1"
    local payload="{\"variables\":{\"tweet_text\":\"$text\"},\"features\":{\"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled\":true}}"
    local result
    result=$(api_post "/graphql/a1p9RWpkYKBjWv_I3Wz1-A/CreateTweet" "$payload")
    local id
    id=$(echo "$result" | jq -r '.data.create_tweet.tweet_results.result.rest_id // empty')
    if [ -n "$id" ]; then
        ok "Posted: https://x.com/i/status/$id"
    else
        die "Gagal post: $(echo "$result" | jq -r '.errors[0].message // .message // "unknown"')"
    fi
}

cmd_reply() {
    local post_id="$1" text="$2"
    local payload="{\"variables\":{\"tweet_text\":\"$text\",\"reply\":{\"in_reply_to_tweet_id\":\"$post_id\",\"exclude_reply_user_ids\":[]}},\"features\":{\"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled\":true}}"
    local result
    result=$(api_post "/graphql/a1p9RWpkYKBjWv_I3Wz1-A/CreateTweet" "$payload")
    local id
    id=$(echo "$result" | jq -r '.data.create_tweet.tweet_results.result.rest_id // empty')
    if [ -n "$id" ]; then ok "Replied: https://x.com/i/status/$id"; else die "Gagal reply"; fi
}

cmd_delete() {
    local payload="{\"variables\":{\"tweet_id\":\"$1\"}}"
    local result
    result=$(api_post "/graphql/k2VpJQ1bT8JNBeYGQ_8i6w/DeleteTweet" "$payload")
    if echo "$result" | jq -e '.data.delete_tweet' &>/dev/null; then ok "Deleted: $1"; else die "Gagal delete"; fi
}

cmd_like() {
    local payload="{\"variables\":{\"tweet_id\":\"$1\"}}"
    local result
    result=$(api_post "/graphql/lI07N6Otwv1PhnEgXILM7A/FavoriteTweet" "$payload")
    if echo "$result" | jq -e '.data.favorite_tweet' &>/dev/null; then ok "Liked: $1"; else die "Gagal like"; fi
}

cmd_unlike() {
    local payload="{\"variables\":{\"tweet_id\":\"$1\"}}"
    local result
    result=$(api_post "/graphql/ZYKSe-w7KEslx3JhSIk6LA/UnfavoriteTweet" "$payload")
    if echo "$result" | jq -e '.data.unfavorite_tweet' &>/dev/null; then ok "Unliked: $1"; else die "Gagal unlike"; fi
}

cmd_repost() {
    local payload="{\"variables\":{\"source_tweet_id\":\"$1\"}}"
    local result
    result=$(api_post "/graphql/ojPdsZsimiJrUGLR1sjUiA/CreateRetweet" "$payload")
    if echo "$result" | jq -e '.data.create_retweet' &>/dev/null; then ok "Reposted: $1"; else die "Gagal repost"; fi
}

cmd_follow() {
    local handle="${1#@}"
    local uid
    uid=$(extract_user_id "$handle")
    [ -n "$uid" ] || die "User @$handle tidak ditemukan"
    local payload="{\"variables\":{\"user_id\":\"$uid\"}}"
    local result
    result=$(api_post "/graphql/i5yNFzXFKP38qLFTLHBYjA/CreateFriendship" "$payload")
    if echo "$result" | jq -e '.data.follow' &>/dev/null; then ok "Followed @$handle"; else die "Gagal follow"; fi
}

cmd_whoami() {
    load_cookies
    local me
    me=$(api_get "/1.1/account/verify_credentials.json")
    echo "$me" | jq '{id,name,screen_name,followers: .followers_count,following: .friends_count,tweets: .statuses_count}'
}

cmd_search() {
    local query="$1" limit="${2:-10}"
    local encoded
    encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query'))" 2>/dev/null || echo "$query")
    api_get "/2/search/recent?query=$encoded&max_results=$limit&tweet.fields=created_at,author_id,public_metrics" | jq '.data // .errors // .'
}

cmd_dm() {
    local handle="${1#@}" text="$2"
    local uid
    uid=$(extract_user_id "$handle")
    [ -n "$uid" ] || die "User @$handle tidak ditemukan"
    local payload="{\"variables\":{\"conversation_id\":null,\"recipient_ids\":[\"$uid\"],\"text\":\"$text\"}}"
    local result
    result=$(api_post "/graphql/7s4z2YCRpGqZiMvNQbXKSw/SendDM" "$payload")
    if echo "$result" | jq -e '.data.send_dm' &>/dev/null; then ok "DM sent to @$handle"; else die "Gagal DM"; fi
}

cmd_user() {
    local handle="${1#@}"
    load_cookies
    curl -sS -X POST "https://x.com/i/api/graphql/G3KGOASz96M-Qu0nwmGXNg" \
        -H "Cookie: auth_token=$AUTH_TOKEN; ct0=$CT0" \
        -H "X-Csrf-Token: $CT0" \
        -H "Authorization: Bearer $BEARER_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"variables\":{\"screen_name\":\"$handle\",\"withSafetyModeUserFields\":true}}" | jq '.data.user.result // .errors // .'
}

cmd_raw() {
    local method="$1" path="$2" body="${3:-}"
    if [ "$method" = "GET" ]; then api_get "$path"; else api_post "$path" "$body"; fi
}

# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────
CMD="${1:-help}"
shift || true

case "$CMD" in
    help|--help|-h|auth|login) ;;
    *) ensure_cookie ;;
esac

case "$CMD" in
    auth)       cmd_auth_status ;;
    login)      cmd_login ;;
    post)       cmd_post "$@" ;;
    reply)      cmd_reply "$@" ;;
    delete)     cmd_delete "$@" ;;
    search)     cmd_search "$@" ;;
    timeline)   api_get "/2/users/me/timeline?max_results=${1:-20}" | jq '.data // .' ;;
    mentions)   api_get "/2/users/me/mentions?max_results=${1:-10}" | jq '.data // .' ;;
    like)       cmd_like "$@" ;;
    unlike)     cmd_unlike "$@" ;;
    repost)     cmd_repost "$@" ;;
    whoami)     cmd_whoami ;;
    user)       cmd_user "$@" ;;
    follow)     cmd_follow "$@" ;;
    dm)         cmd_dm "$@" ;;
    raw)        cmd_raw "$@" ;;
    help|--help|-h)
        echo "twitter-x — X/Twitter via Cookie"
        echo ""
        echo "Usage: twitter-x <command> [args]"
        echo ""
        echo "Commands:"
        echo "  login              Login / refresh cookie"
        echo "  auth status        Cek cookie"
        echo "  post \"text\"        Post tweet"
        echo "  reply ID \"text\"    Reply"
        echo "  delete ID          Delete"
        echo "  search \"q\" [-n N]  Search"
        echo "  timeline [-n N]    Home timeline"
        echo "  mentions [-n N]    Mentions"
        echo "  like ID            Like"
        echo "  unlike ID          Unlike"
        echo "  repost ID          Repost"
        echo "  whoami             Info akun"
        echo "  user @handle       Info user"
        echo "  follow @handle     Follow"
        echo "  dm @handle \"msg\"   Kirim DM"
        echo "  raw METHOD /path   Raw API"
        echo ""
        echo "Skill dir: $SKILL_DIR"
        ;;
    *)
        die "Unknown: $CMD. Coba: twitter-x help"
        ;;
esac
