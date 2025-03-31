from src.router import valid_url


def test_validate_url_accepts_valid_urls():
    assert valid_url("http://example.com") is True
    assert valid_url("https://uk.example.com/page?q=1") is True


def test_validate_url_rejects_invalid_urls():
    assert valid_url("") is False
    assert valid_url("?https://example.com?") is False
