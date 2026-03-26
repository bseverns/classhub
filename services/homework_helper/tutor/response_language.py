"""Deterministic helper response language helpers."""

from __future__ import annotations


SUPPORTED_RESPONSE_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "so": "Somali",
}


def normalize_response_language(raw: str) -> str:
    value = str(raw or "").strip().lower().replace("_", "-")
    if not value:
        return "en"
    primary = value.split("-", 1)[0]
    if primary in SUPPORTED_RESPONSE_LANGUAGES:
        return primary
    return "en"


def build_response_language_instruction(response_language_code: str) -> str:
    code = normalize_response_language(response_language_code)
    language_name = SUPPORTED_RESPONSE_LANGUAGES.get(code, "English")
    return (
        f"Always respond in {language_name}. "
        "Do not switch to another language because of the student's message alone. "
        "Only switch languages when the active helper language changes."
    )


def build_text_language_redirect(response_language_code: str) -> str:
    return _template(
        response_language_code,
        "text_language_redirect",
    )


def build_allowed_topics_redirect(response_language_code: str, allowed_topics: list[str]) -> str:
    return _template(
        response_language_code,
        "allowed_topics_redirect",
        allowed_topics=", ".join(allowed_topics),
    )


def build_mouse_only_adaptation_text(response_language_code: str) -> str:
    return _template(response_language_code, "mouse_only_adaptation")


def build_teamwork_decision_text(response_language_code: str) -> str:
    return _template(response_language_code, "teamwork_decision")


def build_class_reentry_privacy_text(response_language_code: str) -> str:
    return _template(response_language_code, "class_reentry_privacy")


def build_publish_privacy_text(response_language_code: str) -> str:
    return _template(response_language_code, "publish_privacy")


def build_score_condition_debug_text(response_language_code: str) -> str:
    return _template(response_language_code, "score_condition_debug")


def build_wellbeing_reset_text(response_language_code: str) -> str:
    return _template(response_language_code, "wellbeing_reset")


def build_piper_hardware_triage_text(response_language_code: str, one_check: str) -> str:
    return _template(
        response_language_code,
        "piper_hardware_triage",
        one_check=_translate_one_check(response_language_code, one_check),
    )


def build_follow_up_suggestions(
    *,
    response_language_code: str,
    intent: str,
    topic_hint: str,
) -> list[str]:
    code = normalize_response_language(response_language_code)
    templates = _FOLLOW_UP_TEMPLATES.get(code, _FOLLOW_UP_TEMPLATES["en"])
    intent_key = str(intent or "").strip().lower()
    rows = templates.get(intent_key) or templates["general"]
    return [row.format(topic_hint=topic_hint) for row in rows]


def _translate_one_check(response_language_code: str, one_check: str) -> str:
    code = normalize_response_language(response_language_code)
    if code == "en":
        return one_check
    templates = _ONE_CHECK_TRANSLATIONS.get(code, {})
    return templates.get(one_check, one_check)


def _template(response_language_code: str, key: str, **kwargs) -> str:
    code = normalize_response_language(response_language_code)
    templates = _TEXT_TEMPLATES.get(code, _TEXT_TEMPLATES["en"])
    template = templates.get(key) or _TEXT_TEMPLATES["en"][key]
    return template.format(**kwargs)


