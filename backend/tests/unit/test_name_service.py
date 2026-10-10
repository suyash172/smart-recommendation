from app.services.name_service import to_english, names_match


def test_company_name_organiser_example():
    assert to_english("شركة الأمل للتجارة") == "Al-Amal Trading Co."


def test_personal_names():
    assert to_english("محمد أحمد") == "Mohammed Ahmed"
    assert to_english("عبدالله خالد") == "Abdullah Khalid"


def test_matches_across_spellings():
    assert names_match("شركة الأمل للتجارة", "Al-Amal Trading Co.")[0]
    assert names_match("محمد أحمد", "Muhammad Ahmad")[0]
    assert names_match("الأمل", "Amal")[0]


def test_translation_trap_does_not_match():
    assert not names_match("شركة الأمل للتجارة", "The Hope Trading Company")[0]


def test_different_people_do_not_match():
    assert not names_match("محمد أحمد", "Fatima Hassan")[0]


def test_english_passthrough():
    assert to_english("John Smith") == "John Smith"