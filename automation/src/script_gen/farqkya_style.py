"""
Style rule pack and prompt builder for the "Farq Kya" channel (Roman Urdu).

This module owns *only* farqkya. It shares no rules, phrases or examples with
dontmix_style.py — the two packs are separate on purpose so tuning the Urdu
cadence can never leak into the English channel.

Audit of the 5 farqkya scripts in the tracker found the same sentence machine
running underneath all of them:
  - 5/5 opened with the identical formula "Ye hai X aur ye hai Y, aakhir isme
    farq kya hai?"
  - 5/5 signed off with the identical "Mazeed videos ke liye follow karein."
  - `jabke` appeared in 5/5 scripts (6 uses) as the contrast pivot, which is the
    written Urdu equivalent of English "whereas" and the single clearest tell of
    English-order Urdu.
  - 3/5 ran the frame "Aksar log ... samajhte hain, lekin aisa nahi hai", a
    word-for-word calque of "most people think ... but that is not the case".
  - Payoffs restated the mechanism in shorter words ("Farz-e-Ain shakhsi
    zimmedari hai, jabke Farz-e-Kifayah ijtimai") instead of landing anything.

The rules below target those findings specifically.
"""

from typing import Dict, List, Optional, Sequence

from .slop_rules import HookArchetype, SlopRule, StyleRules

# Roman Urdu function words. Used for content-overlap scoring, so that a payoff
# echoing the mechanism is caught on meaning-carrying words only.
STOPWORDS = frozenset("""
ye yeh ya wo woh is us in ka ki ke ko se par mein men aur ek hai hain tha thi the
hota hoti hote hona ho jata jati jate karna karta karti karte kiya ki kar raha
rahi rahe se ne bhi hi to na nahi nahin magar lekin agar jab tab phir bas yaani
yani ab kya kyun kaise kahan kaun kis jo jis jin sab har koi kuch kuchh apne apni
apna mera meri hum aap unka uska iska liye taur wala wali wale se sath saath
""".split())


# ---------------------------------------------------------------------------
# Hook archetypes, in natural spoken Urdu shapes.
# ---------------------------------------------------------------------------