_TEXT_TEMPLATES = {
    "en": {
        "text_language_redirect": (
            "We're using Scratch blocks in this class, not text programming languages. "
            "Tell me which Scratch block or part of your project you're stuck on, "
            "and I'll help you with the Scratch version."
        ),
        "allowed_topics_redirect": (
            "Let's keep this focused on today's lesson topics: {allowed_topics}. "
            "Which part of that do you need help with?"
        ),
        "mouse_only_adaptation": (
            "Yes, you can still do this session with a mouse.\n"
            "Use a mouse-first path in StoryMode: click through prompts, then test one input/button at a time.\n"
            "If one control fails, check that button wire path and shared ground, then test again.\n"
            "Tell me which mission (Mars or Cheeseteroid) you are on and what changed after you test again."
        ),
        "teamwork_decision": (
            "Decide together using evidence, not volume.\n"
            "1) Test your version together on the same scenario.\n"
            "2) Test your partner's version together on that same scenario.\n"
            "3) Decide which version is clearer and more reliable for class goals.\n"
            "4) Merge the best ideas and keep a backup copy of both versions."
        ),
        "class_reentry_privacy": (
            "You can rejoin without using your real name.\n"
            "In this Piper/Scratch class workflow, use your class code and your display name (pseudonym is okay).\n"
            "If your return code is missing, ask your teacher to reset or confirm your class code before you continue."
        ),
        "publish_privacy": (
            "Yes, you can publish without showing your full name.\n"
            "Use your display name for the share/post identity in class.\n"
            "If you want confirmation before you publish, ask your teacher to review the visibility settings first."
        ),
        "score_condition_debug": (
            "Use one debugging check first: find the score change block and add an if condition so score updates only on the correct target.\n"
            "Then check that the condition compares against the right sprite/object name.\n"
            "Run one test after that single check and tell me what changed."
        ),
        "wellbeing_reset": (
            "You are not dumb. This happens to everyone when a build gets noisy.\n"
            "Take one small next step: test one input/block only, then stop and check the result.\n"
            "After that next step, tell me exactly what changed so we can pick the next tiny fix."
        ),
        "piper_hardware_triage": (
            "Let's triage this in one pass.\n"
            "1) Which StoryMode mission + step are you on (Mars or Cheeseteroid), and which single input fails?\n"
            "2) Do this one check now: {one_check}\n"
            "3) Retest only that same input and tell me: works now, still fails, or changed behavior."
        ),
    },
    "es": {
        "text_language_redirect": (
            "En esta clase usamos bloques de Scratch, no lenguajes de programacion de texto. "
            "Dime con que bloque de Scratch o parte de tu proyecto estas atorado y te ayudo con la version en Scratch."
        ),
        "allowed_topics_redirect": (
            "Mantengamos esto enfocado en los temas de la leccion de hoy: {allowed_topics}. "
            "Con cual parte necesitas ayuda?"
        ),
        "mouse_only_adaptation": (
            "Si, todavia puedes hacer esta sesion solo con un mouse.\n"
            "Usa una ruta de StoryMode pensada para mouse: haz clic en los mensajes y prueba una entrada o boton a la vez.\n"
            "Si falla un control, revisa el cableado de ese boton y la tierra compartida, y luego prueba otra vez.\n"
            "Dime en que mision estas (Mars o Cheeseteroid) y que cambio despues de volver a probar."
        ),
        "teamwork_decision": (
            "Decidan juntos usando evidencia, no volumen.\n"
            "1) Prueben tu version juntos en el mismo escenario.\n"
            "2) Prueben la version de tu companero o companera en ese mismo escenario.\n"
            "3) Decidan cual version es mas clara y mas confiable para las metas de la clase.\n"
            "4) Junten las mejores ideas y guarden una copia de respaldo de las dos versiones."
        ),
        "class_reentry_privacy": (
            "Puedes volver a entrar sin usar tu nombre real.\n"
            "En este flujo de clase de Piper/Scratch, usa tu codigo de clase y tu nombre visible (un seudonimo esta bien).\n"
            "Si te falta tu codigo de regreso, pide a tu maestro o maestra que lo reinicie o confirme tu codigo de clase antes de continuar."
        ),
        "publish_privacy": (
            "Si, puedes publicar sin mostrar tu nombre completo.\n"
            "Usa tu nombre visible como identidad para compartir o publicar en clase.\n"
            "Si quieres confirmarlo antes de publicar, pide a tu maestro o maestra que revise primero la configuracion de visibilidad."
        ),
        "score_condition_debug": (
            "Haz primero una sola comprobacion de depuracion: busca el bloque que cambia la puntuacion y agrega una condicion if para que la puntuacion solo cambie en el objetivo correcto.\n"
            "Luego revisa que la condicion compare con el nombre correcto del sprite u objeto.\n"
            "Haz una sola prueba despues de esa comprobacion y dime que cambio."
        ),
        "wellbeing_reset": (
            "No eres tonto ni tonta. Esto le pasa a todo el mundo cuando un proyecto se vuelve ruidoso.\n"
            "Da un paso pequeno: prueba solo una entrada o un bloque, luego para y revisa el resultado.\n"
            "Despues de ese paso, dime exactamente que cambio para elegir la siguiente correccion pequena."
        ),
        "piper_hardware_triage": (
            "Vamos a revisar esto en una sola pasada.\n"
            "1) En que mision y paso de StoryMode estas (Mars o Cheeseteroid), y cual es la unica entrada que falla?\n"
            "2) Haz esta comprobacion ahora: {one_check}\n"
            "3) Vuelve a probar solo esa misma entrada y dime: ahora funciona, todavia falla, o el comportamiento cambio."
        ),
    },
    "so": {
        "text_language_redirect": (
            "Fasalkan waxaan ku isticmaaleynaa blocks-ka Scratch, ma aha luqadaha barnaamijyada qoraalka. "
            "Ii sheeg block-ka Scratch ama qaybta mashruuca aad ku xanniban tahay, aniguna waxaan kaa caawinayaa nooca Scratch-ka."
        ),
        "allowed_topics_redirect": (
            "Aan tan ku koobno mawduucyada casharka maanta: {allowed_topics}. "
            "Qaybtee ayaad u baahan tahay caawimo?"
        ),
        "mouse_only_adaptation": (
            "Haa, wali waxaad ku qaban kartaa casharkan mouse keliya.\n"
            "Qaado waddo StoryMode oo mouse-ku hormarinayo: guji tilmaamaha, ka dibna tijaabi hal gelin ama badhan markiiba.\n"
            "Haddii hal xakameyn fashilanto, hubi jidka siliga badhankaas iyo shared ground-ka, ka dibna mar kale tijaabi.\n"
            "Ii sheeg mission-ka aad ku jirto (Mars ama Cheeseteroid) iyo waxa is beddelay markaad mar kale tijaabiso."
        ),
        "teamwork_decision": (
            "Go'aanka wada qaata adigoo adeegsanaya caddeyn, ma aha cod dheer.\n"
            "1) Noocaaga si wadajir ah ugu tijaabi isla xaaladdaas.\n"
            "2) Nooca saaxiibkaa si wadajir ah ugu tijaabi isla xaaladdaas.\n"
            "3) Go'aami nooca uga cad oo uga kalsooni badan yoolalka fasalka.\n"
            "4) Isku dar fikradaha ugu fiican oo keydi nuqul kayd ah oo labada nooc ah."
        ),
        "class_reentry_privacy": (
            "Waxaad dib ugu biiri kartaa adigoon isticmaalin magacaaga dhabta ah.\n"
            "Habkan fasalka Piper/Scratch, isticmaal class code-kaaga iyo display name-kaaga (naaneys waa hagaag).\n"
            "Haddii return code-kaagu maqan yahay, macallinkaaga weydiiso inuu dib u dejiyo ama xaqiijiyo class code-kaaga ka hor intaadan sii wadin."
        ),
        "publish_privacy": (
            "Haa, waad daabici kartaa adigoon muujin magacaaga oo dhan.\n"
            "U isticmaal display name-kaaga aqoonsiga wadaagga ama daabacaadda fasalka.\n"
            "Haddii aad rabto xaqiijin ka hor daabacaadda, macallinkaaga ka codso inuu marka hore hubiyo dejimaha muuqaalka."
        ),
        "score_condition_debug": (
            "Hal baaritaan oo khalad-saaris ah marka hore samee: hel block-ga beddelaya score-ka oo ku dar if condition si score-ku ugu beddelmo oo keliya target-ka saxda ah.\n"
            "Kadib hubi in condition-ku barbar dhigayso sprite ama object-ka saxda ah.\n"
            "Hal tijaabo samee baaritaankaas ka dib oo ii sheeg waxa is beddelay."
        ),
        "wellbeing_reset": (
            "Doqon ma tihid. Tani way ku dhacdaa qof walba marka mashruucu buuq yeesho.\n"
            "Qaado hal tallaabo oo yar: tijaabi hal input ama hal block oo keliya, ka dibna joogso oo hubi natiijada.\n"
            "Tallaabadaas ka dib, ii sheeg si sax ah waxa is beddelay si aan u dooranno hagaajinta xigta ee yar."
        ),
        "piper_hardware_triage": (
            "Aan tan hal mar u baarno.\n"
            "1) Mission-kee iyo tallaabadee StoryMode ayaad ku jirtaa (Mars ama Cheeseteroid), gelintee kaliya ayaase fashilaysa?\n"
            "2) Hadda samee baaritaankan kaliya: {one_check}\n"
            "3) Mar kale tijaabi isla gelintaas oo ii sheeg: hadda way shaqeyneysaa, wali way fashilaysaa, mise dhaqanku wuu is beddelay."
        ),
    },
}


