#!/bin/bash
# ============================================================================
# ChiperFlux Agent Installer
# ============================================================================
# Installation script for Linux, macOS, and Android/Termux.
# Fork dari Chiper Agent oleh Nous Research.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/iamtubasya/chiper-agent/main/scripts/install.sh | bash
#
# Or with options:
#   curl -fsSL ... | bash -s -- --no-venv --skip-setup
#
# ============================================================================

set -e

# Guard against environment leakage
if [ -n "${PYTHONPATH:-}" ]; then
    echo "⚠ Ignoring inherited PYTHONPATH during install to avoid module shadowing"
    unset PYTHONPATH
fi
if [ -n "${PYTHONHOME:-}" ]; then
    echo "⚠ Ignoring inherited PYTHONHOME during install"
    unset PYTHONHOME
fi

export UV_NO_CONFIG=1

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
REPO_URL_SSH="git@github.com:iamtubasya/chiper-agent.git"
REPO_URL_HTTPS="https://github.com/iamtubasya/chiper-agent.git"
CHIPER_HOME="${CHIPER_HOME:-$HOME/.chiperflux}"
INSTALL_DIR="${CHIPER_INSTALL_DIR:-/usr/local/lib/chiper-agent}"
PYTHON_VERSION="3.11"
NODE_VERSION="22"

# Options
USE_VENV=true
RUN_SETUP=true
SKIP_BROWSER=false
NO_SKILLS=false
BRANCH="main"
INSTALL_COMMIT=""

# Detect non-interactive mode
if [ -t 0 ]; then
    IS_INTERACTIVE=true
else
    IS_INTERACTIVE=false
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-venv)
            USE_VENV=false
            shift
            ;;
        --skip-setup)
            RUN_SETUP=false
            shift
            ;;
        --skip-browser)
            SKIP_BROWSER=true
            shift
            ;;
        --no-skills)
            NO_SKILLS=true
            shift
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --commit)
            INSTALL_COMMIT="$2"
            shift 2
            ;;
        --dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        -h|--help)
            echo "ChiperFlux Agent Installer"
            echo ""
            echo "Usage: install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-venv        Skip virtual environment creation"
            echo "  --skip-setup     Skip post-install setup wizard"
            echo "  --skip-browser   Skip browser installation"
            echo "  --no-skills      Skip skills installation"
            echo "  --branch BRANCH  Install from specific branch (default: main)"
            echo "  --commit COMMIT  Install specific commit"
            echo "  --dir DIR        Custom installation directory"
            echo "  -h, --help       Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${MAGENTA}${BOLD}$1${NC}"
}

# ============================================================================
# Banner
# ============================================================================

show_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                                                              ║"
    echo "║   ██████╗██╗  ██╗██╗██████╗ ███████╗██████╗                  ║"
    echo "║  ██╔════╝██║  ██║██║██╔══██╗██╔════╝██╔══██╗                 ║"
    echo "║  ██║     ███████║██║██████╔╝█████╗  ██████╔╝                 ║"
    echo "║  ██║     ██╔══██║██║██╔═══╝ ██╔══╝  ██╔══██╗                 ║"
    echo "║  ╚██████╗██║  ██║██║██║     ███████╗██║  ██║                 ║"
    echo "║   ╚═════╝╚═╝  ╚═╝╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝                 ║"
    echo "║                                                              ║"
    echo "║   ███████╗██╗     ██╗   ██╗██╗  ██╗                         ║"
    echo "║   ██╔════╝██║     ██║   ██║╚██╗██╔╝                         ║"
    echo "║   █████╗  ██║     ██║   ██║ ╚███╔╝                          ║"
    echo "║   ██╔══╝  ██║     ██║   ██║ ██╔██╗                          ║"
    echo "║   ██║     ███████╗╚██████╔╝██╔╝ ██╗                         ║"
    echo "║   ╚═╝     ╚══════╝ ╚═════╝ ╚═╝  ╚═╝                         ║"
    echo "║                                                              ║"
    echo "║   ⚕️  ChiperFlux Agent Installer                             ║"
    echo "║   Fork dari Chiper Agent oleh Nous Research                  ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ============================================================================
# OS Detection
# ============================================================================

detect_os() {
    log_step "🔍 Detecting operating system..."

    OS="$(uname -s)"
    ARCH="$(uname -m)"

    case "${OS}" in
        Linux*)
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                DISTRO="$ID"
                DISTRO_VERSION="$VERSION_ID"
            else
                DISTRO="unknown"
                DISTRO_VERSION=""
            fi

            # Check for Termux
            if [ -n "$TERMUX_VERSION" ] || [ -d /data/data/com.termux ]; then
                IS_TERMUX=true
                log_info "Detected: Android/Termux"
            else
                IS_TERMUX=false
                log_info "Detected: Linux ($DISTRO $DISTRO_VERSION)"
            fi
            ;;
        Darwin*)
            IS_TERMUX=false
            log_info "Detected: macOS $(sw_vers -productVersion)"
            ;;
        *)
            log_error "Unsupported OS: ${OS}"
            exit 1
            ;;
    esac

    log_info "Architecture: ${ARCH}"
}