HOOKS: List[HookArchetype] = [
    HookArchetype(
        id="classic_labels",
        name="Dono cheezein saamne rakh dein",
        detect=r"ye hai [^.?!]{1,45}\s+aur ye hai [^.?!]{1,45}[,.?]",
        brief=("Channel ka purana formula. Dono cheezon ka naam le kar seedha "
               "sawal. Sirf kabhi kabhi istemaal karein, lagataar do videos mein "
               "nahi."),
        example="Ye hai Nabi aur ye hai Rasool, aakhir isme farq kya hai?",
    ),
    HookArchetype(
        id="ghalati_pehle",
        name="Pehle ghalati, phir dono naam",
        detect=(r"(?:zyada ?tar log|aksar log|bohat se log|bahut se log|"
                r"log aam taur par|hum sab|log)\s+[^.?!]{0,95}"
                r"(?:samajhte|kehte|sochte|maante|samajh lete)\s+hain[^.?!]{0,20}[.?!]"),
        brief=("Pehli line mein wo ghalti bataiye jo sunne wala khud karta hai, "
               "jaise wo baat sahi ho. Doosri line mein dono cheezon ka naam."),
        example="Zyada tar log Sadaqah ko hi Zakat samajh lete hain.",
    ),
    HookArchetype(
        id="seedha_farq",
        name="Sab se tez farq pehli line mein",
        detect=(r"(?:ek|pehla|pehli|aik)\b[^.?!]{0,75}[.?!]\s*"
                r"(?:doosra|doosri|dusra|dusri|dooja)\b"),
        brief=("Sab se bara farq pehle bol dein, naam baad mein. Do chhoti "
               "lines: 'Ek ... . Doosra ... .' Phir dono ka naam."),
        example="Ek saal mein sirf ek baar. Doosra saal bhar kabhi bhi. Hajj aur Umrah.",
    ),
    HookArchetype(
        id="sawal_seedha",
        name="Seedha sawal sunne wale se",
        detect=(r"(?:agar (?:koi|aap|aaj)|kabhi socha|zara sochiye|batayein)[^?]{0,115}\?"
                r"|[^.?!]{0,70}?\bfarq kya\b[^.?!]{0,40}\?"),
        brief=("Sunne wale se seedha sawal karein jis ka jawab usay khud nahi "
               "aata. Sawal ke foran baad dono cheezon ka naam."),
        example="Agar koi aap se poochhe ke Shirk aur Bidah mein farq kya hai, aap kya kahenge?",
    ),
    HookArchetype(
        id="ek_lafz",
        name="Sirf ek baat sab kuch badal deti hai",
        # A short lead-in is allowed before the promise ("In dono mein sirf ek
        # shart ka farq hai") — the old anchored regex rejected the archetype's
        # own example, so compliant scripts were logged as free_open.
        detect=(r"[^.?!]{0,60}?(?:sirf ek|bas ek|ek hi|sirf itna)\s+"
                r"(?:lafz|baat|cheez|shart|farq|nuqta|fasla)[^.?!]{0,95}[.?!]"),
        brief=("Waada karein ke farq sirf ek chhoti si baat ka hai, phir wo baat "
               "aadhi video se pehle khol dein."),
        example="In dono mein sirf ek shart ka farq hai, magar wahi shart sab kuch badal deti hai.",
    ),
    HookArchetype(
        id="roz_marra",
        name="Roz sunne wale alfaz",
        detect=(r"(?:ye dono lafz|ye lafz|ye dono naam|roz|rozana|har roz)"
                r"\s+[^.?!]{0,95}[.?!]"),
        brief=("Bataiye ke ye dono alfaz roz sunai dete hain aur roz hi ghalat "
               "jagah bole jaate hain. Phir dono ka naam."),
        example="Ye dono lafz roz sunai dete hain, aur roz hi ek doosre ki jagah bole jaate hain.",
    ),
    # Loose fallback, kept last so specific shapes match first.
    HookArchetype(
        id="free_open",
        name="Azad shuruaat",
        detect=r"[^.?!]{5,95}[.?!]",
        brief=("Koi bhi shuruaat jo bara sa jhatka de, 12 alfaz se kam ho, aur "
               "doosri line tak dono cheezon ka naam aa jaye. Koi salaam, koi "
               "bhoomika nahi."),
        example="Dono ka maqsad ek hai, magar hukum ek nahi.",
    ),
]


# ---------------------------------------------------------------------------
# Hard bans.
# ---------------------------------------------------------------------------

BANNED: List[SlopRule] = [
    SlopRule("banned.preamble",
             r"\b(?:aaj ki video mein|is video mein hum|is video mein aap|"
             r"assalam ?o ?alaikum|salam doston|welcome back|doston|"
             r"chaliye shuru karein|aayein dekhte hain|aayein samajhte hain|"
             r"aaj hum baat karenge)\b",
             "video-intro bhoomika", "error",
             hint="Short mein intro ki jagah nahi. Seedha baat shuru karein."),
    SlopRule("banned.calque_frame",
             r"lekin aisa nahi hai|lekin aisa nahin hai|magar aisa nahi hai|"
             r"lekin inme bada farq hai|lekin haqeeqat ye hai ke",
             "angrezi se seedha tarjuma kiya hua frame", "error",
             hint="Ye 'but that is not the case' ka lafzi tarjuma hai. Iski jagah "
                  "'asal baat kuch aur hai', 'haqeeqat is se alag hai', ya seedha "
                  "durusti bol dein."),
    SlopRule("banned.summary_payoff",
             r"yahi (?:bunyadi )?farq hai|inme yahi farq hai|"
             r"khulasa ye hai ke|doosre alfaz mein|mukhtasar ye ke",
             "payoff ki jagah khulasa", "error",
             hint="Aakhri line nayi baat le kar aaye, mechanism ko chhota kar ke "
                  "dohrana payoff nahi hai."),
    SlopRule("banned.written_register",
             r"\b(?:mazeed bar aan|bil aakhir|ikhtitami taur par|"
             r"qabil e zikr hai|ye baat qabil e ghaur hai|ba har haal)\b",
             "likhne wali kitabi zubaan", "error",
             hint="Ye alfaz koi bolta nahi. Bolne wali Urdu likhein."),
    SlopRule("banned.english_filler",
             r"\b(?:basically|actually|obviously|literally|so basically|"
             r"the difference is|in short|first of all)\b",
             "angrezi filler", "error",
             hint="Roman Urdu script mein angrezi filler alag se sunai deta hai."),
    SlopRule("banned.digits",
             r"\d|%",
             "hindsa ya percent ka nishan", "error",
             hint="TTS ke liye har adad alfaz mein likhein: 'dhai percent' na ke "
                  "'2.5%', 'paanch waqt' na ke '5 waqt'."),
    SlopRule("banned.name_stutter",
             r"\b([A-Z][\w'-]+)\s+(?:The\s+)?\1\b",
             "ek hi naam do baar", "error",
             hint="Template bug ka nateeja. Line dobara parh kar bhejein."),
]


