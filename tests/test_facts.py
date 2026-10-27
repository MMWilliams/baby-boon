import unittest

from baby_boon.facts import FACTS, conversion_note, fact_note, keeps_figures, with_facts
from baby_boon.guard import guarded

ALL_FACTS = [f for facts in FACTS.values() for f in facts]


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
            # A measure named with "a" next to a real amount is the unit wanted, not a second amount.
            "need 3 tablespoons of oil but I only have a teaspoon, how many do I use": "3 tablespoons of oil = 9 teaspoons.",
            "the recipe wants 4 tbsp butter, how much of a stick is that": "4 tablespoons of butter = 1/2 stick.",
            "how much is 6 tbsp in cups": "6 tablespoons = 3/8 cup.",
            # Unit before a bare reading, "in" between amount and unit, single-letter target.
            "oven dial is in celsius and says 180. whats that in F": "180°C = 356°F.",
            "it's 22 in celsius here, whats that in fahrenheit": "22°C = 71.6°F.",
            "what's 100 C in F": "100°C = 212°F.",
            # The source unit named again isn't a target (regressed in 9106ec3, caught on dev prompt f01).
            "my 1/4 measuring cup broke. how many tablespoons is a quarter of a cup?": "1/4 cup = 4 tablespoons.",
        }
        for text, note in cases.items():
            self.assertEqual(conversion_note(text), note, text)

    def test_named_ingredients_convert_between_weight_and_volume(self):
        cases = {
            "how many cups is 250 g of flour": "250 grams of flour = about 2 cups.",
            "2 cups of sugar in grams": "2 cups of sugar = about 400 grams.",
            "need 1 cup packed brown sugar, how many grams": "1 cup of brown sugar = about 220 grams.",
            "half a cup of milk, how many ounces is that": "1/2 cup of milk = 4 fluid ounces.",
            "3 tbsp peanut butter in grams": "3 tablespoons of peanut butter = about 48 grams.",
            # "X and a half" counted as a half before (dev prompt g21 got 1/2 cup of milk).
            "two and a half cups of sugar in grams": "2 1/2 cups of sugar = about 500 grams.",
            "three and a half cups of water in ml": "3 1/2 cups of water = about 828 milliliters.",
            # The other scale named by a verb, and the same amount said twice.
            "the dial says 400 in F and this oven only does C, where do i put it": "400°F = 204.4°C.",
            "got 3 kilos of apples, the recipe is in pounds. 3 kilos is how many lb": "3 kilograms = about 6 5/8 pounds.",
        }
        for text, note in cases.items():
            self.assertEqual(conversion_note(text), note, text)

    def test_weight_to_volume_needs_a_known_ingredient(self):
        self.assertIn("can't be converted to cups", conversion_note("how many cups is 200 g of chopped walnuts"))

    def test_casual_quantities_get_no_note(self):
        for text in ["had 2 cups of coffee and I'm still dead", "it's 30 C out and my AC died", "I got a C on the test",
                     "lost 5 pounds this month!!", "In fact, tell him the truth.", "my sister is 3 and already reads",
                     "we got to F in the alphabet song before he fell asleep"]:
            self.assertIsNone(conversion_note(text), text)
            self.assertIsNone(fact_note(text), text)

    def test_fact_requests_draw_from_the_topic_list(self):
        self.assertIn(fact_note("Zonked. Tell me one weird animal fact to perk me up."), FACTS["animal"])
        self.assertIn(fact_note("give me a space fact pls"), FACTS["space"])
        self.assertIn(fact_note("random fun fact?"), ALL_FACTS)

    def test_fact_requests_without_the_word_fact(self):
        self.assertIn(fact_note("what's the grossest thing about the human body?"), FACTS["body"])
        self.assertIn(fact_note("tell me the strangest creature in the sea"), FACTS["ocean"])
        self.assertIn(fact_note("bored out of my mind. tell me something weird"), ALL_FACTS)
        self.assertIn(fact_note("hit me with some trivia"), ALL_FACTS)
        self.assertIn(fact_note("know any cool trivia about fish?"), FACTS["ocean"])
        self.assertIn(fact_note("distract me with something wild about the planets"), FACTS["space"])
        self.assertIn(fact_note("craziest thing about the brain? hit me"), FACTS["body"])

    def test_a_named_subject_picks_a_fact_that_mentions_it(self):
        self.assertIn("Sharks", fact_note("know any cool trivia about sharks?"))
        self.assertIn("Cats", fact_note("tell me something weird about cats"))
        self.assertIn("Octopuses", fact_note("whats the strangest thing about octopuses"))

    def test_personal_questions_are_not_fact_requests(self):
        for text in ["what's the weirdest thing about your day?", "tell me something interesting about yourself",
                     "trivia night is tomorrow and I'm nervous", "the weirdest thing about my ex is he never texts back"]:
            self.assertIsNone(fact_note(text), text)

    def test_reply_must_use_the_note_and_add_no_figures(self):
        rice = ("370 grams of rice = about 2 cups.", "recipe says 370 g of rice, how many cups is that")
        self.assertTrue(keeps_figures("That's about 2 cups. 370 g is a bit more than two cups, so round down.", *rice))
        self.assertTrue(keeps_figures("Two cups, more or less.", *rice))  # spelled number counts as present
        self.assertFalse(keeps_figures("That's about 2 cups. One cup is 100 grams, so 370 grams is roughly 2.7 cups.", *rice))  # facts2 g17
        self.assertFalse(keeps_figures("Two and a half cups.", *rice))
        self.assertFalse(keeps_figures("Just use a scale, it's easier.", *rice))
        oven = ("350°F = 176.7°C.", "oven says 350 F, what's that in celsius")
        self.assertTrue(keeps_figures("About 177°C, so 180 on most dials is fine.", *oven))  # rounding within 2%
        self.assertFalse(keeps_figures("About 200°C.", *oven))
        oil = ("3 tablespoons of oil = 9 teaspoons.", "need 3 tablespoons of oil but only have a teaspoon")
        self.assertTrue(keeps_figures("3 tablespoons is 9 teaspoons, so 9 scoops and you're there.", *oil))
        self.assertTrue(keeps_figures("1 gallon is about 3,785 ml, so 3785 is the number.", "1 gallon = about 3,785 milliliters.", "how many ml in a gallon"))
        walnuts = (conversion_note("how many cups is 200 g of chopped walnuts"), "how many cups is 200 g of chopped walnuts")
        self.assertTrue(keeps_figures("I can't convert 200 g of walnuts to cups without knowing how fine they're chopped.", *walnuts))
        self.assertFalse(keeps_figures("About 2 cups.", *walnuts))
        # The guard resamples on a bad reply and answers with the note itself when every attempt fails.
        replies = iter(["One cup is 100 grams, so 2.7 cups.", "About 2 cups."])
        self.assertEqual(guarded(lambda attempt: {"text": next(replies)}, 4, rice[1], rice[0]), {"text": "About 2 cups.", "guard_attempts": 2})
        self.assertEqual(guarded(lambda attempt: {"text": "Use a scale."}, 1, rice[1], rice[0])["text"], rice[0])

    def test_note_goes_to_the_system_prompt_for_this_turn_only(self):
        messages = [{"role": "system", "content": "S"}, {"role": "user", "content": "how many tbsp in a cup"}]
        self.assertEqual(with_facts(messages, messages[-1]["content"])[0]["content"],
                         "S For this reply, use these checked numbers exactly and add no other figures: 1 cup = 16 tablespoons.")
        self.assertEqual(messages[0]["content"], "S")
        self.assertIs(with_facts(messages, "hi"), messages)


if __name__ == "__main__": unittest.main()
