"""Contract tests for the Docker image's immutable /opt/chiper install tree."""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = REPO_ROOT / "Dockerfile"


def _dockerfile_text() -> str:
    return DOCKERFILE.read_text()


def test_dockerfile_makes_opt_chiper_root_owned_and_non_writable() -> None:
    text = _dockerfile_text()

    assert "COPY --chown=chiper:chiper . ." not in text
    assert "COPY . ." in text
    assert "chown -R root:root /opt/chiper" in text
    assert "chmod -R a+rX /opt/chiper" in text
    assert "chmod -R a-w /opt/chiper" in text

    immutable_block = re.search(
        r"RUN mkdir -p /opt/chiper/bin && \\\n"
        r"(?:.*\\\n)+?"
        r"\s+chmod -R a-w /opt/chiper",
        text,
    )
    assert immutable_block, "Dockerfile must lock /opt/chiper after installing code/deps"


def test_dockerfile_keeps_mutable_state_under_opt_data() -> None:
    text = _dockerfile_text()

    assert "ENV CHIPER_HOME=/opt/data" in text
    assert "ENV CHIPER_WRITE_SAFE_ROOT=/opt/data" in text
    assert 'VOLUME [ "/opt/data" ]' in text


def test_dockerfile_disables_runtime_install_mutations() -> None:
    text = _dockerfile_text()

    assert "ENV PYTHONDONTWRITEBYTECODE=1" in text
    assert "ENV CHIPER_DISABLE_LAZY_INSTALLS=1" in text
    assert "CHIPER_TUI_DIR=/opt/chiper/ui-tui" in text


def test_dockerfile_does_not_chown_install_trees_to_chiper() -> None:
    text = _dockerfile_text()
    forbidden_patterns = (
        r"chown\s+-R\s+chiper:chiper\s+/opt/chiper/\.venv",
        r"chown\s+-R\s+chiper:chiper\s+/opt/chiper/ui-tui",
        r"chown\s+-R\s+chiper:chiper\s+/opt/chiper/gateway",
        r"chown\s+-R\s+chiper:chiper\s+/opt/chiper/node_modules",
    )
    for pattern in forbidden_patterns:
        assert not re.search(pattern, text), (
            "runtime install trees under /opt/chiper must stay immutable; "
            f"found forbidden pattern {pattern!r}"
        )


def test_dockerfile_bakes_code_scoped_install_method_stamp() -> None:
    """The 'docker' install-method stamp is baked next to the code.

    detect_install_method() reads the code-scoped stamp
    (/opt/chiper/.install_method) first; baking it at build time keeps the
    published image self-identifying as 'docker' WITHOUT writing into the
    shared $CHIPER_HOME data volume (which a host install may also use).
    It must live inside the immutable block so the runtime user can't alter it.
    """
    text = _dockerfile_text()
    assert "printf 'docker\\n' > /opt/chiper/.install_method" in text

    immutable_block = re.search(
        r"RUN mkdir -p /opt/chiper/bin && \\\n"
        r"(?:.*\\\n)+?"
        r"\s+chmod -R a-w /opt/chiper",
        text,
    )
    assert immutable_block, "immutable block must exist"
    assert ".install_method" in immutable_block.group(0), (
        "the code-scoped install-method stamp must be baked inside the "
        "immutable /opt/chiper block"
    )
