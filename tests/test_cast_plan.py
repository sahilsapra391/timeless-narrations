import unittest

from timeless.cast_plan import plan_cast


class CastPlanTests(unittest.TestCase):
    def test_five_similar_profiles_get_separate_voices(self):
        ids = ["a", "b", "c", "d", "e"]
        book = {
            "cast": {name: {"age": "adult", "gender": "male"} for name in ids},
            "chapters": [{"lines": [{"speaker": name} for name in ["narrator", *ids]]}],
        }
        voices, report = plan_cast(book)
        self.assertEqual(len({v.name for v in voices.values()}), 6)
        self.assertEqual(len(report), 6)

    def test_aliases_and_locked_voice_preserved(self):
        book = {
            "cast": {
                "allen": {"age": "adult", "gender": "male"},
                "james": {"aliases": ["Jim"], "display_name": "James",
                          "age": "adult", "gender": "male", "kokoro_voice": "am_michael"},
            },
            "chapters": [{"lines": [{"speaker": "Allen"}, {"speaker": "JIM"}, {"speaker": "James"}]}],
        }
        voices, report = plan_cast(book)
        self.assertNotEqual(voices["allen"].name, voices["james"].name)
        self.assertEqual(voices["james"].name, "am_michael")
        self.assertEqual(report[1]["passages"], 2)
        self.assertEqual(report[1]["speaker"], "James")