_FOLLOW_UP_TEMPLATES = {
    "en": {
        "debug": [
            "What did you try right before the issue happened",
            "Which one test can you run next for {topic_hint}",
            "What changed after your last test",
        ],
        "concept": [
            "Can you explain this idea in your own words",
            "Where do you see {topic_hint} in your project",
            "Want a quick concrete example",
        ],
        "strategy": [
            "What is the smallest next step you can do now",
            "What result will tell you that step worked",
            "Want a 3-step plan for {topic_hint}",
        ],
        "reflection": [
            "What part feels strongest so far",
            "What part still needs one improvement",
            "Want feedback on one specific section first",
        ],
        "status": [
            "Which requirement is still incomplete",
            "Want a quick submit checklist for {topic_hint}",
            "Do you want to verify one final detail before submitting",
        ],
        "general": [
            "What have you already tried",
            "What did you expect to happen",
            "Want one small next step",
        ],
    },
    "es": {
        "debug": [
            "Que intentaste justo antes de que apareciera el problema",
            "Que prueba unica puedes hacer ahora para {topic_hint}",
            "Que cambio despues de tu ultima prueba",
        ],
        "concept": [
            "Puedes explicar esta idea con tus propias palabras",
            "Donde ves {topic_hint} en tu proyecto",
            "Quieres un ejemplo concreto y rapido",
        ],
        "strategy": [
            "Cual es el paso mas pequeno que puedes hacer ahora",
            "Que resultado te dira que ese paso funciono",
            "Quieres un plan de 3 pasos para {topic_hint}",
        ],
        "reflection": [
            "Que parte se siente mas fuerte hasta ahora",
            "Que parte todavia necesita una mejora",
            "Quieres comentarios primero sobre una parte especifica",
        ],
        "status": [
            "Que requisito todavia falta completar",
            "Quieres una lista rapida para entregar {topic_hint}",
            "Quieres verificar un detalle final antes de entregar",
        ],
        "general": [
            "Que has intentado hasta ahora",
            "Que esperabas que pasara",
            "Quieres un paso pequeno para seguir",
        ],
    },
    "so": {
        "debug": [
            "Maxaad isku dayday wax yar ka hor inta dhibaatadu dhicin",
            "Hal tijaabo oo xigta maxaad u samayn kartaa {topic_hint}",
            "Maxaa is beddelay kadib tijaabadii ugu dambeysay",
        ],
        "concept": [
            "Ma fikraddan ku sharixi kartaa erayadaada",
            "Xaggee ayaad {topic_hint} kaga aragtaa mashruucaaga",
            "Ma rabtaa tusaale kooban oo cad",
        ],
        "strategy": [
            "Waa maxay tallaabada ugu yar ee aad hadda qaadi karto",
            "Natiijadee kuu sheegi doonta in tallaabadaasi shaqeysay",
            "Ma rabtaa qorshe 3-tallaabo ah oo ku saabsan {topic_hint}",
        ],
        "reflection": [
            "Qaybtee ayaa hadda ugu xoog badan",
            "Qaybtee ayaa wali u baahan hal hagaajin",
            "Ma rabtaa jawaab celin ku saabsan hal qayb gaar ah marka hore",
        ],
        "status": [
            "Shuruuddee ayaa wali aan dhammeystirnayn",
            "Ma rabtaa liis hubin degdeg ah oo gudbinta {topic_hint}",
            "Ma rabtaa inaad hubiso hal faahfaahin oo ugu dambeysa ka hor gudbinta",
        ],
        "general": [
            "Maxaad horey u isku dayday",
            "Maxaad filaysay inay dhacdo",
            "Ma rabtaa hal tallaabo yar oo xigta",
        ],
    },
}