# ============================================================================
# Dependency Installation
# ============================================================================

install_dependencies() {
    log_step "📦 Installing system dependencies..."

    if [ "$IS_TERMUX" = true ]; then
        install_deps_termux
    else
        install_deps_linux
    fi
}

install_deps_termux() {
    log_info "Installing Termux packages..."

    pkg update -y
    pkg install -y \
        python \
        git \
        nodejs-lts \
        ripgrep \
        ffmpeg \
        libxml2 \
        libxslt \
        openssl \
        libffi \
        zlib \
        2>/dev/null || true

    log_success "Termux packages installed"
}

install_deps_linux() {
    # Install git if missing
    if ! command -v git &> /dev/null; then
        log_info "Installing git..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y git
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y git
        elif command -v yum &> /dev/null; then
            sudo yum install -y git
        elif command -v pacman &> /dev/null; then
            sudo pacman -Sy --noconfirm git
        fi
    fi

    # Install ripgrep if missing
    if ! command -v rg &> /dev/null; then
        log_info "Installing ripgrep..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y ripgrep 2>/dev/null || true
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y ripgrep 2>/dev/null || true
        fi
    fi

    # Install ffmpeg if missing
    if ! command -v ffmpeg &> /dev/null; then
        log_info "Installing ffmpeg..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get install -y ffmpeg 2>/dev/null || true
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y ffmpeg 2>/dev/null || true
        fi
    fi

    log_success "System dependencies installed"
}

# ============================================================================
# UV / Python Installation
# ============================================================================

install_python() {
    log_step "🐍 Setting up Python ${PYTHON_VERSION}..."

    if [ "$IS_TERMUX" = true ]; then
        # Termux: use system Python
        PYTHON_BIN=$(which python2>/dev/null || echo "")
            log_info "Using system Python: $($PYTHON_BIN --version)"
    else
        # Install uv if missing
        if ! command -v uv &> /dev/null; then
            log_info "Installing uv..."
            curl -LsSf https://astral.sh/uv/install.sh | sh
            export PATH="$HOME/.local/bin:$PATH"
        fi

        # Install Python via uv
        log_info "Installing Python ${PYTHON_VERSION} via uv..."
        uv python install ${PYTHON_VERSION} 2>/dev/null || true
        PYTHON_BIN="uv run python"
    fi

    log_success "Python ready"
}

# ============================================================================
# Clone Repository
# ============================================================================

clone_repo() {
    log_step "📥 Cloning ChiperFlux Agent repository..."

    if [ -d "$INSTALL_DIR" ]; then
        log_warn "Installation directory exists: $INSTALL_DIR"
        log_info "Updating existing installation..."
        cd "$INSTALL_DIR"
        git fetch origin
        git checkout "$BRANCH"
        git pull origin "$BRANCH"
    else
        log_info "Cloning to: $INSTALL_DIR"
        if [ -n "$INSTALL_COMMIT" ]; then
            git clone --branch "$BRANCH" "$REPO_URL_HTTPS" "$INSTALL_DIR"
            cd "$INSTALL_DIR"
            git checkout "$INSTALL_COMMIT"
        else
            git clone --branch "$BRANCH" "$REPO_URL_HTTPS" "$INSTALL_DIR"
        fi
    fi

    log_success "Repository ready"
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
}

# ============================================================================
# Create Symlink
# ============================================================================

create_symlink() {
    log_step "🔗 Creating command symlink..."

    # Create wrapper script
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
}

# ============================================================================
# Initialize Config
# ============================================================================

init_config() {
    log_step "⚙️  Initializing configuration..."

    mkdir -p "$CHIPER_HOME"

    # Create .env if not exists
    if [ ! -f "$CHIPER_HOME/.env" ]; then
        cat > "$CHIPER_HOME/.env" << 'ENVFILE'
# ChiperFlux Agent Configuration
# ================================
# Fill in your API keys below

# LLM Provider (choose one)
OPENROUTER_API_KEY=
# OR
OPENAI_API_KEY=
# OR
XAI_API_KEY=

# Telegram Bot (optional)
TELEGRAM_BOT_TOKEN=

# Discord Bot (optional)
DISCORD_BOT_TOKEN=

# Other optional keys
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
ENVFILE
        log_success "Created default .env at $CHIPER_HOME/.env"
    else
        log_info ".env already exists, skipping"
    fi

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
CONFIGFILE
        log_success "Created default config at $CHIPER_HOME/config.yaml"
    else
        log_info "config.yaml already exists, skipping"
    fi
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

    # Run setup if interactive
    if [ "$IS_INTERACTIVE" = true ]; then
        chiper setup 2>/dev/null || log_warn "Setup wizard skipped (non-critical)"
    else
        log_info "Non-interactive mode, skipping setup wizard"
        log_info "Run 'chiper setup' manually to configure"
    fi
}

# ============================================================================
# Main Installation
# ============================================================================

main() {
    show_banner
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
    echo "║     chiper gateway      # start Telegram/Discord bot         ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Run main
main
