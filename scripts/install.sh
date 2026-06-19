#!/bin/bash
# ============================================================================
# ChiperFlux Agent Installer
# Crack BY : I'AMTUBASYA
# Original hermes-Agent from Nous-Research
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Default values
REPO_URL_HTTPS="https://github.com/iamtubasya/chiper-agent.git"
BRANCH="main"
INSTALL_DIR="/usr/local/lib/chiper-agent"
CHIPER_HOME="${CHIPER_HOME:-$HOME/.chiperflux}"
IS_INTERACTIVE=false
IS_TERMUX=false
SKIP_BROWSER=false
RUN_SETUP=true
USE_VENV=true

# ============================================================================
# Helper Functions
# ============================================================================

log_step() {
    echo -e "\n${CYAN}${BOLD}$1${NC}"
}

log_info() {
    echo -e "  ${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "  ${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "  ${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "  ${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Banner
# ============================================================================

show_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║            ⚕️  ChiperFlux Agent Installer                    ║"
    echo "║                                                              ║"
    echo "║   Crack BY : I'AMTUBASYA                                    ║"
    echo "║   Original hermes-Agent from Nous-Research                   ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ============================================================================
# Parse Arguments
# ============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --branch)
                BRANCH="$2"
                shift 2
                ;;
            --no-venv)
                USE_VENV=false
                shift
                ;;
            --skip-browser)
                SKIP_BROWSER=true
                shift
                ;;
            --skip-setup)
                RUN_SETUP=false
                shift
                ;;
            --yes|-y)
                IS_INTERACTIVE=false
                shift
                ;;
            --help|-h)
                echo "Usage: install.sh [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --dir DIR         Installation directory (default: /usr/local/lib/chiper-agent)"
                echo "  --branch BRANCH   Git branch to install (default: main)"
                echo "  --no-venv         Skip virtual environment"
                echo "  --skip-browser    Skip browser installation"
                echo "  --skip-setup      Skip setup wizard"
                echo "  --yes, -y         Non-interactive mode"
                echo "  --help, -h        Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# ============================================================================
# Detect Environment
# ============================================================================

detect_os() {
    log_step "🔍 Detecting environment..."

    if [[ "$(uname)" == "Linux" ]]; then
        if [[ -f /etc/os-release ]]; then
            . /etc/os-release
            case "$ID" in
                ubuntu|debian)
                    log_info "Detected: Debian/Ubuntu"
                    ;;
                fedora|rhel|centos)
                    log_info "Detected: RHEL/Fedora"
                    ;;
                arch|manjaro)
                    log_info "Detected: Arch Linux"
                    ;;
                *)
                    log_info "Detected: Linux ($ID)"
                    ;;
            esac
        else
            log_info "Detected: Linux (unknown distro)"
        fi
    elif [[ "$(uname)" == "Darwin" ]]; then
        log_info "Detected: macOS"
    fi

    # Check for Termux
    if [[ -d /data/data/com.termux ]]; then
        IS_TERMUX=true
        log_info "Environment: Termux (Android)"
    fi

    # Check if interactive
    if [[ -t 0 ]]; then
        IS_INTERACTIVE=true
    fi

    sleep 2
}

# ============================================================================
# Install System Dependencies
# ============================================================================

install_dependencies() {
    log_step "📦 Installing system dependencies..."

    if [[ "$IS_TERMUX" == true ]]; then
        pkg update -y
        pkg install -y python git nodejs
    elif command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv git nodejs npm curl wget
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y python3 python3-pip git nodejs npm curl wget
    elif command -v pacman &> /dev/null; then
        sudo pacman -Syu --noconfirm python python-pip git nodejs npm curl wget
    elif command -v brew &> /dev/null; then
        brew install python git node curl wget
    else
        log_warn "Unknown package manager. Please install manually: python3, git, nodejs, npm"
    fi

    log_success "System dependencies installed"
    sleep 2
}

# ============================================================================
# Install Python/UV
# ============================================================================

install_python() {
    log_step "🐍 Setting up Python..."

    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        log_info "Python: $PYTHON_VERSION"
    else
        log_error "Python3 not found!"
        exit 1
    fi

    # Install UV if not present
    if ! command -v uv &> /dev/null; then
        log_info "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    else
        log_info "uv already installed"
    fi

    log_success "Python ready"
    sleep 2
}

# ============================================================================
# Clone Repository
# ============================================================================

