"""Writing the review in the reader's language.

Three deliberate limits, because a legal product that overreaches on language
does real harm:

1. **Legal terms stay in English.** Statute names, section numbers and case
   citations are reproduced exactly as they appear in the reference pack,
   whatever language the surrounding sentence is in. Legal terminology in the
   South African indigenous languages is not standardised, an invented
   translation of a section heading is indistinguishable from a real one to the
   reader, and a lawyer picking the matter up later needs the English handle.

2. **English is authoritative, and the document says so.** Every translated
   review carries a line to that effect. This is not a disclaimer for its own
   sake: the analysis is produced in English and translated, so if the two ever
   disagree the English is the one that was actually reasoned about.

3. **Unreviewed translations admit it.** Each language carries a `reviewed`
   flag, in the same spirit as the confidence levels in za_law.py. Everything
   below was written without a first-language speaker checking it, so the flag
   is False and the reader is told. Flip it per language once someone qualified
   has been through the strings, and the notice disappears.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Language:
    code: str
    english_name: str
    native_name: str
    # Tesseract language pack, for OCR of documents written in this language.
    ocr_code: str = "eng"
    # False until a first-language speaker has checked the strings below.
    reviewed: bool = False
    prompt: str = ""
    strings: dict[str, str] = field(default_factory=dict)
    bands: dict[str, tuple[str, str]] = field(default_factory=dict)

    @property
    def is_english(self) -> bool:
        return self.code == "en"


_EN_STRINGS = {
    "document_review": "Document review",
    "prepared": "prepared",
    "reference": "reference",
    "footer": "Automated review. Informational only, not legal advice.",
    "page": "Page",
    "attached": "Your review of {documents} is attached to this email as a PDF.",
    "subject": "Your Legal-Eye review of {documents}",
    "subject_banded": "Your Legal-Eye review ({band} risk): {documents}",
    "attachment": "Attachment",
    "contains": "Contains",
    "contains_value": ("Priority findings, red flags, obligations, a risk table "
                       "with severities, and recommended actions."),
    "not_legal_advice": "Not legal advice.",
    "risk_suffix": "risk",
    "authoritative": "",
    "unreviewed": "",
}

_EN_BANDS = {
    "Critical": ("Critical",
                 "Irreversible loss is likely if you proceed before verifying "
                 "independently. Treat every deadline in the document as noise."),
    "High": ("High",
             "Material loss or no enforceable remedy. Resolve the flagged items "
             "before signing or paying."),
    "Elevated": ("Elevated",
                 "Real gaps that could become expensive. Worth a proper read "
                 "and some negotiation."),
    "Moderate": ("Moderate",
                 "Ordinary commercial risk with some loose ends. Tidy them up "
                 "before execution."),
    "Low": ("Low", "Nothing serious surfaced. Skim the findings and proceed."),
}


# --------------------------------------------------------------------------
# The instruction that actually does the work. The chrome below is translated
# by hand; the review body is written by the model under this addendum.
# --------------------------------------------------------------------------
def _prompt(english_name: str, native_name: str) -> str:
    return f"""

=== LANGUAGE: {english_name} ===

Write the entire review in {native_name} ({english_name}). Every heading, every
bullet, every sentence of explanation.

These stay in English, verbatim, never translated:
- Act names and their numbers, exactly as the reference pack gives them
  ("Consumer Protection Act 68 of 2008", not a translation of it)
- Section and regulation references ("s 43(3)", "reg 44")
- Case names and citations
- Party names, company names and figures as they appear in the document

Write the explanation of each of those in {native_name}. So: name the provision
in English, then say what it means for this reader in {native_name}, in the same
sentence.

Where {native_name} has no settled term for a legal concept, use the English
term and explain it in {native_name} rather than inventing a translation. A
reader who sees an unfamiliar coined word cannot look it up, and a lawyer
reading over their shoulder will not recognise it.

