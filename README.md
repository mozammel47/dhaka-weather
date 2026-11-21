# Dhaka Weather

Automated climate graphs for Dhaka, Bangladesh, built in Python with matplotlib
and refreshed daily by GitHub Actions.

**Why this exists.** A phone already tells you whether to carry an umbrella. What
it never tells you is whether Dhaka is becoming a different place to live in.
Every panel here is chosen to answer something a weather app cannot, and the test
applied to each one was whether it would surprise a person who has checked their
forecast every day for a year.

The daily refresh is not the point, but it does mean each figure carries a live
marker for where the current year stands against the whole record.

## The four indicators

![Dhaka climate indicators](graphs/ClimateIndicators_Dhaka.png)

| Panel | Question it answers | Ramp |
| --- | --- | --- |
| A, hot nights | Is it getting harder to sleep | purples |
| B, humid heat days | Is outdoor work getting more dangerous | reds |
| C, monsoon season | Are the rains shifting | blues |
| D, rain concentration | Is the rain getting flashier | greens |

Heat, heat plus humidity, rain timing, rain intensity. Four distinct mechanisms,
no redundancy between them.

**Thresholds come from Dhaka, not from a textbook.** A hot night and a heat day
are both defined as the 90th percentile of Dhaka's own 1961 to 1990 record. This
matters more than it sounds. The European "tropical night" threshold of 20 °C is
meaningless here, because nearly every Dhaka summer night clears it. Asking how
often today's weather would have counted as unusual within living memory is the
question that travels. The exact threshold in degrees is printed on the figure
itself and recomputed every run, so it is never a hidden constant.

**Why apparent temperature for panel B.** In a delta city the humid heat is the
story and the dry-bulb reading hides it. Open-Meteo serves apparent temperature
directly, so humidity is folded into the indicator rather than ignored.

**Why the night panel at all.** Warm nights track heat mortality more closely
than daytime peaks, since a hot day is survivable if the night lets the body shed
heat. Overnight minima also tend to rise faster than daytime maxima under
warming, so a drift upward usually shows here first.

**Partial years are handled honestly.** The current year is incomplete by
definition, so it is drawn as a dark bar labelled "to date" and excluded from
every running mean. Only years with at least 360 daily records count as complete.

### Monsoon dates, and a caveat

There is no single agreed definition of monsoon onset. The Bangladesh
Meteorological Department, the India Meteorological Department and the research
literature all use different criteria, so the dates in panel C are one defensible
rule rather than an official declaration. The rule is stated here and lives in
the constants at the top of `src/indicators.py`.

- **Onset.** The first day from 1 May onward where that day plus the next six
  bring at least 40 mm, and that day plus the next nineteen bring at least
  100 mm. The second condition is what stops an isolated pre-monsoon
  thunderstorm from being read as the monsoon arriving.
- **Withdrawal.** The first day from 1 September onward whose following
  fortnight brings less than 20 mm. Withdrawal is recorded as the day before
  that dry spell begins.

Change the numbers in one place and the whole series recomputes. If you are
comparing against a published onset series, expect offsets of a week or more, and
say which definition you used.

`data/indicators.csv` carries every yearly value behind the figure, so you can
plot or model them without rerunning anything.

## The seasonal graphs

Three Tufte-style ribbon charts, kept because they show the seasonal texture that
the indicator panel deliberately throws away.

![Daily high temperature in Dhaka](graphs/DailyHighTemp_Dhaka.png)

![Overnight low temperature in Dhaka](graphs/OvernightLowTemp_Dhaka.png)

![Cumulative rainfall in Dhaka](graphs/CumulativeRainfall_Dhaka.png)

*All four images fill in after the first fetch-and-build run, whether you run it
locally or trigger the workflow from the Actions tab.*