# ---------------------------------------------------------------------------
# Tics: bolne mein ek dafa theek, us se zyada machine lagti hai.
# ---------------------------------------------------------------------------

TICS: List[SlopRule] = [
    SlopRule("tic.jabke", r"\bjabke\b|\bjab ke\b", "'jabke' se contrast",
             "error", max_allowed=1,
             hint="Audit ki 5 mein se 5 scripts mein tha. Bolne mein contrast "
                  "poore stop se hota hai: 'Zakat farz hai. Sadaqah marzi.' Ya "
                  "'magar' se."),
    SlopRule("tic.aksar_log", r"\baksar log\b|\bzyada ?tar log\b",
             "'aksar log' frame", "error", max_allowed=1,
             hint="Agar hook mein ye kaam ho gaya to body se hata dein."),
    SlopRule("tic.samajhte_hain", r"\bsamajhte hain\b|\bsamajh lete hain\b",
             "'samajhte hain' frame", "warn", max_allowed=1),
    SlopRule("tic.passive", r"\b(?:kiya|ki|kiye|diya|di) ja(?:ta|ti|te) hai\b|"
             r"\bada ki?ya jata hai\b",
             "kitabi passive ('ada kiya jata hai')", "warn", max_allowed=1,
             hint="Bolne mein log 'karte hain' ya 'hota hai' kehte hain."),
    SlopRule("tic.farq_ye_hai", r"\bfarq ye hai ke\b|\bfarq yeh hai ke\b",
             "'farq ye hai ke' bridge", "warn", max_allowed=1),
    SlopRule("tic.yaani", r"\byaani\b|\byani\b", "'yaani' ki takrar",
             "warn", max_allowed=2),
    SlopRule("tic.list_run", r",\s*\w+,\s*\w+,\s*(?:aur|ya)\s+",
             "teen cheezon ki list", "warn", max_allowed=0,
             hint="List bolne ki raftaar tor deti hai. Sirf ek cheez chunein."),
]


# Bolne wali Urdu ke discourse markers. Script mein kam az kam ek hona chahiye,
# warna jumle likhe hue lagte hain.
NATURAL_MARKERS: List[str] = [
    r"\bto\b", r"\bphir\b", r"\bbas\b", r"\bmagar\b", r"\bab\b",
    r"\basal mein\b", r"\bdekhiye\b", r"\bsuniye\b", r"\bzara\b",
    r"\byaani\b", r"\byani\b", r"\bhi\b",
]

# Urdu jumla tqreeban hamesha fael par khatam hota hai. Agar zyada jumle noun par
# khatam hon to cadence angrezi ki hai. Validator isay naapta hai.
VERB_FINAL_TOKENS = frozenset("""
hai hain tha thi the hoga hogi honge hota hoti hote ho hua hui hue
karta karti karte karein karen karo kariye kar liya diya di dein len lein
jata jati jate gaya gayi gaye raha rahi rahe sakta sakti sakte
chahiye samjhein dekhein padhein sunein banta banti milta milti
nahi nahin kahenge kahein poochhein batayein bataiye laga lagi lagta lagti
chahe chahein kare karen jaye jaaye mile mil sake sakein rahega rahegi
bane banein bola boli bole suna suni parha parhi dete deti dena deti
""".split())


