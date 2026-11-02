from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "e_hdl_buspro_mqtt" / "app" / "static"
OPERATOR_TEMPLATES = (
    ROOT / "user" / "home.html",
    ROOT / "user" / "home2.html",
    ROOT / "user" / "home_plus.html",
    ROOT / "user" / "lights.html",
    ROOT / "user" / "covers.html",
    ROOT / "user" / "extra.html",
    ROOT / "user" / "scenarios.html",
    ROOT / "user" / "locks.html",
    ROOT / "user" / "ksenia.html",
    ROOT / "user" / "e_guard.html",
    ROOT / "eface" / "index.html",
)


def test_every_operator_template_declares_operator_mode():
    missing = [
        str(path.relative_to(ROOT))
        for path in OPERATOR_TEMPLATES
        if 'data-econtrol-page="operator"' not in path.read_text(encoding="utf-8")
    ]
    assert missing == []


def test_navigation_exits_before_admin_shell_side_effects():
    script = (ROOT / "hub" / "hub-nav.js").read_text(encoding="utf-8")
    guard = "if(document.documentElement.dataset.econtrolPage==='operator')return;"
    assert guard in script
    guard_offset = script.index(guard)
    assert guard_offset < script.index("document.body.classList.add('hub-shell-ready')")
    assert guard_offset < script.index("document.createElement('nav')")
    assert guard_offset < script.index("fetch(url('api/meta')")


def test_admin_page_does_not_opt_out_of_navigation():
    admin = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'data-econtrol-page="operator"' not in admin

