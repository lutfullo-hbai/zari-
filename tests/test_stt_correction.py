import sys

sys.path.insert(0, "/home/lutfullo/bor/forlearnproject/zari/zari-")

from voice.stt import correct_stt


def test_einstein_corrections():
    assert correct_stt("enxten") == "Einstein"
    assert correct_stt("enxte") == "Einstein"
    assert correct_stt("enste") == "Einstein"
    assert correct_stt("enxin") == "Einstein"
    assert correct_stt("enksin") == "Einstein"


def test_telegram_corrections():
    assert correct_stt("telefram") == "Telegram"
    assert correct_stt("telegramm") == "Telegram"


def test_python_corrections():
    assert correct_stt("paison") == "Python"
    assert correct_stt("payton") == "Python"


def test_jarvis_corrections():
    assert correct_stt("javris") == "Jarvis"
    assert correct_stt("djevis") == "Jarvis"


def test_n8n_corrections():
    assert correct_stt("nayn") == "n8n"
    assert correct_stt("eneyn") == "n8n"


def test_microsoft_corrections():
    assert correct_stt("maykrosoft") == "Microsoft"
    assert correct_stt("mikrosoft") == "Microsoft"


def test_full_sentence():
    text = "Menga enxten haqida ayting"
    result = correct_stt(text)
    assert result == "Menga Einstein haqida ayting"

    text2 = "telefram ochish kerak"
    result2 = correct_stt(text2)
    assert result2 == "Telegram ochish kerak"


def test_case_insensitive():
    assert correct_stt("ENXTEN") == "Einstein"
    assert correct_stt("Enxte") == "Einstein"
    assert correct_stt("TELEFRAM") == "Telegram"


def test_no_corrections_needed():
    text = "Salom, men Zari"
    result = correct_stt(text)
    assert result == text


def test_multiple_corrections():
    text = "enxte telefram paison javris"
    result = correct_stt(text)
    assert result == "Einstein Telegram Python Jarvis"


if __name__ == "__main__":
    test_einstein_corrections()
    test_telegram_corrections()
    test_python_corrections()
    test_jarvis_corrections()
    test_n8n_corrections()
    test_microsoft_corrections()
    test_full_sentence()
    test_case_insensitive()
    test_no_corrections_needed()
    test_multiple_corrections()
    print("All tests passed!")