CTA_BANK: List[str] = [
    "Mazeed videos ke liye follow karein.",
    "Agar baat samajh aa gayi to follow kar lein.",
    "Aisi hi baaton ke liye follow karein.",
    "Comment mein batayein, agla farq kis cheez ka chahiye.",
    "Ye baat aage pohanchayein, kisi ko fayda ho jayega.",
    "Kya aapko pehle se pata tha? Comment karein.",
    "Follow karein, agla farq is se bara hai.",
]


FARQKYA_RULES = StyleRules(
    channel="farqkya",
    banned=BANNED,
    tics=TICS,
    hooks=HOOKS,
    cta_bank=CTA_BANK,
    stopwords=STOPWORDS,
    # Bolne wali Urdu ke jumle angrezi se chhote hote hain.
    min_sentence_stdev=2.1,
    max_mean_sentence_words=14.0,
    max_sentence_words=26,   # Urdu spends more words per idea than English
    reuse_window=6,
    max_body_ngram_overlap=0.28,
    max_payoff_echo=0.35,   # 3-gram overlap between payoff and setup
)


# ---------------------------------------------------------------------------
# Few-shot golds, written in spoken Roman Urdu. Four different hook archetypes,
# four different payoff shapes, none of them ending on a restatement.
# ---------------------------------------------------------------------------

GOLD_EXAMPLES: List[Dict[str, str]] = [
    {
        "hook": "classic_labels",
        "why": "Payoff ek mantiqi rishta khol deta hai jo body mein nahi tha. 70 alfaz.",
        "script": (
            "Ye hai Nabi aur ye hai Rasool, aakhir isme farq kya hai? Dono Allah "
            "Ta'ala ke bheje hue hain, dono par wahi aati hai. Farq wahi mein "
            "nahi, zimmedari mein hai. Nabi usi shariat ko aage badhate hain jo "
            "pehle se maujood hai. Rasool nayi kitab aur naya hukum le kar aate "
            "hain. Isi liye har Rasool Nabi hota hai. Magar har Nabi Rasool nahi "
            "hota. Agar baat samajh aa gayi to follow kar lein."
        ),
    },
    {
        "hook": "ghalati_pehle",
        "why": "Payoff nateeja deta hai, tareef nahi dohrata. 'jabke' ek baar bhi nahi.",
        "script": (
            "Zyada tar log Sadaqah ko hi Zakat samajh lete hain. Dono dena achha "
            "hai, magar hukum ek nahi. Zakat un par farz hai jinke paas nisab se "
            "zyada maal saal bhar rehta hai, aur us ka hisaab muqarrar hai, dhai "
            "percent. Sadaqah ka koi hisaab nahi, koi waqt nahi, jitna dil kare. "
            "Isi liye Sadaqah na dene par koi pakad nahi. Zakat na dene par pakad "
            "hai. Ye baat aage pohanchayein, kisi ko fayda ho jayega."
        ),
    },
    {
        "hook": "seedha_farq",
        "why": "Naam teesri line mein aata hai. Payoff waqt ka nuqsaan dikhata hai.",
        "script": (
            "Ek saal mein sirf ek baar. Doosra saal bhar kabhi bhi. Baat Hajj aur "
            "Umrah ki ho rahi hai. Hajj Islam ka rukn hai, har sahib-e-ista'at par "
            "zindagi mein ek baar farz hai. Aur wo bhi sirf Zil Hajj ke chand khaas "
            "dinon mein hota hai. Umrah nafl hai, jab dil chahe, jitni baar chahe. "
            "Isi liye Hajj chhoot jaye to poora saal intezaar karna padta hai. "
            "Umrah kal bhi ho sakta hai. Mazeed videos ke liye follow karein."
        ),
    },
    {
        "hook": "ek_lafz",
        "why": "66 alfaz. Payoff amal ka farq bataata hai, tareef nahi.",
        "script": (
            "In dono mein sirf ek shart ka farq hai. Istighfar zubaan se maafi "
            "maangna hai, bas jitni baar chahein. Tawbah us se aage ki cheez hai, "
            "gunah chhorne ka pakka irada. Isi liye aadmi saara din Istighfar "
            "karta reh sakta hai aur wahi gunah bhi karta rahe. Tawbah ke baad wo "
            "raasta band ho jata hai. Kya aapko pehle se pata tha? Comment karein."
        ),
    },
]


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def assign_hooks(count: int, recent_hook_ids: Sequence[str]) -> List[str]:
    """One archetype per script, skipping whatever the last few scripts used."""
    recent = list(recent_hook_ids)[-3:]
    pool = [h.id for h in HOOKS if h.id != "free_open"]
    fresh = [h for h in pool if h not in recent] or pool
    plan: List[str] = []
    i = 0
    while len(plan) < count:
        candidate = fresh[i % len(fresh)]
        if candidate in plan and len(plan) < len(fresh):
            i += 1
            continue
        plan.append(candidate)
        i += 1
    return plan


