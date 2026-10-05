---
id: astronomical-determination-of-islamic-times
work_id: jmbras-51-1-p46
title: Astronomical determination of Islamic times
canonical_name: Astronomical determination of Islamic times
type: article
article_type: article
authors:
- Mohamed Ilyas
year: 1978
journal_code: JMBRAS
volume: 51
issue: '1'
pages: 46–83
has_bibliography: true
has_footnotes: false
PublishedByMBRAS: true
amendments: []
status: stub
published: false
source_doc: jmbras-233-ilyas-astronomicaldeterminationislamic-1978-06c3e9c26631
source_path: ../sources/jmbras-233-ilyas-astronomicaldeterminationislamic-1978-06c3e9c26631.md
summarized: true
---
# Astronomical determination of Islamic times

Mohamed Ilyas published "Astronomical Determination of Islamic Times" in the *Journal of the Malaysian Branch of the Royal Asiatic Society* in 1978, presenting a rigorous mathematical framework for computing the five daily Islamic prayer times and the breaking of the fast using standard astronomical parameters. The article's central thesis is that all Islamic time markers can be reduced to specific solar zenith angles, making them amenable to precise calculation from published ephemeris data and, ultimately, to computer automation.

## Summary

Ilyas begins by establishing the correspondence between each Islamic time event and a defined solar zenith angle (Z). Sunset and sunrise are fixed at Z = 90°, midday (beginning of Zuhr) at the minimum Z for the day, and the end of Fajr at the start of morning twilight. The more complex cases—end of Zuhr and the two variants of Asr (Shafei and Hanafi)—are derived from the classical shadow-length rules: the end of Zuhr occurs when a vertical rod's shadow equals its own length plus its noon shadow, while Asr-Hanafi begins when the shadow equals twice the rod's length plus the noon shadow. These geometric conditions yield explicit formulas for the solar altitude at each transition (pp. 46–48).

The second half of the article shifts from theoretical derivation to practical implementation. Ilyas shows how the universal parameters from the *Astronomical Ephemeris* (Right Ascension, Declination, Greenwich Hour Angle) can be converted to local solar zenith angles via standard spherical trigonometry, and how equation (10) can be solved for local time given a target zenith angle. He then proposes two routes to a usable time table: a full computer programme that accepts latitude, longitude, and zone time as free parameters, or a simpler method using existing printed tables (*Tables of Sunrise, Sunset and Twilight* and Maniar's Tables) with a small set of arithmetic corrections for longitude, hemisphere, and secular drift (pp. 49–53).

A recurring theme is the deliberate separation of the astronomical calculation from the jurisprudential question of where exactly twilight begins and ends. Ilyas adopts Z = 105° for the Islamic twilight boundary (citing Maulana Mufti Rashid Ahmad Ludhianavi's 15° view) but explicitly flags this as a parameter that Islamic scholars may revise without altering the computational machinery (pp. 47–48).

### Key Findings

- The solar zenith angle for apparent sunrise/sunset, after correcting for the Sun's semi-diameter (16′) and mean atmospheric refraction at mid-latitudes (34′), is Z = 90° 50′ rather than the geometric 90° (p. 50).
- The end of Zuhr and beginning of Asr-Shafei are defined by the altitude formula A = Cot⁻¹(1 + Cot An), where An is the solar altitude at noon; Asr-Hanafi uses A = Cot⁻¹(2 + Cot An) (pp. 47–48).
- The Islamic twilight boundary is provisionally set at Z = 105° (i.e., 15° below the horizon), with the author noting that some authorities prefer 108° (18°) and that the value is open to scholarly revision (pp. 47–48).
- A time table constructed from the 1966-based *Tables of Sunrise, Sunset and Twilight* will remain accurate to within 2–3 minutes in mid-latitudes for two decades, provided a uniform 5-minute correction is applied (p. 52).
- A time table prepared for one city can be transferred to another city at the same latitude (±5°) by adding a constant longitudinal correction equal to the difference of their respective longitude-to-zone-time offsets; for different latitudes, a variable seasonal correction must also be applied (pp. 52–53).
- The article was accompanied by a worked example for Adelaide (35°S, 138.6°E), yielding a longitude correction of +16 minutes to convert mean solar time to local standard time (p. 51).

### Conclusion

Ilyas concludes that the astronomical basis for Islamic times is now sufficiently well-defined to be encoded in a computer programme accessible to any Muslim organisation, and that a simpler table-based method requiring only basic arithmetic is available for communities without computing facilities. He leaves the final calibration of the twilight angle to Islamic scholars, positioning the article as a technical infrastructure upon which jurisprudential decisions can be applied.

## Context

- Primary data sources: the *Astronomical Ephemeris* (annual), *Tables of Sunrise, Sunset and Twilight* (1966-based), and Maniar's Tables for Asr shadow ratios.
- The article's contribution lies at the intersection of applied astronomy and Islamic practical jurisprudence (fiqh al-mawaqit), offering one of the earliest published attempts in the MBRAS series to formalise prayer-time computation for the Southern Hemisphere and for computer implementation.

## References
<!-- Grounded occurrences and citations -->
