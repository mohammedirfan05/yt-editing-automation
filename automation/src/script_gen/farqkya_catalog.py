"""
Farq Kya Concept Catalog Module.
Curated database of high-potential Islamic X vs Y comparison topics in Roman Urdu.
Uses retention-first hook engineering (Paradoxes, Worship Stakes, Misconception Shatters).
"""

from typing import Any, Dict, List


class FarqKyaCatalog:
    """Curated database of Islamic X vs Y concept opportunities for Farq Kya channel."""

    OPPORTUNITIES = [
        {
            "id": "farq_fk_opt_01",
            "title": "Nabi vs Rasool: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Nabi", "Rasool"]],
            "template_id": 1,
            "entity_a": "Nabi",
            "entity_b": "Rasool",
            "concept_hook": "Har Rasool Nabi hota hai... lekin har Nabi Rasool kyun nahi hota?",
            "mechanism_a": "pehli shariat ko aage badhate hain aur wahi haasil karte hain",
            "mechanism_b": "nayi aasmani kitab aur nayi shariat ke saath aate hain",
            "punchline": "Har Rasool ke paas Nayi Shariat hoti hai, jabke Nabi pichli shariat ko aam karte hain."
        },
        {
            "id": "farq_fk_opt_02",
            "title": "Hajj vs Umrah: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Hajj", "Umrah"]],
            "template_id": 1,
            "entity_a": "Hajj",
            "entity_b": "Umrah",
            "concept_hook": "Ek saal mein sirf ek baar hota hai... jabke doosra saal bhar kabhi bhi!",
            "mechanism_a": "Zil-Hajj ke khass dino mein ada kiya jane wala farz rukn hai",
            "mechanism_b": "saal mein kisi bhi waqt ada ki jane wali nafli ibadat hai",
            "punchline": "Hajj Islam ka farz rukn hai, jabke Umrah nafli ziaraat."
        },
        {
            "id": "farq_fk_opt_03",
            "title": "Fard vs Sunnah: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Fard", "Sunnah"]],
            "template_id": 1,
            "entity_a": "Fard",
            "entity_b": "Sunnah",
            "concept_hook": "Ek ko chhorne par azab hai... lekin doosre ko chhorne par kya hoga?",
            "mechanism_a": "Allah ka lazmi hukum hai jise chhorna gunah hai",
            "mechanism_b": "Nabi Kareem (SAW) ka mubaarak tareeqa hai jise karne par sawab hai",
            "punchline": "Fard Farz zimmedari hai, jabke Sunnah Nabi ki mohobbat aur tareeqa."
        },
        {
            "id": "farq_fk_opt_04",
            "title": "Zakat vs Sadaqah: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Zakat", "Sadaqah"]],
            "template_id": 1,
            "entity_a": "Zakat",
            "entity_b": "Sadaqah",
            "concept_hook": "Kya aapko pata hai konsi maaldari par khairat farz hoti hai aur konsi aam?",
            "mechanism_a": "saal mein ek baar saahib-e-nisab par 2.5% farz hai",
            "mechanism_b": "kisi bhi waqt aur kitni bhi miqdar mein nafli khairat hai",
            "punchline": "Zakat farz maali ibadat hai, jabke Sadaqah aam nafli neki."
        },
        {
            "id": "farq_fk_opt_05",
            "title": "Quran vs Hadith: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Quran", "Hadith"]],
            "template_id": 1,
            "entity_a": "Quran",
            "entity_b": "Hadith",
            "concept_hook": "Dono deen ka sarchashma hain... lekin lafz kis ke hain?",
            "mechanism_a": "Allah Ta'ala ka seedha kalam aur lafz-ba-lafz wahy hai",
            "mechanism_b": "Nabi SAW ke mubaarak aqwaal, afaal aur tareeqe ka majmua hai",
            "punchline": "Quran Allah ka lafzi kalam hai, jabke Hadith Nabi ki rasoolana tashreeh."
        },
        {
            "id": "farq_fk_opt_06",
            "title": "Shirk vs Bidah: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Shirk", "Bidah"]],
            "template_id": 1,
            "entity_a": "Shirk",
            "entity_b": "Bidah",
            "concept_hook": "In dono mein se konsa gunah kabhi maaf nahi hota?",
            "mechanism_a": "Allah ke saath kisi aur ko shareek karna hai jo yaqeen ko tod deta hai",
            "mechanism_b": "deen mein bagair saboot ke nayi cheez ijad karna hai",
            "punchline": "Shirk Ibadat mein shiraakat hai, jabke Bidah Deen mein ijad."
        },
        {
            "id": "farq_fk_opt_07",
            "title": "Salah vs Dua: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Salah", "Dua"]],
            "template_id": 1,
            "entity_a": "Salah",
            "entity_b": "Dua",
            "concept_hook": "Dono Allah se rabta hain... lekin ek ke bina deen adhura kyun hai?",
            "mechanism_a": "muqarrar waqt aur ahkaam ke saath paanch waqt ki farz ibadat hai",
            "mechanism_b": "kisi bhi waqt, kisi bhi zaban mein Allah se seedhi pukaar hai",
            "punchline": "Salah muqarrar rukn hai, jabke Dua bando ki aazad pukaar."
        },
        {
            "id": "farq_fk_opt_08",
            "title": "Tawbah vs Istighfar: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Tawbah", "Istighfar"]],
            "template_id": 1,
            "entity_a": "Tawbah",
            "entity_b": "Istighfar",
            "concept_hook": "Ek zuban ka lafz hai... jabke doosra dil ki poori waapsi!",
            "mechanism_a": "dil se gunah chhodna aur dobara na karne ka azm hai",
            "mechanism_b": "zuban se Allah se maafi aur maghfirat ki darkhwast hai",
            "punchline": "Istighfar zuban ki pukaar hai, jabke Tawbah dil ki mukammal waapsi."
        },
        {
            "id": "farq_fk_opt_09",
            "title": "Jannah vs Firdaus: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Jannah", "Firdaus"]],
            "template_id": 1,
            "entity_a": "Jannah",
            "entity_b": "Firdaus",
            "concept_hook": "Jannat ke tamaam darjat ek jaisay nahi hotay... sabse aala konsa hai?",
            "mechanism_a": "jannat ka aam naam hai jo tamaam darjat ke liye istemal hota hai",
            "mechanism_b": "jannat ka sabse buland darjah hai jiske upar Arsh-e-Elahi hai",
            "punchline": "Jannah tamaam darjat ka naam hai, jabke Firdaus sabse aala darjah."
        },
        {
            "id": "farq_fk_opt_10",
            "title": "Masjid vs Masjid al-Haram: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Aam Masjid", "Masjid al-Haram"]],
            "template_id": 1,
            "entity_a": "Aam Masjid",
            "entity_b": "Masjid al-Haram",
            "concept_hook": "Ek namaz ka sawab ek lakh namazon ke barabar kahan milta hai?",
            "mechanism_a": "aam ibadat gah hai jahan jamaat ka aada sawab milta hai",
            "mechanism_b": "Makkah ki muqaddas masjid hai jahan ek namaz 1 lakh namaz ke barabar hai",
            "punchline": "Aam Masjid mein 27 guna sawab hai, jabke Masjid al-Haram mein 1 lakh guna."
        },
        {
            "id": "farq_fk_opt_11",
            "title": "Haram vs Makruh: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Haram", "Makruh"]],
            "template_id": 1,
            "entity_a": "Haram",
            "entity_b": "Makruh",
            "concept_hook": "Ek ko karne par gunah aur azab hai... lekin doosre ko karne par kya hoga?",
            "mechanism_a": "shari'at ka qati aur lazmi mana karda amal hai jise karne par gunah hai",
            "mechanism_b": "napasandida amal hai jise chhorne par sawab hai lekin karne par azab nahi",
            "punchline": "Haram qati gunah hai, jabke Makruh napasandida amal."
        },
        {
            "id": "farq_fk_opt_12",
            "title": "Halal vs Tayyib: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Halal", "Tayyib"]],
            "template_id": 1,
            "entity_a": "Halal",
            "entity_b": "Tayyib",
            "concept_hook": "Kya aapko pata hai konsi khuraak jaiz hone ke saath paak aur faide-mand hoti hai?",
            "mechanism_a": "shari'at ke mutabiq jaiz aur khorak ki ijazat rakhta hai",
            "mechanism_b": "paak, saaf, aur jism ke liye mufeed aur aala meyaar ka hota hai",
            "punchline": "Halal qanooni ijazat hai, jabke Tayyib uski paakizgi aur meyaar."
        },
        {
            "id": "farq_fk_opt_13",
            "title": "Iman vs Ihsan: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Iman", "Ihsan"]],
            "template_id": 1,
            "entity_a": "Iman",
            "entity_b": "Ihsan",
            "concept_hook": "Deen ka sabse aala maqam konsa hai... jab aap Allah ko dekh rahe ho?",
            "mechanism_a": "dil se yaqeen aur ghaib par tasdeeq ka naam hai",
            "mechanism_b": "ibadat ka wo aala meyaar hai jaise aap Allah ko dekh rahe ho",
            "punchline": "Iman yaqeen ki bunyad hai, jabke Ihsan ibadat ka husn aur kamal."
        },
        {
            "id": "farq_fk_opt_14",
            "title": "Kaffarah vs Fidyah: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Kaffarah", "Fidyah"]],
            "template_id": 1,
            "entity_a": "Kaffarah",
            "entity_b": "Fidyah",
            "concept_hook": "Ek kasdi ghalti ka Kaffara hai... jabke doosra majburi ka muawwaza!",
            "mechanism_a": "jaan boojh kar roza todne ya qasam todne ki saza hai",
            "mechanism_b": "bimaari ya shdeed majburi mein roza na rakhne ka muawwaza hai",
            "punchline": "Kaffarah kasdi ghalti ki saza hai, jabke Fidyah majburi ka badla."
        },
        {
            "id": "farq_fk_opt_15",
            "title": "Suhoor vs Iftar: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Suhoor", "Iftar"]],
            "template_id": 1,
            "entity_a": "Suhoor",
            "entity_b": "Iftar",
            "concept_hook": "Roze ke dono siraay kitne mubaarak hain... lekin kis mein barkat zyada hai?",
            "mechanism_a": "subah saadiq se pehle roza shuru karne ka barkat wala khana hai",
            "mechanism_b": "guroob-e-aftab ke waqt roza kholne ka khushgawar lamha hai",
            "punchline": "Suhoor roze ki barkat aur tayyari hai, jabke Iftar ibadat ka in'aam."
        },
        {
            "id": "farq_fk_opt_16",
            "title": "Wudu vs Ghusl: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Wudu", "Ghusl"]],
            "template_id": 1,
            "entity_a": "Wudu",
            "entity_b": "Ghusl",
            "concept_hook": "Ek rozmarra namaz ki tahaarat hai... lekin doosre ke bina namaz kyun nahi hoti?",
            "mechanism_a": "munh, haath, sar aur paaon dhone ki choti tahaarat hai",
            "mechanism_b": "poore badan ko nahla kar haasil hone wali badi tahaarat hai",
            "punchline": "Wudu aam tahaarat hai, jabke Ghusl mukammal paakizgi."
        },
        {
            "id": "farq_fk_opt_17",
            "title": "Muhajir vs Ansar: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Muhajir", "Ansar"]],
            "template_id": 1,
            "entity_a": "Muhajir",
            "entity_b": "Ansar",
            "concept_hook": "Ek ne Makkah se sab kuch chhod kar hijrat ki... lekin doosre ne kya diya?",
            "mechanism_a": "Makkah se Madina Hijrat karne wale Sahaba hain jinhone apna ghar bar qurban kiya",
            "mechanism_b": "Madina ke muqami Sahaba hain jinhone hijrat karne walon ko apna adha maal diya",
            "punchline": "Muhajir qurbani dene wale hain, jabke Ansar madad karne wale."
        },
        {
            "id": "farq_fk_opt_18",
            "title": "Riya vs Ikhlas: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Riya", "Ikhlas"]],
            "template_id": 1,
            "entity_a": "Riya",
            "entity_b": "Ikhlas",
            "concept_hook": "Ek ibadat ko zaya kar deta hai... jabke doosra azeem sawab lata hai!",
            "mechanism_a": "dikhaway ke liye ibadat karna hai jo aamaal ko zaya kar deta hai",
            "mechanism_b": "sirf Allah ki raza ke liye amal karna hai jo ibadat ki rooh hai",
            "punchline": "Riya dikhaway ki deemak hai, jabke Ikhlas ibadat ki rooh."
        },
        {
            "id": "farq_fk_opt_19",
            "title": "Tawakkul vs Sabr: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Tawakkul", "Sabr"]],
            "template_id": 1,
            "entity_a": "Tawakkul",
            "entity_b": "Sabr",
            "concept_hook": "Mushkil waqt mein momin ke do sabse bare hathyar konsay hain?",
            "mechanism_a": "asbaab ikhtiyar karke natija Allah par chhod dene ka yaqeen hai",
            "mechanism_b": "aazmaish par dil ko qaaboo mein rakhna aur aah-o-pukaar na karna hai",
            "punchline": "Tawakkul Allah par bharosa hai, jabke Sabr aazmaish par saabat-qadmi."
        },
        {
            "id": "farq_fk_opt_20",
            "title": "Surah vs Ayat: Farq Kya Hai?",
            "type": "deepdive",
            "fandom": "Islamic",
            "pairs": [["Surah", "Ayat"]],
            "template_id": 1,
            "entity_a": "Surah",
            "entity_b": "Ayat",
            "concept_hook": "Quran Majeed ki bunyadi tarseem aur hifazat ka farq kya hai?",
            "mechanism_a": "Quran Majeed ka ek pura baab ya chapter hai jise bismillah se shuru kiya jata hai",
            "mechanism_b": "Quran Majeed ke baab ke andar ki ek nishani ya single sentence hai",
            "punchline": "Surah Quran ka pura chapter hai, jabke Ayat uski ek nishani."
        }
    ]

    @classmethod
    def get_all_opportunities(cls) -> List[Dict[str, Any]]:
        """Returns pre-curated Islamic concept opportunities for Farq Kya channel."""
        return cls.OPPORTUNITIES