def _hook_briefing(hook_plan: Sequence[str]) -> str:
    lines = []
    for idx, hid in enumerate(hook_plan, 1):
        h = next((x for x in HOOKS if x.id == hid), HOOKS[-1])
        lines.append(
            f"  Script {idx} -> hook archetype `{h.id}` ({h.name})\n"
            f"      {h.brief}\n"
            f"      Shape reference (in alfaz ko dobara istemaal NA karein): {h.example}"
        )
    return "\n".join(lines)


def _banned_briefing() -> str:
    lines = []
    for rule in BANNED:
        lines.append(f"  - NEVER: {rule.label}. {rule.hint}")
    for rule in TICS:
        cap = "bilkul nahi" if rule.max_allowed == 0 else f"script mein max {rule.max_allowed} baar"
        lines.append(f"  - {rule.label}: {cap}. {rule.hint}")
    return "\n".join(lines)


def _gold_briefing() -> str:
    out = []
    for i, g in enumerate(GOLD_EXAMPLES, 1):
        out.append(f"GOLD {i} (hook: {g['hook']}) — kyun chalta hai: {g['why']}\n\"{g['script']}\"")
    return "\n\n".join(out)


VOICE_BRIEF = """\
You write for the Roman Urdu YouTube Shorts channel "Farq Kya". You are one
person explaining an Islamic distinction to a friend who asked, in the ordinary
spoken Urdu of Karachi or Lahore. You are not reading a fatwa and you are not
translating an English script.

Everything you write is spoken out loud by a voice model reading Roman Urdu, so
write only speakable words.
"""

