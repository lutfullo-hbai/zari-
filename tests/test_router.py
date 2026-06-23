from core.router import detect_intent, route


def test_detect_search():
    assert detect_intent("internetdan qidir") == "search"
    assert detect_intent("buni qidirib top") == "search"


def test_detect_music():
    assert detect_intent("musiqa qo'y") == "music"
    assert detect_intent("qo'shiq tingla") == "music"


def test_detect_weather():
    assert detect_intent("ob-havo qanday") == "weather"
    assert detect_intent("havo qanday") == "weather"


def test_detect_time():
    assert detect_intent("soat necha") == "time"
    assert detect_intent("bugun qanday kun") == "time"


def test_detect_chat_fallback():
    assert detect_intent("nima gap") == "chat"
    assert detect_intent("salom") == "chat"


def test_route():
    assert route("musiqa qo'y") == "music"
    assert route("salom") == "chat"
