"""
Playbook & Historical Data Analyzer Module.
Extracts insights from historical Shorts data and maintains a curated catalog of high-potential X vs Y concepts.
"""

from typing import Any, Dict, List


class ConceptCatalog:
    """
    Curated database of high-potential pop-culture & superhero X vs Y opportunities
    spanning Marvel, DC, Transformers, Anime, Star Wars, and Mythology.
    """

    OPPORTUNITIES = [
        # --- MARVEL DEEPDIVES ---
        {
            "id": "opp_marvel_01",
            "title": "Uru vs Vibranium: Which Metal Is Stronger?",
            "type": "deepdive",
            "fandom": "Marvel",
            "pairs": [["Uru", "Vibranium"]],
            "template_id": 2,
            "entity_a": "Uru Metal",
            "entity_b": "Vibranium",
            "concept_hook": "Most people think Vibranium is Marvel's strongest metal. It's not.",
            "mechanism_a": "Uru is a mystical forged metal from Asgard that absorbs magic and spell enchantments, growing stronger the more energy is poured into it",
            "mechanism_b": "Vibranium is a rare cosmic metal that absorbs kinetic physical force and vibrations, converting impacts into stored kinetic energy",
            "punchline": "Vibranium stops physical attacks, while Uru absorbs mystical power."
        },
        {
            "id": "opp_marvel_02",
            "title": "Wolverine vs Deadpool: Healing Factor Diff",
            "type": "deepdive",
            "fandom": "Marvel",
            "pairs": [["Wolverine", "Deadpool"]],
            "template_id": 1,
            "entity_a": "Wolverine",
            "entity_b": "Deadpool",
            "concept_hook": "Most people think Wolverine and Deadpool have the exact same healing factor. They don't.",
            "mechanism_a": "Wolverine's natural mutant healing factor constantly fights off his heavy Adamantium skeletal poisoning while repairing cellular damage",
            "mechanism_b": "Deadpool's artificial healing factor was cloned from Wolverine but mutated by his aggressive cancer, regenerating cells so fast his body constantly replaces itself",
            "punchline": "Wolverine heals to survive his own bones, while Deadpool heals to stay alive."
        },
        {
            "id": "opp_marvel_03",
            "title": "Infinity Stones vs Darkhold: Dark Magic",
            "type": "deepdive",
            "fandom": "Marvel",
            "pairs": [["Infinity Stones", "Darkhold"]],
            "template_id": 1,
            "entity_a": "The Infinity Stones",
            "entity_b": "The Darkhold",
            "concept_hook": "Most fans think the Infinity Stones are the ultimate power in Marvel. That's wrong.",
            "mechanism_a": "The Infinity Stones control the fundamental forces of physical reality, space, time, and mind in a single universe",
            "mechanism_b": "The Darkhold is a corrupting book of dark magic that corrupts the user's soul and allows dreamwalking across the multiverse",
            "punchline": "The Infinity Stones rule physical reality, while the Darkhold corrupts the mind."
        },
        {
            "id": "opp_marvel_04",
            "title": "Spider-Man vs Symbiote Spider-Man",
            "type": "deepdive",
            "fandom": "Marvel",
            "pairs": [["Classic Spider-Man", "Black Suit Spider-Man"]],
            "template_id": 5,
            "entity_a": "Classic Spider-Man",
            "entity_b": "Symbiote Spider-Man",
            "concept_hook": "Most people think the Black Suit was just a cool wardrobe change for Peter Parker. It wasn't.",
            "mechanism_a": "Classic Spider-Man relies on his natural spider-sense, mechanical web-shooters, and moral responsibility to hold back his true strength",
            "mechanism_b": "The Symbiote suit provides unlimited organic webbing, boosted strength, and feeds on aggression, removing Peter's moral restraint",
            "punchline": "Classic Peter holds back his strength, while the Symbiote unleashes his rage."
        },

        # --- DC DEEPDIVES ---
        {
            "id": "opp_dc_01",
            "title": "Batman's Hellbat Suit vs Iron Man's Hulkbuster",
            "type": "deepdive",
            "fandom": "DC",
            "pairs": [["Hellbat Armor", "Hulkbuster Armor"]],
            "template_id": 2,
            "entity_a": "The Hellbat Armor",
            "entity_b": "The Hulkbuster Armor",
            "concept_hook": "Most fans think the Hulkbuster is the ultimate anti-god suit. It's not.",
            "mechanism_a": "The Hellbat suit was forged by the entire Justice League in the sun to let Batman fight New Gods, but drains his life force while operating",
            "mechanism_b": "The Hulkbuster uses modular heavy hydraulic armor plates and satellite replacement parts to withstand brute physical force",
            "punchline": "The Hulkbuster fights physical monsters, while the Hellbat drains life to kill Gods."
        },
        {
            "id": "opp_dc_02",
            "title": "Speed Force vs Artificial Speed: Flash vs Reverse Flash",
            "type": "deepdive",
            "fandom": "DC",
            "pairs": [["Positive Speed Force", "Negative Speed Force"]],
            "template_id": 1,
            "entity_a": "The Speed Force",
            "entity_b": "The Negative Speed Force",
            "concept_hook": "Most fans think Barry Allen and Eobard Thawne pull speed from the same place. They don't.",
            "mechanism_a": "The Speed Force is a positive kinetic energy field created by Barry's movement that generates momentum and protects the timeline",
            "mechanism_b": "The Negative Speed Force was created by Thawne using hatred, eating away at kinetic energy and corrupting time",
            "punchline": "Barry creates speed with movement, while Thawne feeds speed with hatred."
        },

        # --- ANIME / POP CULTURE DEEPDIVES ---
        {
            "id": "opp_anime_01",
            "title": "Super Saiyan vs Super Saiyan God: Transformation Clash",
            "type": "deepdive",
            "fandom": "Anime",
            "pairs": [["Super Saiyan", "Super Saiyan God"]],
            "template_id": 1,
            "entity_a": "Super Saiyan",
            "entity_b": "Super Saiyan God",
            "concept_hook": "Most fans think Super Saiyan God is just Super Saiyan 4. It's not.",
            "mechanism_a": "Super Saiyan multiplies mortal ki through intense emotional rage and physical stamina strain",
            "mechanism_b": "Super Saiyan God absorbs divine god ki through a ritual of pure-hearted Saiyans, granting godlike speed and self-healing",
            "punchline": "Super Saiyan burns mortal rage, while Super Saiyan God channel divine peace."
        },

        # --- COMPILATIONS ---
        {
            "id": "opp_comp_01",
            "title": "3 Marvel Weapons Everyone Gets Wrong",
            "type": "compilation",
            "fandom": "Marvel",
            "pairs": [
                ["Mjolnir", "Stormbreaker"],
                ["Cap's Shield", "Panther Suit"],
                ["Uru Gauntlet", "Nano Gauntlet"]
            ],
            "template_id": 8,
            "pairs_data": [
                {
                    "entity_a": "Mjolnir",
                    "entity_b": "Stormbreaker",
                    "contrast_a": "requires worthiness to lift",
                    "contrast_b": "requires raw strength and summons the Bifrost"
                },
                {
                    "entity_a": "Cap's Shield",
                    "entity_b": "Panther Suit",
                    "contrast_a": "absorbs and reflects physical impacts",
                    "contrast_b": "stores kinetic force and releases purple energy blasts"
                },
                {
                    "entity_a": "Uru Gauntlet",
                    "entity_b": "Nano Gauntlet",
                    "contrast_a": "safely channels cosmic stone power",
                    "contrast_b": "uses Stark tech and leaks lethal radiation"
                }
            ]
        },
        {
            "id": "opp_comp_02",
            "title": "3 DC Power Terms You've Been Mixing Up",
            "type": "compilation",
            "fandom": "DC",
            "pairs": [
                ["Red Sun", "Yellow Sun"],
                ["Lazarus Pit", "Venom Serum"],
                ["Anti-Life Equation", "Mother Box"]
            ],
            "template_id": 8,
            "pairs_data": [
                {
                    "entity_a": "Red Sun",
                    "entity_b": "Yellow Sun",
                    "contrast_a": "strips Kryptonian powers",
                    "contrast_b": "charges Kryptonian cells like a battery"
                },
                {
                    "entity_a": "Lazarus Pit",
                    "entity_b": "Venom Serum",
                    "contrast_a": "heals wounds but induces madness",
                    "contrast_b": "boosts muscle mass but causes addiction"
                },
                {
                    "entity_a": "Anti-Life Equation",
                    "entity_b": "Mother Box",
                    "contrast_a": "rewrites free will to obey Darkseid",
                    "contrast_b": "is a living supercomputer opening Boom Tubes"
                }
            ]
        }
    ]

    @classmethod
    def get_all_opportunities(cls) -> List[Dict[str, Any]]:
        """Returns all pre-curated concept opportunities."""
        return cls.OPPORTUNITIES
