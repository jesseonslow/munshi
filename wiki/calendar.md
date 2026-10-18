---
id: calendar
title: Calendar
canonical_name: Calendar
aliases: []
broader:
- Natural phenomena
narrower: []
related:
- title: Islam
  slug: islam
  inferred: true
is_cluster: false
is_contributor: false
status: stub
published: false
type: concept
generated: true
---

The concept of a calendar in the Malay world encompasses a broad spectrum of temporal systems, ranging from the star-based and solar-observation methods developed by indigenous farming communities of Borneo to the rigorous astronomical computation of Islamic prayer times. Both traditions address the fundamental problem of orienting human activity within the annual cycle, yet they do so through radically different epistemological frameworks: one rooted in direct empirical observation of celestial bodies, the other in the mathematical formalisation of solar geometry. Together, the records preserved in the Society's journals reveal how the near-equatorial setting of the region imposed distinctive constraints on timekeeping, forcing communities to devise solutions that differ markedly from those familiar in temperate latitudes.

## Indigenous Astronomical Timekeeping in Borneo

Charles Hose, writing in 1905 from his experience as a colonial administrator and ethnographer in Sarawak, argued that agriculture, even in its most rudimentary form, constitutes both a token and a cause of systematic observational knowledge among tropical peoples [[1, p. 1]](#ref-1). The Bornean farmer, unlike the hunter-gatherer, must study the course of the seasons, the nature of the soil, and the variability of plants and animals; it is this practical necessity that drives the development of temporal orientation [[1, p. 1]](#ref-1).

The specific difficulty in Borneo is climatic. From October to April the wind is usually from the north-east and brings rain, while during the rest of the year the monsoon is reversed, yet there is little else to distinguish one month's weather from another [[1, p. 1]](#ref-1). Temperature and moisture offer almost no reliable indication of the time of year, and the length of the day varies very little in the tropics, a variation the native has no means of observing [[1, p. 2]](#ref-1). The farmer therefore must turn to the stars or the sun.

Among the Dayaks and many lesser tribes, the stars provide the signal. A designated observer is appointed to go out before dawn to watch for the Pleiades, known in Malay as *bintang banyak* or *Apai andau* (the father of the day), while Orion's belt is called *bintang tiga* [[1, p. 2]](#ref-1). When the "seven stars" rise while it is yet dark, it is time to begin felling the forest [[1, p. 2]](#ref-1). Two men are sent into the jungle to find omens, and after a period ranging from two days to a month, the favourable indications appear and the community sets to work [[1, p. 2]](#ref-1). If they are so late that Orion's belt rises before daybreak, they must make every effort to regain lost time or the crop will be poor [[1, p. 2]](#ref-1).

The next critical operation—burning and sowing—is timed by a further stellar cue: only when the Pleiades are at the zenith before dawn do the Dayaks consider it advisable to proceed [[1, p. 3]](#ref-1). By this time, unless the weather has been unusually wet, the felled boughs are dry as match wood and the leaves are dead though still on the twigs [[1, p. 3]](#ref-1). The burning is accompanied by special charms to secure wind and by loud whirring intended to attract the Æolian spirits, after which the mass of dead wood is set alight [[1, p. 3]](#ref-1). The rice is then dropped by the women, a few grains at a time, into holes made by the men with pointed sticks [[1, p. 4]](#ref-1).

The Kenyahs and Kayans, by contrast, judge the seasons by the sun, and their methods display what Hose considered a remarkable knowledge of the precautions necessary to accuracy [[1, p. 4]](#ref-1). The Kenyahs measure the shadow cast at midday with an instrument that Hose notes the Greeks would have called a gnomon: a pole set up near the village, guarded by a fence to keep away children and animals, and more than a fathom in height by the span of the thumb and first finger [[1, p. 4]](#ref-1). A piece of string weighted at each end and thrown over the top shows when the pole is perfectly upright [[1, p. 4]](#ref-1). The length of the shadow is measured by a stick called *asu do*, marked with notches that gradually approach one another more closely as they recede from the pole, the interval between successive notches representing the change in shadow length over three days [[1, p. 4]](#ref-1).

The Kayan method differs in practice but not in theory: a beam of light is let in through a hole in the roof, and the distance from the point immediately beneath the hole to where the light reaches the floor is measured using a plank made level so that round discs do not roll on it, and fixed in position and direction by chocks placed at the side [[1, p. 4]](#ref-1). This arrangement demonstrates that the Kayans know the sun to be always due north or due south at noon [[1, p. 4]](#ref-1).

The optimal planting time for the Kenyahs arrives when the noon shadow equals the length of the forearm, from the tip of the fingers to the inside of the elbow; when the shadow is less than the length of the hand, sowing is unlikely to prove productive [[1, p. 5]](#ref-1). The measuring stick is left in the charge of an old and presumably wise man, excused from farming and supplied with necessaries in return for his services, who ensures that the shadow is not measured obliquely and reports the favourable moment [[1, p. 5]](#ref-1).

Hose offers an explanation for why these peoples, having achieved such precision, did not invent a conventional sundial: in the tropics, on many days near each equinox, no sundial would be of use, because when the sun passes from the north of the zenith to the south, its shadow points due west in the morning and due east in the afternoon, rendering any time-piece depending on shadow direction inoperative [[1, p. 5]](#ref-1).

## Islamic Temporal Computation

Mohamed Ilyas's 1978 article presents a rigorous mathematical framework for computing the five daily Islamic prayer times and the breaking of the fast using standard astronomical parameters [[2]](#ref-2). The central thesis is that all Islamic time markers can be reduced to specific solar zenith angles, making them amenable to precise calculation from published ephemeris data and, ultimately, to computer automation [[2]](#ref-2).

Ilyas establishes the correspondence between each Islamic time event and a defined solar zenith angle (*Z*). Sunset and sunrise are fixed at *Z* = 90°, midday (the beginning of *Zuhr*, the noon prayer) at the minimum *Z* for the day, and the end of *Fajr* (the dawn prayer) at the start of morning twilight [[2, pp. 46–48]](#ref-2). The more complex cases—the end of *Zuhr* and the two variants of *Asr* (the afternoon prayer, distinguished by the Shāfiʿī and Ḥanafī schools)—are derived from classical shadow-length rules: the end of *Zuhr* occurs when a vertical rod's shadow equals its own length plus its noon shadow, while *Asr* in the Ḥanafī school begins when the shadow equals twice the rod's length plus the noon shadow [[2, pp. 46–48]](#ref-2). These geometric conditions yield explicit formulas for the solar altitude at each transition [[2, pp. 47–48]](#ref-2).

A recurring theme in Ilyas's treatment is the deliberate separation of the astronomical calculation from the jurisprudential question of where exactly twilight begins and ends. He adopts *Z* = 105° for the Islamic twilight boundary, citing Maulānā Muftī Rāshid Aḥmad Ludhianavī's fifteen-degree view, but explicitly flags this as a parameter that Islamic scholars may revise without altering the computational machinery [[2, pp. 47–48]](#ref-2). Some authorities prefer 108° (eighteen degrees below the horizon) [[2, pp. 47–48]](#ref-2).

In the practical implementation, Ilyas shows how the universal parameters from the *Astronomical Ephemeris*—Right Ascension, Declination, and Greenwich Hour Angle—can be converted to local solar zenith angles via standard spherical trigonometry, and how the resulting equation can be solved for local time given a target zenith angle [[2, pp. 49–53]](#ref-2). He proposes two routes to a usable time table: a full computer programme that accepts latitude, longitude, and zone time as free parameters, or a simpler method using existing printed tables with a small set of arithmetic corrections for longitude, hemisphere, and secular drift [[2, pp. 49–53]](#ref-2). A time table constructed from the 1966-based *Tables of Sunrise, Sunset and Twilight* will remain accurate to within two to three minutes in mid-latitudes for two decades, provided a uniform five-minute correction is applied [[2, p. 52]](#ref-2). A table prepared for one city can be transferred to another at the same latitude (within five degrees) by adding a constant longitudinal correction; for different latitudes, a variable seasonal correction must also be applied [[2, pp. 52–53]](#ref-2).

The article was accompanied by a worked example for Adelaide (35°S, 138.6°E), yielding a longitude correction of sixteen minutes to convert mean solar time to local standard time [[2, p. 51]](#ref-2). Ilyas's contribution lies at the intersection of applied astronomy and Islamic practical jurisprudence (*fiqh al-mawāqit*, the jurisprudence of prayer times), offering one of the earliest published attempts in the Society's series to formalise prayer-time computation for the Southern Hemisphere and for computer implementation [[2]](#ref-2).

## Research and Documentation

The Society's literature on calendrical and temporal systems spans more than seven decades and reflects a marked shift in disciplinary orientation. Hose's 1905 note is characteristic of the early period of the *Journal of the Straits Branch of the Royal Asiatic Society*, in which colonial officials and residents contributed first-hand ethnographic accounts of indigenous practices [[1]](#ref-1). The piece draws on Hose's own field observation rather than on a named archival collection, and its framing—emphasising the intellectual capacity of "primitive" peoples to develop accurate observational knowledge—reflects the contemporary colonial-scientific interest in documenting such systems as evidence of human cognitive development [[1]](#ref-1). The article is concise, descriptive, and largely free of theoretical apparatus; its value lies in the specificity of the instruments described and the clarity with which the seasonal logic of slash-and-burn agriculture is laid out [[1]](#ref-1).

By 1978, the character of the Society's engagement with temporal computation had transformed entirely. Ilyas's article is a work of applied mathematics and astronomical physics, employing spherical trigonometry, ephemeris data, and algorithmic logic to produce a reproducible computational framework [[2]](#ref-2). Where Hose documented a community's empirical relationship with the sky, Ilyas formalised the geometric relationships that underpin a religiously mandated temporal order. The two articles are thus complementary rather than contradictory: one records how people without written calendars oriented their agricultural labour to the annual cycle through direct observation, the other demonstrates how the same solar geometry can be reduced to formulae and implemented programmatically.

The gap between these two publications also marks a broader shift in the Society's priorities, from the ethnographic documentation of indigenous knowledge systems to the technical service of the Muslim community in the Malaysian context. No intermediate publications on calendrical computation appear in the records provided, leaving the precise trajectory of the Society's interest in this subject between 1905 and 1978 undocumented in the available archive.

## MBRAS Sources

- [C. Hose](./c-hose.md) (1905). [Various methods of computing the time for planting among the races of Borneo](./various-methods-of-computing-the-time-for-planting-among-the.md). *[JSBRAS](./journal-of-the-malaysian-branch-of-the-royal-asiatic-society.md)* 42: 1–5
- [Mohammed Ilyas](./mohamed-ilyas.md). [Astronomical determination of Islamic times](./astronomical-determination-of-islamic-times.md). *JMBRAS* 51(1)
- Mohammed Ilyas. Visibility of the new moon: predictability. *JMBRAS* 51(2)
- Muhamed Sayid, Haji. Muhammadan calendar. *JMBRAS* 1(2)
- Names of months. *JSBRAS* 30

## References

1. <span id="ref-1"></span> C. Hose (1905). [Various methods of computing the time for planting among the races of Borneo](./various-methods-of-computing-the-time-for-planting-among-the.md) *JSBRAS* 42: 1–5. <a href="https://www.jstor.org/stable/41560561" class="aggregator-link" target="_blank" rel="noopener noreferrer">Read on JSTOR</a>
2. <span id="ref-2"></span> Mohamed Ilyas (1978). [Astronomical determination of Islamic times](./astronomical-determination-of-islamic-times.md) *JMBRAS* 51(1): 46–83.
