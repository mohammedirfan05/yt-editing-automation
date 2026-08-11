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
            "mechanism_a": "The Hellbat suit was forged by the Justice League in the sun to fight Gods, but drains Batman's life force",
            "mechanism_b": "The Hulkbuster uses heavy hydraulic armor plates and satellite parts to withstand brute physical force",
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
                    "contrast_b": "unleashes a 360 degree shockwave"
                },
                {
                    "entity_a": "Jedi Mind Trick",
                    "entity_b": "Force Persuasion",
                    "contrast_a": "influences weak minds with gentle suggestion",
                    "contrast_b": "forces absolute mental compliance on hostiles"
                },
                {
                    "entity_a": "Force Lightning",
                    "entity_b": "Electric Judgement",
                    "contrast_a": "is a dark side attack fed by malice",
                    "contrast_b": "is a light side emerald energy strike"
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
                    "contrast_a": "uses genetic fangs and talons",
                    "contrast_b": "uses venom electricity and camouflage"
                },
                {
                    "entity_a": "Spider-Gwen",
                    "entity_b": "Spider-Woman",
                    "contrast_a": "is Gwen Stacy with drum-beat instincts",
                    "contrast_b": "is Jessica Drew with bio-electric venom"
                },
                {
                    "entity_a": "Cosmic Spider-Man",
                    "entity_b": "Captain Universe",
                    "contrast_a": "is Peter Parker bonded with Enigma Force",
                    "contrast_b": "is Uni-Power sent for cosmic balance"
                }
            ]
        },
        {
            "id": "opp_marvel_10",
            "title": "Necrosword vs All-Black: Marvel Lore",
            "type": "deepdive",
            "fandom": "Marvel",
            "pairs": [["All-Black The Necrosword", "Symbiotes"]],
            "template_id": 1,
            "entity_a": "All-Black The Necrosword",
            "entity_b": "Klyntar Symbiotes",
            "concept_hook": "Most fans think Knull created symbiotes before weapons. They're wrong.",
            "mechanism_a": "All-Black was the very first primordial weapon forged by Knull from the shadow of a slain Celestial",
            "mechanism_b": "Klyntar symbiotes were created later as living offspring spawned from the Necrosword's dark divine mass",
            "punchline": "The Necrosword is the god-slaying father of all symbiotes."
        },
        {
            "id": "opp_dc_10",
            "title": "Speed Force vs Negative Speed Force",
            "type": "deepdive",
            "fandom": "DC",
            "pairs": [["Speed Force", "Negative Speed Force"]],
            "template_id": 1,
            "entity_a": "The Speed Force",
            "entity_b": "The Negative Speed Force",
            "concept_hook": "Most people think Reverse Flash uses Barry's Speed Force. He doesn't.",
            "mechanism_a": "The Speed Force is an extra-dimensional kinetic field generated by Barry Allen running forward in time",
            "mechanism_b": "The Negative Speed Force was created by Eobard Thawne to decay and consume kinetic energy",
            "punchline": "The Speed Force generates motion, while the Negative Speed Force rots it away."
        },
        {
            "id": "opp_anime_10",
            "title": "Domain Expansion vs Simple Domain",
            "type": "deepdive",
            "fandom": "Anime",
            "pairs": [["Domain Expansion", "Simple Domain"]],
            "template_id": 1,
            "entity_a": "Domain Expansion",
            "entity_b": "Simple Domain",
            "concept_hook": "Most fans think Simple Domain is just a weak Domain Expansion. It's not.",
            "mechanism_a": "Domain Expansion manifests your innate cursed technique into a barrier guaranteeing a sure-hit attack",
            "mechanism_b": "Simple Domain is an anti-domain barrier technique that neutralizes the sure-hit effect of an enemy's domain",
            "punchline": "Domain Expansion forces a guaranteed hit, while Simple Domain cancels it out."
        },
        {
            "id": "opp_marvel_11",
            "title": "Thanos vs Darkseid: Marvel vs DC Gods",
            "type": "deepdive",
            "fandom": "Marvel",
            "pairs": [["Thanos", "Darkseid"]],
            "template_id": 1,
            "entity_a": "Thanos",
            "entity_b": "Darkseid",
            "concept_hook": "Most fans think Thanos and Darkseid are copies of each other. They're wrong.",
            "mechanism_a": "Thanos is a warlord titan seeking the Infinity Stones to rebalance resource scarcity in the universe",
            "mechanism_b": "Darkseid is a New God ruler of Apokolips seeking the Anti-Life Equation to strip all free will across reality",
            "punchline": "Thanos seeks universal balance, while Darkseid seeks total mental enslavement."
        },
        {
            "id": "opp_dc_11",
            "title": "Doctor Strange vs Doctor Fate",
            "type": "deepdive",
            "fandom": "DC",
            "pairs": [["Doctor Strange", "Doctor Fate"]],
            "template_id": 1,
            "entity_a": "Doctor Strange",
            "entity_b": "Doctor Fate",
            "concept_hook": "Most fans think Doctor Fate copied Doctor Strange. It's actually the opposite.",
            "mechanism_a": "Doctor Strange draws arcane energy through study and spells as Sorcerer Supreme",
            "mechanism_b": "Doctor Fate is a mortal host possessed by Nabu, a Lord of Order through the Helmet of Fate",
            "punchline": "Strange casts spells with human agency, while Fate acts as a divine puppet of Order."
        },
        {
            "id": "opp_anime_11",
            "title": "Goku Ultra Instinct vs Vegeta Ultra Ego",
            "type": "deepdive",
            "fandom": "Anime",
            "pairs": [["Ultra Instinct", "Ultra Ego"]],
            "template_id": 1,
            "entity_a": "Ultra Instinct",
            "entity_b": "Ultra Ego",
            "concept_hook": "Most DBZ fans think Ultra Ego is just a purple Ultra Instinct. It's not.",
            "mechanism_a": "Ultra Instinct lets Goku's body dodge attacks autonomously by detaching emotion",
            "mechanism_b": "Ultra Ego powers up Vegeta's destruction energy by absorbing physical damage",
            "punchline": "Ultra Instinct avoids damage, while Ultra Ego thrives on taking hits."
        },
        {
            "id": "opp_anime_12",
            "title": "Gojo Limitless vs Sukuna Malevolent Shrine",
            "type": "deepdive",
            "fandom": "Anime",
            "pairs": [["Unlimited Void", "Malevolent Shrine"]],
            "template_id": 1,
            "entity_a": "Unlimited Void",
            "entity_b": "Malevolent Shrine",
            "concept_hook": "Most JJK fans think Gojo and Sukuna's domains work the same way. They don't.",
            "mechanism_a": "Unlimited Void floods the enemy's brain with infinite information to paralyze them",
            "mechanism_b": "Malevolent Shrine has no outer barrier, unleashing relentless slashes across a 200m radius",
            "punchline": "Gojo's domain overwhelms the mind, while Sukuna's domain shreds physical reality."
        },
        {
            "id": "opp_pop_10",
            "title": "Saitama vs Superman: Unmatched Power",
            "type": "deepdive",
            "fandom": "PopCulture",
            "pairs": [["Saitama", "Superman"]],
            "template_id": 1,
            "entity_a": "Saitama",
            "entity_b": "Superman",
            "concept_hook": "Most people think Saitama gets his strength from alien biology. He doesn't.",
            "mechanism_a": "Saitama broke his natural biological limiter through sheer human willpower and basic training",
            "mechanism_b": "Superman absorbs solar radiation from Earth's yellow sun into Kryptonian cells",
            "punchline": "Superman relies on solar energy, while Saitama shattered the limits of human power."
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

    OPPORTUNITIES_URDU = [
        {
            "id": "farq_islamic_01",
            "title": "Nabi vs Rasool: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Nabi", "Rasool"]],
            "template_id": 1,
            "entity_a": "Nabi",
            "entity_b": "Rasool",
            "concept_hook": "Aksar log samajhte hain ke Nabi aur Rasool ek hi hain, lekin aisa nahi hai.",
            "mechanism_a": "Allah Ta'ala ki taraf se wahi aur hidayat haasik karte hain pehli shariat ko aage badhane ke liye",
            "mechanism_b": "Naye Aasmani Kitab aur naye shariat ke saath nayi ummat ki taraf bheje jaate hain",
            "punchline": "Har Rasool Nabi hota hai, lekin har Nabi Rasool nahi hota."
        },
        {
            "id": "farq_islamic_02",
            "title": "Hajj vs Umrah: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Hajj", "Umrah"]],
            "template_id": 1,
            "entity_a": "Hajj",
            "entity_b": "Umrah",
            "concept_hook": "Aksar log Hajj aur Umrah ko ek jaisa ziarat samajhte hain, lekin inme bada farq hai.",
            "mechanism_a": "Islam ka farz rukn hai jo saal mein sirf Zil-Hajj ke khass dino mein ada kiya jata hai",
            "mechanism_b": "Nafli ibadat hai jise saal mein kisi bhi waqt ada kiya ja sakta hai",
            "punchline": "Hajj mahsoos dino ka farz ibadat hai, jabke Umrah saal bhar mein kabhi bhi kiya jata hai."
        },
        {
            "id": "farq_islamic_03",
            "title": "Fard vs Sunnah: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Fard", "Sunnah"]],
            "template_id": 1,
            "entity_a": "Fard",
            "entity_b": "Sunnah",
            "concept_hook": "Aksar log Fard aur Sunnah mein farq nahi samajhte, lekin inke ahkaam alag hain.",
            "mechanism_a": "Allah ki taraf se lazmi hukum hai jise chorna gunah hai",
            "mechanism_b": "Nabi Kareem Sallallahu Alaihi Wasallam ki tareeqa hai jise karne par sawab aur na karne par mahrumi hai",
            "punchline": "Fard chhorne par gunah aur azab hai, jabke Sunnah Nabi ki mohobbat aur tareeqa hai."
        },
        {
            "id": "farq_islamic_04",
            "title": "Zakat vs Sadaqah: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Zakat", "Sadaqah"]],
            "template_id": 1,
            "entity_a": "Zakat",
            "entity_b": "Sadaqah",
            "concept_hook": "Aksar log Zakat aur Sadaqah ko ek hi tarah ka khairat samajhte hain, lekin aisa nahi hai.",
            "mechanism_a": "Maaldar Musalman par saal mein ek baar nisab par 2.5% farz hai",
            "mechanism_b": "Kisi bhi waqt apni marzi se di jaane wali nafli khairat hai",
            "punchline": "Zakat farz haq hai, jabke Sadaqah dil ki khushi se diya jata hai."
        },

        {
            "id": "farq_islamic_05",
            "title": "Quran vs Hadith: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Quran", "Hadith"]],
            "template_id": 1,
            "entity_a": "Quran",
            "entity_b": "Hadith",
            "concept_hook": "Aksar log Quran aur Hadith dono ko ek jaisi wahy samajhte hain, lekin inme bunyadi farq hai.",
            "mechanism_a": "seedha Allah ka kalam hai jo Jibreel AS ke zariye Nabi SAW par nazil hua aur lafz-ba-lafz mahfooz hai",
            "mechanism_b": "Nabi SAW ke aqwaal, afaal aur tagreeraat hain jo sahaabah ne yaad rakhe aur baad mein sanad ke saath likhe gaye",
            "punchline": "Quran Allah ka seedha kalam hai, jabke Hadith Nabi SAW ki zindagi ki tafseer hai."
        },
        {
            "id": "farq_islamic_06",
            "title": "Shirk vs Bidah: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Shirk", "Bidah"]],
            "template_id": 1,
            "entity_a": "Shirk",
            "entity_b": "Bidah",
            "concept_hook": "Aksar log Shirk aur Bidah ko ek hi burai samajhte hain, lekin inme bada farq hai.",
            "mechanism_a": "Allah ke saath kisi ko shareek karna hai, yani ibadat mein ghair Allah ko shamil karna",
            "mechanism_b": "Deen mein aisi nai cheez daalna hai jiske liye koi saboot na ho, chahe niyat achi bhi ho",
            "punchline": "Shirk tawheed ko tod deta hai, jabke Bidah sunnat ke khilaf naya tariqa hai."
        },
        {
            "id": "farq_islamic_07",
            "title": "Salah vs Dua: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Salah", "Dua"]],
            "template_id": 1,
            "entity_a": "Salah",
            "entity_b": "Dua",
            "concept_hook": "Aksar log samajhte hain ke Salah aur Dua ek hi cheez hain, lekin ye dono alag hain.",
            "mechanism_a": "waqt ke saath mukammal ibadat hai jiske arkaan, niyyat aur tareeqa muqarrar hain aur din mein paanch baar farz hai",
            "mechanism_b": "seedha Allah se maangna hai jo kisi bhi waqt, kisi bhi zabaan mein, kisi bhi haal mein ki ja sakti hai",
            "punchline": "Salah Allah ki taraf se muqarrar ibadat hai, jabke Dua ek Musalman ki seedhi pukaar hai."
        },
        {
            "id": "farq_islamic_08",
            "title": "Tawbah vs Istighfar: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Tawbah", "Istighfar"]],
            "template_id": 1,
            "entity_a": "Tawbah",
            "entity_b": "Istighfar",
            "concept_hook": "Aksar log Tawbah aur Istighfar ko aik hi samajh lete hain, lekin dono mein bunyadi farq hai.",
            "mechanism_a": "mukammal rujoo hai jisme gunah chhodna, pachtana, aur dobara na karne ka azm zaruri hai",
            "mechanism_b": "Allah se maafi maangna hai jo Tawbah ka ek hissa hai lekin shart nahi ke puri Tawbah ho",
            "punchline": "Istighfar zuban ki maafi hai, jabke Tawbah dil ki mukammal waapsi hai."
        },
        {
            "id": "farq_islamic_09",
            "title": "Jannah vs Firdaus: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Jannah", "Firdaus"]],
            "template_id": 1,
            "entity_a": "Jannah",
            "entity_b": "Firdaus",
            "concept_hook": "Aksar log samajhte hain ke Jannah aur Firdaus ek hi jagah ka naam hai, lekin aisa nahi hai.",
            "mechanism_a": "jannat ke liye aam lafz hai jo saat darja jannat ke liye use hota hai aur kisi bhi darje se murad ho sakta hai",
            "mechanism_b": "jannat ka sabse aala aur behtareen darjah hai jahan se jannat ki nahrein nikalti hain aur Arsh e Elahi iske upar hai",
            "punchline": "Jannah jannat ka aam naam hai, jabke Firdaus uska sabse aacha aur aacha darjah hai."
        },
        {
            "id": "farq_islamic_10",
            "title": "Roza vs Qaza Roza: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Roza", "Qaza Roza"]],
            "template_id": 1,
            "entity_a": "Roza",
            "entity_b": "Qaza Roza",
            "concept_hook": "Aksar log samajhte hain ke Ramadan ke baad Qaza Roza rakhna same sawab deta hai, lekin aisa nahi.",
            "mechanism_a": "Ramadan ke mahine mein Allah ke hukum par ibadat ke liye roza rakhna hai jisme azeem sawab aur lailat ul qadr hai",
            "mechanism_b": "Ramadan ke choote hue roze ki qaza hai jo farz hone ki wajah se baad mein poora kiya jata hai",
            "punchline": "Ramadan ka Roza ibadat ka mausam hai, jabke Qaza Roza farz zimmedari ka poora karna hai."
        },
        {
            "id": "farq_islamic_11",
            "title": "Masjid vs Masjid al-Haram: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Masjid", "Masjid al-Haram"]],
            "template_id": 1,
            "entity_a": "Masjid",
            "entity_b": "Masjid al-Haram",
            "concept_hook": "Aksar log samajhte hain ke kisi bhi masjid mein namaz ka sawab barabar hota hai, lekin aisa nahi.",
            "mechanism_a": "aam ibadat gah hai jahan namaz ki jamaat ada hoti hai aur sawab aam jamaat se milta hai",
            "mechanism_b": "Makkah ki muqaddas masjid hai jahan ek namaz kisi bhi dusri jagah ki ek lakh namaz se afzal hai",
            "punchline": "Aam Masjid mein namaz barakar hai, jabke Masjid al-Haram mein ek lakh guna sawab hai."
        },
        {
            "id": "farq_islamic_12",
            "title": "Iman vs Islam: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Iman", "Islam"]],
            "template_id": 1,
            "entity_a": "Iman",
            "entity_b": "Islam",
            "concept_hook": "Aksar log Iman aur Islam ko ek hi cheez samajhte hain, lekin dono mein gehra farq hai.",
            "mechanism_a": "andar ki sacchi tasdeeq hai, dil se Allah, Rasool, malaik, kitabon, qayamat aur taqdir par yaqeen",
            "mechanism_b": "zaahiri amaal hain, paanch arkaan: Shahadah, Salah, Sawm, Zakat, aur Hajj",
            "punchline": "Iman dil ki gehri sachai hai, jabke Islam usi yaqeen ka zaahiri amali izhar hai."
        },
        {
            "id": "farq_islamic_13",
            "title": "Kaffarah vs Fidyah: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Kaffarah", "Fidyah"]],
            "template_id": 1,
            "entity_a": "Kaffarah",
            "entity_b": "Fidyah",
            "concept_hook": "Aksar log Kaffarah aur Fidyah ko ek jaisi saza samajhte hain, lekin ye alag alag hain.",
            "mechanism_a": "jaan boojh kar kisi ahad ya ibadat ke toorne ka kaffara hai, jaise qasd se roza todne par ek ghulam aazad karna ya 60 roze",
            "mechanism_b": "mazeerat ki wajah se ibadat ada na kar sakne par muawwaza hai, jaise bimar shaks ka roza chhod kar mazloom ko khana dena",
            "punchline": "Kaffarah kasdi ghalti ki saza hai, jabke Fidyah majburi ka muawwaza hai."
        },
        {
            "id": "farq_islamic_14",
            "title": "Wudu vs Ghusl: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Wudu", "Ghusl"]],
            "template_id": 1,
            "entity_a": "Wudu",
            "entity_b": "Ghusl",
            "concept_hook": "Aksar log samajhte hain ke Ghusl sirf napaaki ke liye hai, lekin dono mein poora farq hai.",
            "mechanism_a": "choti tahaarat hai jo namaz se pehle munh, haath, sar aur paaon dhone se hasil hoti hai",
            "mechanism_b": "badi tahaarat hai jo poore badan ko ghusal dene se janabat ya haidh ke baad hasil hoti hai",
            "punchline": "Wudu rozmarra namaz ki tahaarat hai, jabke Ghusl poori tahaarat ki zarurat hai."
        },
        {
            "id": "farq_islamic_comp_01",
            "title": "3 Islamic Concepts Inme Farq Kya Hai",
            "type": "compilation",
            "fandom": "Islamic",
            "pairs": [
                ["Nabi", "Rasool"],
                ["Hajj", "Umrah"],
                ["Zakat", "Sadaqah"]
            ],
            "template_id": 8,
            "pairs_data": [
                {
                    "entity_a": "Nabi",
                    "entity_b": "Rasool",
                    "contrast_a": "wahi haasil karta hai",
                    "contrast_b": "nayi shariat aur kitab lata hai"
                },
                {
                    "entity_a": "Hajj",
                    "entity_b": "Umrah",
                    "contrast_a": "Zil-Hajj ke khass dino mein farz hai",
                    "contrast_b": "saal mein kisi bhi waqt ada kiya jata hai"
                },
                {
                    "entity_a": "Zakat",
                    "entity_b": "Sadaqah",
                    "contrast_a": "saal mein 2.5% farz rukn hai",
                    "contrast_b": "kisi bhi waqt nafli khairat hai"
                }
            ]
        },
        {
            "id": "farq_islamic_comp_02",
            "title": "Quran Hadith aur Iman: Farq Kya Hai",
            "type": "compilation",
            "fandom": "Islamic",
            "pairs": [
                ["Quran", "Hadith"],
                ["Shirk", "Bidah"],
                ["Iman", "Islam"]
            ],
            "template_id": 8,
            "pairs_data": [
                {
                    "entity_a": "Quran",
                    "entity_b": "Hadith",
                    "contrast_a": "Allah ka seedha kalam aur lafz-ba-lafz wahy hai",
                    "contrast_b": "Nabi SAW ke aqwaal aur afaal ka sanadyafta majmua hai"
                },
                {
                    "entity_a": "Shirk",
                    "entity_b": "Bidah",
                    "contrast_a": "Allah ke saath shareek banana tawheed ko tod deta hai",
                    "contrast_b": "deen mein saboot ke bagair nai cheez daalna hai"
                },
                {
                    "entity_a": "Iman",
                    "entity_b": "Islam",
                    "contrast_a": "dil ki andar ki sacchi tasdeeq hai",
                    "contrast_b": "paanch arkaan ka zaahiri amali izhar hai"
                }
            ]
        },
        {
            "id": "farq_islamic_comp_03",
            "title": "Tahaarat Ibadat aur Maafi: Farq Kya Hai",
            "type": "compilation",
            "fandom": "Islamic",
            "pairs": [
                ["Wudu", "Ghusl"],
                ["Salah", "Dua"],
                ["Tawbah", "Istighfar"]
            ],
            "template_id": 8,
            "pairs_data": [
                {
                    "entity_a": "Wudu",
                    "entity_b": "Ghusl",
                    "contrast_a": "choti tahaarat namaz ke liye hai",
                    "contrast_b": "poori tahaarat janabat ke baad zaruri hai"
                },
                {
                    "entity_a": "Salah",
                    "entity_b": "Dua",
                    "contrast_a": "Allah ka muqarrar farz hai paanch waqt",
                    "contrast_b": "kisi bhi waqt Allah se seedhi pukaar hai"
                },
                {
                    "entity_a": "Tawbah",
                    "entity_b": "Istighfar",
                    "contrast_a": "dil se mukammal rujoo aur azm hai",
                    "contrast_b": "zuban se maafi ki darkhwast hai"
                }
            ]
        },
        {
            "id": "farq_islamic_comp_04",
            "title": "Roza Kaffarah aur Jannah: Farq Kya Hai",
            "type": "compilation",
            "fandom": "Islamic",
            "pairs": [
                ["Roza", "Qaza Roza"],
                ["Kaffarah", "Fidyah"],
                ["Jannah", "Firdaus"]
            ],
            "template_id": 8,
            "pairs_data": [
                {
                    "entity_a": "Roza",
                    "entity_b": "Qaza Roza",
                    "contrast_a": "Ramadan mein ibadat ka sawab hai",
                    "contrast_b": "choote hue roze ki baad mein zimmedari hai"
                },
                {
                    "entity_a": "Kaffarah",
                    "entity_b": "Fidyah",
                    "contrast_a": "kasdi ghalti ki saza hai",
                    "contrast_b": "majburi mein ibadat na kar sakne ka muawwaza hai"
                },
                {
                    "entity_a": "Jannah",
                    "entity_b": "Firdaus",
                    "contrast_a": "jannat ka aam naam hai",
                    "contrast_b": "jannat ka sabse aala darjah hai"
                }
            ]
        }
    ]

    @classmethod
    def get_all_opportunities(cls, channel: str = "dontmixthis") -> List[Dict[str, Any]]:
        """Returns pre-curated concept opportunities based on target channel."""
        if channel == "farqkya":
            return cls.OPPORTUNITIES_URDU
        return cls.OPPORTUNITIES
