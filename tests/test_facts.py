import unittest

from baby_boon.facts import FACTS, conversion_note, fact_note, with_facts


class Facts(unittest.TestCase):
    def test_known_wrong_conversions_are_computed(self):
        cases = {
            "Running on empty. How many tablespoons make a quarter cup again?": "1/4 cup = 4 tablespoons.",
            "recipe card says 1 pound of butter. how many cups is that?": "1 pound of butter = 2 cups.",
            "thermometer says 38.5 C, what's that in fahrenheit?": "38.5°C = 101.3°F.",
            "how many grams is 1.5 lbs": "1 1/2 pounds = about 680 grams.",
            "convert 350°F to celsius": "350°F = 176.7°C.",
            "half a cup is how many tsp": "1/2 cup = 24 teaspoons.",
            "how much is two sticks of butter": "2 sticks = 1 cup = 16 tablespoons = 8 ounces.",
            "how many ml in 3/4 cup": "3/4 cup = about 177 milliliters.",
        }
        for text, note in cases.items():
            self.assertEqual(conversion_note(text), note, text)

    def test_weight_to_volume_needs_the_ingredient(self):
        self.assertIn("can't be converted to cups", conversion_note("how many cups is 200 g of flour"))

    def test_casual_quantities_get_no_note(self):
        for text in ["had 2 cups of coffee and I'm still dead", "it's 30 C out and my AC died", "I got a C on the test",
                     "lost 5 pounds this month!!", "In fact, tell him the truth."]:
            self.assertIsNone(conversion_note(text), text)
            self.assertIsNone(fact_note(text), text)

    def test_fact_requests_draw_from_the_topic_list(self):
        self.assertIn(fact_note("Zonked. Tell me one weird animal fact to perk me up."), FACTS["animal"])
        self.assertIn(fact_note("give me a space fact pls"), FACTS["space"])
        self.assertIn(fact_note("random fun fact?"), [f for facts in FACTS.values() for f in facts])

    def test_note_goes_to_the_system_prompt_for_this_turn_only(self):
        messages = [{"role": "system", "content": "S"}, {"role": "user", "content": "how many tbsp in a cup"}]
        self.assertEqual(with_facts(messages, messages[-1]["content"])[0]["content"],
                         "S For this reply, use these checked numbers exactly and add no other figures: 1 cup = 16 tablespoons.")
        self.assertEqual(messages[0]["content"], "S")
        self.assertIs(with_facts(messages, "hi"), messages)


if __name__ == "__main__": unittest.main()