Keep the structure, the headings' order, the severity words in the risk table
(Critical, High, Medium, Low) and the rating format exactly as specified. Only
the prose changes language.
"""


LANGUAGES: dict[str, Language] = {
    "en": Language(
        code="en", english_name="English", native_name="English",
        ocr_code="eng", reviewed=True, prompt="",
        strings=_EN_STRINGS, bands=_EN_BANDS,
    ),

    # Afrikaans has a settled legal vocabulary: statutes were published in it
    # for decades and the law reports are full of it. Of the three, this is the
    # one where a machine translation is least likely to mislead.
    "af": Language(
        code="af", english_name="Afrikaans", native_name="Afrikaans",
        ocr_code="afr", reviewed=False,
        prompt=_prompt("Afrikaans", "Afrikaans"),
        strings={
            **_EN_STRINGS,
            "document_review": "Dokumentoorsig",
            "prepared": "opgestel",
            "reference": "verwysing",
            "footer": "Outomatiese oorsig. Slegs ter inligting, nie regsadvies nie.",
            "page": "Bladsy",
            "attached": "Jou oorsig van {documents} is as 'n PDF by hierdie e-pos aangeheg.",
            "subject": "Jou Legal-Eye oorsig van {documents}",
            "subject_banded": "Jou Legal-Eye oorsig ({band} risiko): {documents}",
            "attachment": "Aanhegsel",
            "contains": "Bevat",
            "contains_value": ("Prioriteitsbevindings, rooi vlae, verpligtinge, 'n "
                               "risikotabel met erns, en aanbevole stappe."),
            "not_legal_advice": "Nie regsadvies nie.",
            "risk_suffix": "risiko",
            "authoritative": ("Hierdie oorsig is in Engels opgestel en daarna vertaal. "
                              "Waar die twee verskil, geld die Engelse weergawe."),
            "unreviewed": ("Hierdie Afrikaanse vertaling is nog nie deur 'n "
                           "eerstetaalspreker nagegaan nie."),
        },
        bands={
            "Critical": ("Kritiek",
                         "Onherstelbare verlies is waarskynlik as jy voortgaan "
                         "voordat jy onafhanklik verifieer het. Moenie op enige "
                         "sperdatum in die dokument staatmaak nie."),
            "High": ("Hoog",
                     "Wesenlike verlies of geen afdwingbare remedie nie. Los die "
                     "gemerkte items op voordat jy teken of betaal."),
            "Elevated": ("Verhoog",
                         "Werklike gapings wat duur kan word. Dit verdien 'n "
                         "behoorlike deurlees en onderhandeling."),
            "Moderate": ("Matig",
                         "Gewone kommersiële risiko met 'n paar los drade. Maak "
                         "dit reg voor ondertekening."),
            "Low": ("Laag",
                    "Niks ernstigs het na vore gekom nie. Lees die bevindings "
                    "deur en gaan voort."),
        },
    ),

    "zu": Language(
        code="zu", english_name="isiZulu", native_name="isiZulu",
        ocr_code="eng", reviewed=False,
        prompt=_prompt("isiZulu", "isiZulu"),
        strings={
            **_EN_STRINGS,
            "document_review": "Ukubuyekezwa kwedokhumenti",
            "prepared": "kulungiswe",
            "reference": "inkomba",
            "footer": ("Ukubuyekezwa okwenziwe ngekhompyutha. Ngokwazisa kuphela, "
                       "akulona iseluleko sezomthetho."),
            "page": "Ikhasi",
            "attached": ("Ukubuyekezwa kwakho kwe-{documents} kunamathiselwe "
                         "kule imeyili njenge-PDF."),
            "subject": "Ukubuyekezwa kwakho kwe-Legal-Eye kwe-{documents}",
            "subject_banded": ("Ukubuyekezwa kwakho kwe-Legal-Eye (ubungozi "
                               "obu-{band}): {documents}"),
            "attachment": "Okunamathiselwe",
            "contains": "Kuqukethe",
            "contains_value": ("Okutholakele okubalulekile, izimpawu zengozi, "
                               "izibopho, ithebula lobungozi, nezinyathelo "
                               "ezinconyiwe."),
            "not_legal_advice": "Akulona iseluleko sezomthetho.",
            "risk_suffix": "ubungozi",
            "authoritative": ("Lokhu kubuyekezwa kwenziwe ngesiNgisi kwabe "
                              "sekuhunyushwa. Uma kunomehluko, kusebenza "
                              "inguqulo yesiNgisi."),
            "unreviewed": ("Le nguqulo yesiZulu ayikahlolwa umuntu okhuluma "
                           "isiZulu njengolimi lwakhe lwebele."),
        },
        bands={
            "Critical": ("Kubucayi",
                         "Ungalahlekelwa ngendlela engenakulungiseka uma "
                         "uqhubeka ungakaqinisekisi ngokuzimele. Ungathembi "
                         "noma yimuphi umnqamulajuqu okule dokhumenti."),
            "High": ("Buphezulu",
                     "Ukulahlekelwa okukhulu noma awukho umthetho "
                     "ongakusiza. Xazulula izinto eziphawuliwe ngaphambi "
                     "kokusayina noma ukukhokha."),
            "Elevated": ("Bukhulisiwe",
                         "Kunezikhala ezingabiza imali eningi. Kufanele "
                         "uyifunde kahle futhi uxoxisane."),
            "Moderate": ("Bulinganiselwe",
                         "Ubungozi obujwayelekile bebhizinisi nezinto "
                         "ezingaphelele. Zilungise ngaphambi kokusayina."),
            "Low": ("Buphansi",
                    "Akukho okubi okutholakele. Bheka okutholakele bese "
                    "uqhubeka."),
        },
    ),

    "xh": Language(
        code="xh", english_name="isiXhosa", native_name="isiXhosa",
        ocr_code="eng", reviewed=False,
        prompt=_prompt("isiXhosa", "isiXhosa"),
        strings={
            **_EN_STRINGS,
            "document_review": "Uphononongo lwexwebhu",
            "prepared": "lulungiselelwe",
            "reference": "isalathiso",
            "footer": ("Uphononongo olwenziwe ngekhompyutha. Lwazisa kuphela, "
                       "asilulo icebiso lomthetho."),
            "page": "Iphepha",
            "attached": ("Uphononongo lwakho lwe-{documents} luqhotyoshelwe "
                         "kule imeyile njenge-PDF."),
            "subject": "Uphononongo lwakho lwe-Legal-Eye lwe-{documents}",
            "subject_banded": ("Uphononongo lwakho lwe-Legal-Eye (umngcipheko "
                               "o-{band}): {documents}"),
            "attachment": "Okuqhotyoshelweyo",
            "contains": "Iqulethe",
            "contains_value": ("Okufunyanisiweyo okubalulekileyo, iimpawu "
                               "zomngcipheko, izibophelelo, itheyibhile "
                               "yomngcipheko, namanyathelo acetyisiweyo."),
            "not_legal_advice": "Asilulo icebiso lomthetho.",
            "risk_suffix": "umngcipheko",
            "authoritative": ("Olu phononongo lwenziwe ngesiNgesi lwaza "
                              "lwaguqulelwa. Ukuba kukho umahluko, kusebenza "
                              "inguqulelo yesiNgesi."),
            "unreviewed": ("Le nguqulelo yesiXhosa ayikahlolwa ngumntu othetha "
                           "isiXhosa njengolwimi lwakhe lwenkobe."),
        },
        bands={
            "Critical": ("Ibucayi",
                         "Unokulahlekelwa ngendlela engenakulungiseka ukuba "
                         "uyaqhubeka ungaqinisekisanga ngokuzimeleyo. Musa "
                         "ukuthembela nakuwuphi na umhla osexwebheni."),
            "High": ("Uphezulu",
                     "Ilahleko enkulu okanye akukho sisombululo somthetho. "
                     "Sombulula izinto ezenzelwe uphawu phambi kokutyikitya "
                     "okanye ukuhlawula."),
            "Elevated": ("Unyusiwe",
                         "Kukho izikhewu ezinokubiza imali eninzi. Kufanele "
                         "ulufunde kakuhle uze uthethathethane."),
            "Moderate": ("Uphakathi",
                         "Umngcipheko oqhelekileyo weshishini kunye nezinto "
                         "ezingagqitywanga. Zilungise phambi kokutyikitya."),
            "Low": ("Usezantsi",
                    "Akukho nto imbi ifunyenweyo. Jonga okufunyanisiweyo uze "
                    "uqhubeke."),
        },
    ),
}

DEFAULT = LANGUAGES["en"]


def get(code: str | None) -> Language:
    """Look up a language, falling back to English rather than raising.

    A review that renders in the wrong language is a disappointment. One that
    fails to render is a lost review, so an unknown code degrades instead.
    """
    if not code:
        return DEFAULT
    return LANGUAGES.get(code.strip().lower(), DEFAULT)


def choices() -> list[tuple[str, str]]:
    """(code, label) pairs for a selector, English first."""
    return [(code, language.native_name) for code, language in LANGUAGES.items()]


def ocr_languages() -> str:
    """The Tesseract language string covering every language we accept.

    Tesseract takes several at once, joined by '+', and will pick per block.
    Passing them all costs a little speed and buys correct recognition of
    Afrikaans diacritics, which otherwise come through as noise the analysis
    then treats as real text.
    """
    codes = {language.ocr_code for language in LANGUAGES.values()}
    return "+".join(sorted(codes))


def notices(language: Language) -> list[str]:
    """The lines a translated review must carry, in reading order."""
    if language.is_english:
        return []
    lines = [language.strings.get("authoritative", "")]
    if not language.reviewed:
        lines.append(language.strings.get("unreviewed", ""))
    return [line for line in lines if line]
