from app.services.dograh_sync import parse_transcript


def test_parse_transcript_roles_and_multiline():
    text = (
        "[2026-07-24T13:13:18.654+00:00] assistant: Hi, this is Sam.\n"
        "[2026-07-24T13:13:28.327+00:00] user: My name is Ryan\n"
        "and I want to rent.\n"
        "[2026-07-24T13:13:33.934+00:00] assistant: Great, Ryan!\n"
    )
    turns = parse_transcript(text)
    assert turns == [
        ("agent", "Hi, this is Sam."),
        ("caller", "My name is Ryan and I want to rent."),  # folded continuation line
        ("agent", "Great, Ryan!"),
    ]


def test_parse_transcript_ignores_blank_and_garbage():
    assert parse_transcript("") == []
    assert parse_transcript("no timestamp here\n\n") == []