clone_repo() {
    log_step "📥 Instalasi Chiper-Agent repository..."

    if [ -d "$INSTALL_DIR" ]; then
        log_warn "Installation directory exists: $INSTALL_DIR"
        log_info "Updating existing installation..."
        cd "$INSTALL_DIR"
        git fetch origin
        git checkout "$BRANCH"
        git pull origin "$BRANCH"
    else
        log_info "Cloning to: $INSTALL_DIR"
        git clone --branch "$BRANCH" "$REPO_URL_HTTPS" "$INSTALL_DIR"
    fi

    log_success "Repository ready"
    sleep 2
}

# ============================================================================
# Virtual Environment
# ============================================================================

setup_venv() {
    if [ "$USE_VENV" = false ]; then
        log_info "Skipping venv (--no-venv)"
        return
    fi

    log_step "🔧 Setting up virtual environment..."

    cd "$INSTALL_DIR"

    if [ "$IS_TERMUX" = true ]; then
        # Termux: use stdlib venv
        python -m venv venv
        source venv/bin/activate
        pip install -e ".[termux]"
    else
        # Desktop/Server: use uv
        uv venv
        source .venv/bin/activate
        uv pip install -e ".[all]"
    fi

    log_success "Virtual environment ready"
    sleep 2
}

# ============================================================================
# Node.js Dependencies
# ============================================================================

install_node_deps() {
    log_step "📦 Installing Node.js dependencies..."

    cd "$INSTALL_DIR"

    if [ -f "package.json" ]; then
        npm install --production 2>/dev/null || true
        log_success "Node.js dependencies installed"
    else
        log_info "No package.json found, skipping"
    fi

    sleep 2
}

# ============================================================================
# Browser Installation
# ============================================================================

install_browser() {
    if [ "$SKIP_BROWSER" = true ]; then
        log_info "Skipping browser installation (--skip-browser)"
        return
    fi

    log_step "🌐 Setting up browser automation..."

    # Install Playwright browsers
    if command -v npx &> /dev/null; then
        npx playwright install chromium 2>/dev/null || true
        log_success "Browser ready"
    else
        log_warn "npx not found, skipping browser installation"
    fi

    sleep 2
}

# ============================================================================
# Create Symlink
# ============================================================================

create_symlink() {
    log_step "🔗 Creating command symlink..."

    # Create wrapper script at /usr/local/bin/chiper
    cat > /usr/local/bin/chiper << 'WRAPPER'
#!/bin/bash
export CHIPER_HOME="${CHIPER_HOME:-$HOME/.chiperflux}"
export CHIPER_INSTALL_DIR="/usr/local/lib/chiper-agent"

# Activate venv if exists
if [ -f "$CHIPER_INSTALL_DIR/.venv/bin/activate" ]; then
    source "$CHIPER_INSTALL_DIR/.venv/bin/activate"
elif [ -f "$CHIPER_INSTALL_DIR/venv/bin/activate" ]; then
    source "$CHIPER_INSTALL_DIR/venv/bin/activate"
fi

# Run CLI
cd "$CHIPER_INSTALL_DIR"
python -c "from chiper_cli.main import main; main()" "$@"
WRAPPER

    chmod +x /usr/local/bin/chiper
    log_success "Command 'chiper' available at /usr/local/bin/chiper"

    # Also create symlink at ~/.local/bin/chiper (for doctor check)
    local _venv_bin="$CHIPER_INSTALL_DIR/.venv/bin/chiper"
    local _local_bin="$HOME/.local/bin"
    if [ -f "$_venv_bin" ]; then
        mkdir -p "$_local_bin"
        ln -sf "$_venv_bin" "$_local_bin/chiper"
        log_success "Symlink '$_local_bin/chiper' → $_venv_bin"

        # Check if ~/.local/bin is on PATH
        if ! echo "$PATH" | tr ':' '\n' | grep -q "^$_local_bin$"; then
            log_warn "~/.local/bin is not on PATH"
            log_info "Add to your shell config: export PATH=\"\$HOME/.local/bin:\$PATH\""
        fi
    fi

    sleep 2
}

# ============================================================================
# Initialize Config
# ============================================================================

