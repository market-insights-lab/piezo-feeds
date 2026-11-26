"""Aerospace & Defense relevance rules (sub-segments from the client's market structure)."""
import re
SUBRX = [
 ("Space – Optical Inter-Satellite Communication", r"inter.?satellite|free.?space optical|laser ?communication|laserkommunikation|optische bodenstation|optical (ground station|terminal)|point.?ahead|FSOC|OGS\b|optische bodenstation|station sol optique"),
 ("Space – Defense/Government", r"(reconnaissance|early.?warning|military|defen[cs]e|secure).{0,30}(satellite|space)|missile (detection|tracking)|space.?based (sensing|surveillance)|weltraum.{0,20}bundeswehr"),
 ("Defense – Land, Sea & Air", r"sonar|hydrophon|hydrofon|underwater|unterwasser|subacv|podwodn|povandenin|subaqu|submarin|torped|sonobuoy|towed array|anti.?submarine|mine ?(hunt|counter)|diver detection|ROV\b|AUV|UUV|multibeam|electro.?optical|EO/IR|gimbal|stabili[sz]ed (sight|platform)|naval|navy|marine|military|defen[cs]e|bundeswehr|armed forces|wojsk|armée|ejército|esercito"),
 ("Space – Commercial", r"satellit|star (tracker|sensor)|sternensensor|reaction wheel|spacecraft|launch vehicle|cubesat|antenna pointing|beam steering|fine pointing|\bspace (mission|segment|programme|program|system)|raumfahrt|weltraum"),
 ("Astronomy – Ground-based", r"adaptive optic|deformable mirror|tip.?tilt|segmented mirror|observator|astronom|telescop(e|io|ium)(?!ic)|teleskop(?!isch)|télescope"),
 ("Aviation – Commercial", r"aircraft|aviation|airplane|avionic|UAV|drone|flight control|structural health|SHM\b|engine test|luftfahrt|aéronaut|aeronáut"),
]
COMPONENT = r"piezo|transduc|wandler|(?<!optical )hydrophon|hydrofon|deformable mirror|tip.?tilt|fast steering mirror|beam steering|fine pointing|point.?ahead|star tracker|gimbal|hexapod|nanopositi|vibration (isolation|control|damp)|actuator|aktuator|aktor\b|phased array|ultrasonic (sensor|test|probe)"
EXCL = r"analysis platform|ferroelectric and piezoelectric analysis|legal|marketing|advertis|training|shipping|transport|shell work|shovel|borehole|drilling|programming services|time-lapse|photograph|video production|planetari|rehabilit|travaux|works|medical|hospital|patient|surgical|dental|clinic|ultrasound scanner|consumable|catering|cleaning|construction|budow|insurance|furniture|telescopic|teleskopisch|telescopio movil|fork ?lift|crane|ladder|handler|röntgen|x-ray|microscop"
def classify(text):
    if re.search(EXCL, text, re.I): return None
    sub = next((s for s, rx in SUBRX if re.search(rx, text, re.I)), None)
    comp = re.search(COMPONENT, text, re.I)
    if not sub and comp and re.search(r"space|satell|defen|military|naval|aircraft|telescop|optic", text, re.I): sub = "Defense – Land, Sea & Air"
    if not sub: return None
    if comp: return sub, "High", "Component level: needs piezo actuators, transducers, steering mirrors, positioning or vibration control – possible direct or partner bid"
    return sub, "Medium", "System level: platform that typically integrates piezo actuators or transducers – demand signal for OEM customers"