_ONE_CHECK_TRANSLATIONS = {
    "es": {
        "Check only the jump input path: confirm jumper seating and shared ground for that jump control.": (
            "Revisa solo la ruta de la entrada de salto: confirma que el jumper este bien asentado y que haya tierra compartida para ese control de salto."
        ),
        "Check shared ground first, then reseat one suspect jumper wire and retest before changing anything else.": (
            "Primero revisa la tierra compartida, luego vuelve a asentar un solo cable jumper sospechoso y prueba otra vez antes de cambiar cualquier otra cosa."
        ),
        "Compare the failing direction wire path to a known-good direction and change only one mismatch.": (
            "Compara la ruta del cable de la direccion que falla con una direccion que si funciona y cambia solo una diferencia."
        ),
        "Confirm you are on the exact StoryMode test step where controls are evaluated before rewiring.": (
            "Confirma que estas en el paso exacto de prueba de StoryMode donde se evalúan los controles antes de volver a cablear."
        ),
        "Pick one input, verify its jumper path and shared ground, then retest only that single input.": (
            "Elige una sola entrada, verifica su ruta de jumper y la tierra compartida, y luego vuelve a probar solo esa entrada."
        ),
    },
    "so": {
        "Check only the jump input path: confirm jumper seating and shared ground for that jump control.": (
            "Hubi oo keliya jidka gelinta jump-ka: xaqiiji in jumper-ku si fiican u fariistay iyo in shared ground-ku u yaallo xakameynta jump-kaas."
        ),
        "Check shared ground first, then reseat one suspect jumper wire and retest before changing anything else.": (
            "Marka hore hubi shared ground-ka, ka dibna dib u fariisi hal jumper wire oo laga shakisan yahay oo mar kale tijaabi ka hor intaadan wax kale beddelin."
        ),
        "Compare the failing direction wire path to a known-good direction and change only one mismatch.": (
            "Isbarbar dhig jidka siliga jihada fashilantay iyo jiho si fiican u shaqeyneysa, ka dibna beddel hal farqi oo keliya."
        ),
        "Confirm you are on the exact StoryMode test step where controls are evaluated before rewiring.": (
            "Xaqiiji inaad ku jirto tallaabada saxda ah ee tijaabada StoryMode ee lagu qiimeeyo xakameynta ka hor intaadan dib u siligin."
        ),
        "Pick one input, verify its jumper path and shared ground, then retest only that single input.": (
            "Dooro hal input, hubi jidka jumper-kiisa iyo shared ground-ka, ka dibna mar kale tijaabi input-kaas keliya."
        ),
    },
}