CADENCE_BRIEF = """\
### URDU CADENCE — this is what the old generator got wrong

The old scripts were English sentences wearing Urdu words. Every tell below was
measured in the audited output. Avoid all of them.

1. FAEL AAKHIR MEIN. Urdu sentences end on the verb.
   Angrezi order : "Zakat farz hai maaldar Musalman par."
   Urdu order    : "Maaldar Musalman par Zakat farz hai."
   Har jumla `hai / hain / hota hai / karte hain / nahi` jaise fael par khatam ho.

2. "jabke" SE CONTRAST MAT KAREIN. `jabke` likhi jaane wali Urdu ka "whereas"
   hai. Bolne wala aisa nahi kehta.
   Machine : "Zakat farz hai, jabke Sadaqah nafli khairat hai."
   Natural : "Zakat farz hai. Sadaqah marzi." / "Zakat par pakad hai, Sadaqah par nahi."
   Poora stop, ya `magar`, ya dono jumlon ko ulat dein. Ek script mein `jabke`
   sirf ek baar, aur behtar ye ke ek baar bhi nahi.

3. TARJUME WALE FRAME BAND. "Aksar log ... samajhte hain, lekin aisa nahi hai"
   angrezi ka lafzi tarjuma hai aur audit ki 3 mein se 5 scripts mein tha.
   Iski jagah: "asal baat kuch aur hai", "haqeeqat is se alag hai", ya seedha
   durusti bol dein bina bhoomika ke.

4. BOLNE WALE ZARF ISTEMAAL KAREIN. `to`, `phir`, `bas`, `magar`, `ab`,
   `asal mein`, `isi liye`, `dekhiye`. Kam az kam ek zaroor, warna jumle likhe
   hue lagte hain. Magar inhein bhi takrar na karein.

5. AASAAN LAFZ JAHAN MAUJOOD HAI: `makhsoos` ki jagah `khaas`; `ijtima'i
   zimmedari` ki jagah `sab ki zimmedari`; `ada kiya jata hai` ki jagah
   `karte hain`; `mustaqil` ki jagah `hamesha ka`.

6. DEENI ISTILAHAT WAISE HI RAHENGI: farz, wajib, sunnat, nafl, mustahab,
   shariat, wahi, nisab, rukn, tawheed. Inhein aasaan karne ki koshish na karein.

7. TAZKEER O TANEES DURUST: "Umrah ho sakta hai", "Zakat farz hai", "Namaz ho
   jati hai", "Sadaqah diya jata hai". Ghalat agreement sab se pehle pakri jati hai.

8. CHHOTE JUMLE. Ek jumla bees alfaz se zyada nahi, aur poori script ka ausat
   chaudah se kam. Bolne wali Urdu angrezi se chhoti hoti hai.

9. ADAB: Allah ka zikr ho to "Allah Ta'ala". Nabi ka zikr ho to "Nabi Kareem
   sallallahu alaihi wasallam" poora likhein — "SAW" ko TTS harf ba harf parhta
   hai.

10. Sirf wo farq bataayein jis par ummat ka ittefaq hai. Fiqhi ikhtilaf, kisi
    maslak ki tardeed, ya kisi firqe par tanqeed bilkul nahi.
"""

BEAT_CONTRACT = """\
### BEAT CONTRACT (dhancha, template nahi — alfaz har baar naye)

1. THANDA SHURU, assigned archetype mein. Dono cheezon ka naam doosri line tak
   aa jaye, kyunke video mein dono tasveerein foran dikhti hain.
2. GHALAT-FEHMI EK BAAR TORHEIN, ek jumle mein, aur sirf agar sunne wala waqai
   wo ghalti karta hai. Nakli ghalat-fehmi banane se behtar hai ye beat chhor dein.
3. DONO TARAF KA EK THOS SABAB. Ek check karne laayak baat — waqt, hukum, sharat,
   miqdaar, asal. Naam ko dobara bayan karna sabab nahi hai.
4. AAGE BADHAYEIN. Aakhri hisse mein ek nayi baat aaye jo shuru mein nahi thi aur
   jo farq ko bara kar de. Isi beat ke baghair script lughat lagti hai.
5. LAND KAREIN. Aakhri line akeli bhi caption ban sake. Us mein kam az kam ek
   baat ya lafz aisa ho jo beat 3 mein nahi tha. Agar payoff sirf beat 3 ka
   chhota version hai to wo payoff nahi.
6. SIGN OFF assigned CTA se, us ke baad kuch nahi.

Payoff ke baad us ki tafseel bilkul na karein. Video landing par khatam hoti hai.
"""