init_config() {
    log_step "⚙️  Initializing configuration..."

    mkdir -p "$CHIPER_HOME"

    # Create .env from .env.example if not exists
    if [ ! -f "$CHIPER_HOME/.env" ]; then
        if [ -f "$INSTALL_DIR/.env.example" ]; then
            cp "$INSTALL_DIR/.env.example" "$CHIPER_HOME/.env"
            log_success "Created .env from .env.example at $CHIPER_HOME/.env"
        else
            # Fallback: create minimal .env
            cat > "$CHIPER_HOME/.env" << 'ENVFILE'
# ChiperFlux Agent Configuration
# ================================
# Run 'chiper setup' or 'chiper env wizard' to configure

# LLM Provider (choose one)
OPENROUTER_API_KEY=

# Telegram Bot
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USERS=
ENVFILE
            log_success "Created default .env at $CHIPER_HOME/.env"
        fi
    else
        log_info ".env already exists, skipping"
    fi

    sleep 2

    # Create config.yaml if not exists
    if [ ! -f "$CHIPER_HOME/config.yaml" ]; then
        cat > "$CHIPER_HOME/config.yaml" << 'CONFIGFILE'
# ChiperFlux Agent Configuration
# ================================

# Model settings
model:
  provider: openrouter
  model: anthropic/claude-sonnet-4

# Memory settings
memory:
  enabled: true
  max_entries: 1000

# Tool settings
tools:
  enabled:
    - terminal
    - file
    - web
    - browser
    - image_gen
    - tts

# Gateway settings (Telegram, Discord, etc.)
gateway:
  enabled: false
  platforms: []

# Port settings (avoid conflict with Hermes)
# Hermes: 8642, 8644, 8645
# Chiper: 1511, 1512, 1513
api_server:
  host: "127.0.0.1"
  port: 1511

webhook:
  host: "0.0.0.0"
  port: 1512

proxy:
  host: "127.0.0.1"
  port: 1513
CONFIGFILE
        log_success "Created default config at $CHIPER_HOME/config.yaml"
    else
        log_info "config.yaml already exists, skipping"
    fi

    sleep 2
}

# ============================================================================
# Post-Install Setup
# ============================================================================

post_install() {
    if [ "$RUN_SETUP" = false ]; then
        log_info "Skipping setup wizard (--skip-setup)"
        return
    fi

    log_step "🧙 Running setup wizard..."

    cd "$INSTALL_DIR"

    # Run setup if interactive - use full path to chiper
    local _chiper_cmd="$INSTALL_DIR/.venv/bin/chiper"
    if [ ! -f "$_chiper_cmd" ]; then
        _chiper_cmd="/usr/local/bin/chiper"
    fi

    if [ "$IS_INTERACTIVE" = true ]; then
        log_info "Starting chiper setup..."
        "$_chiper_cmd" setup || log_warn "Setup wizard skipped (non-critical)"
    else
        log_info "Non-interactive mode, skipping setup wizard"
        log_info "Run 'chiper setup' manually to configure"
    fi

    sleep 5
}

# ============================================================================
# Main Installation
# ============================================================================

main() {
    show_banner
    parse_args "$@"
    detect_os
    install_dependencies
    install_python
    clone_repo
    setup_venv
    install_node_deps
    install_browser
    create_symlink
    init_config
    post_install

    # Success!
    echo ""
    echo -e "${GREEN}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║   ✅  ChiperFlux Agent installed successfully!               ║"
    echo "║                                                              ║"
    echo "║   📁 Data:    $CHIPER_HOME"
    echo "║   📁 Code:    $INSTALL_DIR"
    echo "║   🔧 Command: chiper"
    echo "║                                                              ║"
    echo "║   Quick start:                                               ║"
    echo "║     source ~/.bashrc    # reload shell                       ║"
    echo "║     chiper              # start chatting!                    ║"
    echo "║                                                              ║"
    echo "║   Configure:                                                 ║"
    echo "║     chiper setup        # full setup wizard                  ║"
    echo "║     chiper model        # choose LLM provider               ║"
    echo "║     chiper telegram setup  # setup Telegram gateway          ║"
    echo "║     chiper gateway      # start gateway (Telegram etc)       ║"
    echo "║                                                              ║"
    echo "║   Tools:                                                     ║"
    echo "║     chiper env show     # view .env config                   ║"
    echo "║     chiper env check    # check required vars                ║"
    echo "║     chiper platform detect  # detect platforms               ║"
    echo "║     chiper doctor       # diagnose issues                    ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Run main
main "$@"