These are a Python port of [jdjohn215/milwaukee-weather](https://github.com/jdjohn215/milwaukee-weather),
adapted for a monsoon climate. The original uses R, ggplot2 and NOAA's GHCN-Daily
station records. The graphic itself is much older than either repository, and the
lineage is set out under
[Where this graphic comes from](#where-this-graphic-comes-from) below.

Each graph carries its own colour ramp so the three are told apart instantly,
warm reds for daytime heat, purples for the night, blues for rain.

**Daily high temperature.** Nested ribbons give the distribution of the daily
maximum temperature for every calendar day across the whole record, from the
all-time range down to the 40th to 60th percentile core. The black line is the
current year. Red and blue dots mark days where the current year broke the
all-time record for that calendar day, judged against the unsmoothed daily
extremes. In Dhaka this curve peaks in April, before the monsoon arrives, not at
midsummer.

**Overnight low temperature.** The same picture drawn from the daily minimum.
This is the quieter half of the temperature story and often the more
consequential one, since a hot day is survivable if the night lets the body shed
heat. Warm nights track heat mortality more closely than daytime peaks do, and
overnight minima tend to rise faster than daytime maxima under warming, so a
drift upward usually shows here first.

**Cumulative rainfall.** Dhaka receives most of its rain in a few monsoon months,
so a running annual total says far more than daily bars. Bands cover the full
historical range plus the 10th to 90th and 25th to 75th percentiles. The wettest
and driest years on record are traced as dashed lines, and the current year is
labelled against the median for the same date.

## Where this graphic comes from

This design has a long pedigree and it is worth stating plainly, since the
version here is four steps removed from the original.

1. **The New York Times, 11 January 1981, page 32.** The paper's graphics desk
   published "New York City's Weather for 1980", a single hand-drawn panel
   carrying roughly 2,200 numbers across temperature, precipitation and humidity,
   with the year's daily values set against the long-run normal.
2. **Edward Tufte, 1983.** He reproduced it on page 30 of *The Visual Display of
   Quantitative Information* as an example of a newspaper graphic that chooses
   detail over simplicity and succeeds. That reproduction is why the chart is
   widely known as a Tufte graphic. He later drew his own version,
   [New York City's Weather in 2003](https://www.edwardtufte.com/bboard/q-and-a-fetch-msg?msg_id=00014g).
3. **Brad Boehmke, 2014.** He rebuilt the chart in R for Dayton, Ohio, adding the
   percentile ribbons and the record-breaking day markers that this repository
   uses. [Alex Bresler](https://gist.github.com/abresler/46c36c1a88c849b94b07)
   adapted that code for New York City, and between them the R recipe spread
   widely.
4. **John D. Johnson, [jdjohn215/milwaukee-weather](https://github.com/jdjohn215/milwaukee-weather).**
   He wrapped the chart in a GitHub Actions workflow that refetches NOAA data and
   rebuilds the graphs every day. That automation pattern is what this repository
   ports to Python.

So the picture belongs to the NYT graphics desk and to Tufte, the percentile-band
and record-marker treatment to Boehmke, the daily automation to Johnson, and only
the Python, the ERA5 pipeline and the Dhaka framing are new here.

## About the data

[Open-Meteo](https://open-meteo.com/) serves ECMWF ERA5 and ERA5-Land reanalysis
as a free API with no key required. Two endpoints are used together.

| Endpoint | Role |
| --- | --- |
| `archive-api.open-meteo.com/v1/archive` | daily values from 1940 to roughly five days ago |
| `api.open-meteo.com/v1/forecast` with `past_days` | patches the reanalysis lag so the series runs to yesterday |

Variables pulled are `temperature_2m_max`, `temperature_2m_min`,
`precipitation_sum` and `apparent_temperature_max`, all in metric units, with the
day boundary set to `Asia/Dhaka`. If you have a cached CSV from before the
apparent-temperature column existed, the fetch script notices the missing column
and refetches the whole record rather than leaving a gap.

Reanalysis is a model-plus-observations product rather than a gauge reading at a
single point. For Dhaka that is a feature, since the local gauge record in
GHCN-Daily is patchy. If you want the station record instead, see the note on
swapping sources below.

**Citation.** Hersbach, H. et al. (2020), The ERA5 global reanalysis.
*Quarterly Journal of the Royal Meteorological Society*, 146, 1999 to 2049.
Open-Meteo asks that you credit them and link back when you publish a graph.

## Running it yourself

```bash
pip install -r requirements.txt

python src/fetch_dhaka.py                 # writes data/dhaka_daily.csv
python src/indicators.py                  # writes data/indicators.csv
python src/build_indicators.py            # writes graphs/ClimateIndicators_Dhaka.png
python src/build_daily_high.py            # writes graphs/DailyHighTemp_Dhaka.png
python src/build_overnight_low.py         # writes graphs/OvernightLowTemp_Dhaka.png
python src/build_cumulative_precip.py     # writes graphs/CumulativeRainfall_Dhaka.png
```

`src/indicators.py` also prints one line of plain arithmetic comparing the last
ten complete years against the first ten on record, which is the sentence worth
putting at the top of the README once you have real data in hand.

The first fetch pulls the whole record from 1940 in twenty-year chunks and takes
a minute or two. Later runs refetch only a trailing window and merge, because
ERA5 revises its most recent days as the reanalysis settles. Pass `--full` to
force a complete refetch.

Useful flags.

```bash
python src/build_daily_high.py --smooth 1        # raw daily percentiles, no smoothing
python src/build_daily_high.py --smooth 11       # heavier smoothing of the ribbons
python src/build_daily_high.py --palette night   # any chart in any of the three ramps
python src/build_daily_high.py --data path.csv --out somewhere.png
```

### No network access

`tools/make_sample_data.py` writes a synthetic Dhaka-like series so the plotting
code can be exercised offline. It is not real weather data.

```bash
python tools/make_sample_data.py --out data/sample_dhaka_daily.csv
python src/build_daily_high.py --data data/sample_dhaka_daily.csv --out graphs/_preview.png
```

## Automatic updating

`.github/workflows/update-graphs.yml` runs every day at 02:15 UTC, which is 08:15
in Dhaka. It refetches the data, rebuilds both graphs and commits the result back
to the repository. You can also trigger it by hand from the Actions tab.

Two settings matter on a fresh fork. Under Settings, Actions, General, set
workflow permissions to read and write, otherwise the commit step cannot push.
And GitHub disables scheduled workflows on repositories with no activity for
sixty days, so a run by hand wakes it up again.

## Adapting this to another city

Everything location-specific sits at the top of `src/fetch_dhaka.py`.

```python
LATITUDE = 23.8103
LONGITUDE = 90.4125
TIMEZONE = "Asia/Dhaka"
LOCATION_NAME = "Dhaka"
```

Change those four values, update the `title` passed by each build script, and the
rest follows. The rainfall y-axis step switches between 250 mm and 500 mm on its
own depending on how wet the place is.

To use a NOAA GHCN-Daily station instead, find the station code in
[ghcnd-stations.txt](https://www1.ncdc.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt)
and read `https://www.ncei.noaa.gov/pub/data/ghcn/daily/by_station/<CODE>.csv.gz`
into the same column layout that `src/fetch_dhaka.py` writes, which is
`date, year, month, day, day_of_year, tmax_c, tmin_c, app_tmax_c, prcp_mm`. GHCN
values arrive in tenths of a degree Celsius and tenths of a millimetre, so divide
both by ten. The Dhaka station code is `BGM00041923`.

One thing does not survive that swap. GHCN-Daily carries no apparent temperature,
so panel B would have to fall back to dry-bulb maxima, which for a delta city
loses the part of the heat signal that actually harms people. Everything else
works unchanged.

## Figure settings and colour

`src/style.py` holds the shared matplotlib configuration. Output is 300 dpi on a
170 mm canvas, Arial with TrueType font embedding (`pdf.fonttype` and
`ps.fonttype` set to 42), saved without `bbox_inches="tight"` so the declared
canvas size is exact. Change the canvas in one place and all three graphs follow.

The same file holds the four palettes, each a ColorBrewer sequential ramp of four
steps running light to dark.

| Name | Ramp | Seasonal graph | Indicator panel |
| --- | --- | --- | --- |
| `heat` | reds | daily high temperature | B, humid heat days |
| `night` | purples | overnight low temperature | A, hot nights |
| `rain` | blues | cumulative rainfall | C, monsoon season |
| `burst` | greens | none | D, rain concentration |

Sequential ramps were chosen over arbitrary colours for two reasons. They survive
being printed in greyscale, since each step differs in lightness as well as hue,
and they stay readable under the common forms of colour vision deficiency. The
lightest step in each ramp is kept deliberately darker than the linen paper, so
the outermost record-range band does not vanish into the background. Every
seasonal build script takes `--palette`, so any of those charts can be drawn in
any of the four.

The indicator figure uses `apply_panel_style()` rather than the single-chart
style, with slightly smaller tick and title type, since four panels on one
170 mm canvas crowd at full publication size.

## Layout

```
.
├── src/
│   ├── style.py                      canvas, fonts and the four palettes
│   ├── fetch_dhaka.py                data retrieval and incremental caching
│   ├── indicators.py                 the four yearly metrics and their thresholds
│   ├── build_indicators.py           four-panel indicator figure
│   ├── ribbon.py                     shared builder for the two temperature graphs
│   ├── build_daily_high.py           daily high temperature graph
│   ├── build_overnight_low.py        overnight low temperature graph
│   └── build_cumulative_precip.py    cumulative rainfall graph
├── tools/
│   └── make_sample_data.py           synthetic series for offline testing
├── data/                             dhaka_daily.csv and indicators.csv
├── graphs/                           generated PNGs
└── .github/workflows/
    └── update-graphs.yml             daily refresh
```

`indicators.py` holds no plotting code and `build_indicators.py` holds no
statistics, so a threshold can be argued with and changed without touching the
figure. Adding another ribbon chart is a dozen lines. Copy
`build_overnight_low.py`, point `value` at another column and give it a title,
since `ribbon.py` does the rest.

## Credit

Original graphic by the New York Times graphics desk, 11 January 1981.
Reproduced and made famous by [Edward Tufte](https://www.edwardtufte.com/bboard/q-and-a-fetch-msg?msg_id=00014g)
in *The Visual Display of Quantitative Information* (1983), page 30.
Percentile bands and record markers from Brad Boehmke's R recreation (2014).
Daily automation pattern by [John D. Johnson](https://github.com/jdjohn215/milwaukee-weather).
Weather data by [Open-Meteo](https://open-meteo.com/), derived from ECMWF ERA5.
Colour ramps from [ColorBrewer](https://colorbrewer2.org/) by Cynthia Brewer.