def build_generation_prompt(
    count: int,
    target_deepdives: int,
    target_compilations: int,
    hook_plan: Sequence[str],
    cta_plan: Sequence[str],
    excluded_pairs: str,
    fandom: Optional[str] = None,
    recent_openers: Optional[Sequence[str]] = None,
) -> str:
    """Builds the full farqkya generation prompt for one batch."""
    opener_block = ""
    if recent_openers:
        shown = "\n".join(f'  - "{o}"' for o in list(recent_openers)[:8])
        opener_block = (
            "\n### IS CHANNEL PAR PEHLE ISTEMAAL HO CHUKE OPENERS (in ka dhancha "
            "aur pehle chhe alfaz dobara na aayein)\n" + shown + "\n"
        )

    cta_block = "\n".join(f'  Script {i}: "{c}"' for i, c in enumerate(cta_plan, 1))

    return f"""{VOICE_BRIEF}
{CADENCE_BRIEF}
{BEAT_CONTRACT}
### HARD BANS (in mein se koi bhi cheez ho to script phaink di jati hai)
{_banned_briefing()}
  - Em dash, asterisk, teen nuqte, bracket ya parenthesis kahin nahi. Text
    seedha voice model ko jata hai.
  - Kisi cheez ka naam lagataar do baar na likhein.

### LAMBAI
  DEEPDIVE: 55-85 bole jane wale alfaz. Kam taraf rakhein. Saath alfaz ki kasi
  hui script chaurasi alfaz ki bhari script se behtar chalti hai.
  COMPILATION: teen jode, kul 80-100 alfaz, aur har jode ka contrast alag tarah
  se banayein. Teen dafa "A ye hai, jabke B wo hai" — bilkul yahi ghalti thi.

### HOOK ASSIGNMENT (har script ka apna archetype, tabdeeli nahi)
{_hook_briefing(hook_plan)}
{opener_block}
### SIGN-OFF ASSIGNMENT (bilkul yahi line, aakhri jumle ke taur par)
{cta_block}

### GOLD STANDARD (dhancha aur raftaar copy karein, mauzu aur alfaz nahi)

{_gold_briefing()}

### IS BATCH MEIN
Theek {count} scripts likhein: {target_deepdives} deepdive, {target_compilations} compilation.
{f'Sirf is daaere mein rahein: {fandom}.' if fandom else 'Mukhtalif Islamic mauzu chunein: ibadat, aqeedah, akhlaq, seerat, fiqh ki aasaan istilahat.'}
Aise jode chunein jinhein log waqai mila dete hain. Jis jode ko koi confuse nahi
karta, us mein hook hi nahi.

PEHLE HO CHUKE — ye jode na chunein:
{excluded_pairs}

### OUTPUT: strict JSON, koi markdown fence nahi, koi tabsira nahi
{{
  "topics": [
    {{
      "id": "fk_01",
      "title": "Nabi vs Rasool: Farq Kya Hai?",
      "type": "deepdive",
      "fandom": "Islamic",
      "pairs": [["Nabi", "Rasool"]],
      "hook_archetype": "classic_labels",
      "payoff": "landing line, dobara yahan likhein taake check ho sake",
      "script": "poori boli jane wali script, ek paragraph, assigned sign-off par khatam",
      "seo_metadata": {{
        "seo_title": "70 characters se kam",
        "ab_title": "usi video ka doosra angle",
        "thumbnail_text": "24 characters se kam",
        "hashtags": ["#Shorts", "#FarqKya", "#IslamicKnowledge"],
        "description": "do jumle, hashtag ka dher nahi",
        "pinned_comment": "aisa sawal jo sirf poori video dekhne wala samajh sake"
      }}
    }}
  ]
}}"""


def build_repair_prompt(
    script: str,
    title: str,
    issues: Sequence[str],
    required_hook: Optional[str] = None,
    required_cta: Optional[str] = None,
) -> str:
    """Second pass for a farqkya script that failed validation."""
    problems = "\n".join(f"  - {i}" for i in issues)
    hook = next((h for h in HOOKS if h.id == required_hook), None)
    hook_line = (
        f"\nOpener isi archetype mein rahe `{hook.id}`: {hook.brief}\n" if hook else ""
    )
    cta_line = f'\nAakhri jumla bilkul yahi ho: "{required_cta}"\n' if required_cta else ""

    return f"""{VOICE_BRIEF}
{CADENCE_BRIEF}
Farq Kya ki ek script channel ka slop check pass nahi kar saki. Isay dobara
likhein, wahi mauzu aur wahi do cheezein rakhte hue.

MAUZU: {title}

MAUJOODA SCRIPT:
"{script}"

KYA FAIL HUA:
{problems}
{hook_line}{cta_line}
Dobara likhne ke usool:
  - Masle wali lines dobara likhein, content kaat kar check pass na karein.
  - Payoff mein koi nayi baat ho jo mechanism wali lines mein nahi thi.
  - Contrast poore stop se, `jabke` se nahi.
  - Deepdive 55-85 alfaz, compilation 80-100. Lambai poori karne ke liye bharti
    na karein.

Sirf strict JSON wapas karein:
{{"script": "dobara likhi hui script", "payoff": "landing line"}}"""
