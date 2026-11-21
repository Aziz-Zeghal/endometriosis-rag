import pytest
from endorag_back.prompts import PROMPTS_DIR, load_prompt

NODES = [
    "safety_gate",
    "emergency",
    "router",
    "chitchat",
    "out_of_scope",
    "rewrite",
    "generate",
    "triage",
    "clarify",
    "refuse",
]
FIXED_MESSAGES = ["error", "safety_footer"]  # read by the chat service


@pytest.mark.parametrize("profile", ["patient", "gp"])
@pytest.mark.parametrize("node", NODES)
def test_every_node_has_a_prompt_in_both_profiles(profile, node):
    assert load_prompt(profile, node)


@pytest.mark.parametrize("profile", ["patient", "gp"])
def test_fixed_messages_exist_and_the_safety_footer_names_15_and_112(profile):
    assert all(load_prompt(profile, name) for name in FIXED_MESSAGES)
    footer = load_prompt(profile, "safety_footer")
    assert "15" in footer and "112" in footer


def test_profiles_have_the_same_nodes():
    assert {p.name for p in (PROMPTS_DIR / "patient").glob("*.md")} == {
        p.name for p in (PROMPTS_DIR / "gp").glob("*.md")
    }


def test_load_prompt_reads_the_profile_file():
    assert load_prompt("gp", "router") != load_prompt("patient", "router")
    assert load_prompt("gp", "router") == (PROMPTS_DIR / "gp" / "router.md").read_text().strip()


def test_missing_prompt_raises():
    with pytest.raises(FileNotFoundError, match="nope"):
        load_prompt("patient", "nope")
