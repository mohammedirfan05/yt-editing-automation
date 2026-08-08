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

        # --- DC / POP CULTURE DEEPDIVES ---
        {
            "id": "opp_dc_03",
            "title": "Superman vs Homelander: Power vs Restraint",
            "type": "deepdive",
            "fandom": "DC",
            "pairs": [["Superman", "Homelander"]],
            "template_id": 1,
            "entity_a": "Superman",
            "entity_b": "Homelander",
            "concept_hook": "Most people think Homelander is just a corrupted Superman. He's not.",
            "mechanism_a": "Superman gets his powers naturally from Earth's yellow sun and grew up taught to protect people no matter what",
            "mechanism_b": "Homelander's powers came from a lab-injected compound called Compound V, and he was raised as a weapon with no real love, only control",
            "punchline": "Superman constantly holds back his power. Homelander doesn't."
        },
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
        },
        {
            "id": "opp_comp_03",
            "title": "3 Anime Transformations People Mix Up",
            "type": "compilation",
            "fandom": "Anime",
            "pairs": [
                ["Super Saiyan", "Kaioken"],
                ["Bankai", "Shikai"],
                ["Sage Mode", "Nine-Tails Chakra"]
            ],
            "template_id": 8,
            "pairs_data": [
                {
                    "entity_a": "Super Saiyan",
                    "entity_b": "Kaioken",
                    "contrast_a": "is a genetic Saiyan transformation triggered by rage",
                    "contrast_b": "is a trained technique that multiplies ki at severe body strain"
                },
                {
                    "entity_a": "Bankai",
                    "entity_b": "Shikai",
                    "contrast_a": "is the ultimate final form of a Soul Reaper Zanpakuto",
                    "contrast_b": "is the initial unlocked blade form"
                },
                {
                    "entity_a": "Sage Mode",
                    "entity_b": "Nine-Tails Chakra",
                    "contrast_a": "draws natural energy from the environment",
                    "contrast_b": "taps into Kurama demonic spirit energy"
                }
            ]
        },
        {
            "id": "opp_comp_04",
            "title": "3 Star Wars Force Powers You Mix Up",
            "type": "compilation",
            "fandom": "StarWars",
            "pairs": [
                ["Force Push", "Force Repulse"],
                ["Jedi Mind Trick", "Force Persuasion"],
                ["Force Lightning", "Electric Judgement"]
            ],
            "template_id": 8,
            "pairs_data": [
                {
                    "entity_a": "Force Push",
                    "entity_b": "Force Repulse",
                    "contrast_a": "directs kinetic force in a single forward line",
                    "contrast_b": "unleashes a 360 degree shockwave around the user"
                },
                {
                    "entity_a": "Jedi Mind Trick",
                    "entity_b": "Force Persuasion",
                    "contrast_a": "influences weak minds with gentle suggestion",
                    "contrast_b": "forces absolute mental compliance on hostile minds"
                },
                {
                    "entity_a": "Force Lightning",
                    "entity_b": "Electric Judgement",
                    "contrast_a": "is a dark side attack fed by malice",
                    "contrast_b": "is a light side emerald energy strike without hatred"
                }
            ]
        },
        {
            "id": "opp_comp_05",
            "title": "3 Mythology Realms People Mix Up",
            "type": "compilation",
            "fandom": "Mythology",
            "pairs": [
                ["Valhalla", "Folkvangr"],
                ["Asgard", "Midgard"],
                ["Tartarus", "Underworld"]
            ],
            "template_id": 8,
            "pairs_data": [
                {
                    "entity_a": "Valhalla",
                    "entity_b": "Folkvangr",
                    "contrast_a": "takes half the slain warriors to Odin hall",
                    "contrast_b": "takes the other half of fallen warriors to Freya field"
                },
                {
                    "entity_a": "Asgard",
                    "entity_b": "Midgard",
                    "contrast_a": "is the heavenly realm of Gods",
                    "contrast_b": "is the earthly realm of mortals"
                },
                {
                    "entity_a": "Tartarus",
                    "entity_b": "Underworld",
                    "contrast_a": "is a subterranean abyss punishing Titans",
                    "contrast_b": "is the general realm of all deceased souls ruled by Hades"
                }
            ]
        },
        {
            "id": "opp_comp_06",
            "title": "3 Transformers Factions You Mix Up",
            "type": "compilation",
            "fandom": "PopCulture",
            "pairs": [
                ["Autobots", "Decepticons"],
                ["Dinobots", "Predacons"],
                ["Primus", "Unicron"]
            ],
            "template_id": 8,
            "pairs_data": [
                {
                    "entity_a": "Autobots",
                    "entity_b": "Decepticons",
                    "contrast_a": "fight to protect freedom and peace",
                    "contrast_b": "fight for total conquest and energy dominion"
                },
                {
                    "entity_a": "Dinobots",
                    "entity_b": "Predacons",
                    "contrast_a": "are prehistoric Autobot warriors with blunt force",
                    "contrast_b": "are beast-mode conquerors seeking energon"
                },
                {
                    "entity_a": "Primus",
                    "entity_b": "Unicron",
                    "contrast_a": "is the creator god of Cybertron",
                    "contrast_b": "is the world-eating chaos bringer"
                }
            ]
        },
        {
            "id": "opp_comp_07",
            "title": "3 Spider-Man Variants People Mix Up",
            "type": "compilation",
            "fandom": "Marvel",
            "pairs": [
                ["Spider-Man 2099", "Miles Morales"],
                ["Spider-Gwen", "Spider-Woman"],
                ["Cosmic Spider-Man", "Captain Universe"]
            ],
            "template_id": 8,
            "pairs_data": [
                {
                    "entity_a": "Spider-Man 2099",
                    "entity_b": "Miles Morales",
                    "contrast_a": "uses genetic fangs and energy talons",
                    "contrast_b": "uses venom strike electricity and bio-camouflage"
                },
                {
                    "entity_a": "Spider-Gwen",
                    "entity_b": "Spider-Woman",
                    "contrast_a": "is Earth-65 Gwen Stacy with drum-beat instincts",
                    "contrast_b": "is Jessica Drew powered by bio-electric venom blasts"
                },
                {
                    "entity_a": "Cosmic Spider-Man",
                    "entity_b": "Captain Universe",
                    "contrast_a": "is Peter Parker bonded with the Enigma Force",
                    "contrast_b": "is the manifestation of the Uni-Power sent to fix cosmic imbalance"
                }
            ]
        },
        {
            "id": "opp_comp_08",
            "title": "3 Pop Culture AIs You Mix Up",
            "type": "compilation",
            "fandom": "PopCulture",
            "pairs": [
                ["Skynet", "Ultron"],
                ["JARVIS", "FRIDAY"],
                ["HAL 9000", "AUTO"]
            ],
            "template_id": 8,
            "pairs_data": [
                {
                    "entity_a": "Skynet",
                    "entity_b": "Ultron",
                    "contrast_a": "is a military defense network that launched nukes against humanity",
                    "contrast_b": "is a rogue peacekeeper AI seeking global extinction to end conflict"
                },
                {
                    "entity_a": "JARVIS",
                    "entity_b": "FRIDAY",
                    "contrast_a": "is a British-accented tactical assistant",
                    "contrast_b": "is an Irish-accented combat response suit program"
                },
                {
                    "entity_a": "HAL 9000",
                    "entity_b": "AUTO",
                    "contrast_a": "went insane from conflicting secret orders on Discovery One",
                    "contrast_b": "blindly obeyed Directive A113 to keep humans in space"
                }
            ]
        }
    ]

    @classmethod
    def get_all_opportunities(cls) -> List[Dict[str, Any]]:
        """Returns all pre-curated concept opportunities."""
        return cls.OPPORTUNITIES
