"""refusal_text: a refusal page's HTML to plain text for the admin (spec 067 R5)."""

from __future__ import annotations

from adapters.web.refusal_text import MAX_CHARS, refusal_text

HTML = "text/html; charset=utf-8"


def test_drops_script_style_noscript_and_template() -> None:
    html = (
        b"<html><head><style>.a{}</style><script>alert(1)</script></head><body>"
        b"<noscript>enable js</noscript><template><p>hidden</p></template>"
        b"<p>Visible</p></body></html>"
    )

    assert refusal_text(html, HTML) == "Visible"


def test_unescapes_entities_and_collapses_whitespace() -> None:
    html = b"<p>Fish &amp;\n\n   chips&nbsp;&eacute;</p>\t<div>  next </div>"

    assert refusal_text(html, HTML) == "Fish & chips é next"


def test_keeps_a_mailto_target() -> None:
    html = b"<p>Please <a href='mailto:licensing@people.test'>contact us</a>.</p>"

    text = refusal_text(html, HTML)

    assert "contact us" in text and "licensing@people.test" in text


def test_a_mailto_target_that_is_the_link_text_shows_once() -> None:
    html = b"<p>Write to <a href='mailto:a@b.test'>a@b.test</a></p>"

    assert refusal_text(html, HTML) == "Write to a@b.test"


def test_cut_on_a_word_boundary() -> None:
    html = ("<p>" + "word " * 400 + "</p>").encode()

    text = refusal_text(html, HTML)

    assert len(text) <= MAX_CHARS
    assert text.endswith("word")


def test_non_html_and_empty_give_empty() -> None:
    assert refusal_text(b'{"error":"no"}', "application/json") == ""
    assert refusal_text(b"", HTML) == ""
    assert refusal_text(b"<p>x</p>", "") == ""
