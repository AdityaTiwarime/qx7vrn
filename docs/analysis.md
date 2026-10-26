# How good are the wind forecasts? (January 2026)

Every number here is printed by `python backend/scripts/findings.py` from the committed data snapshot,
so it can be re-checked in seconds.

## The question

The trading team buys power in the GB day-ahead market the day before delivery. To know how much to buy
beyond what wind will supply, they rely on the national wind forecast (Elexon WINDFOR). This pilot asks:
**how far off was the forecast they would actually have had on screen, and how should they allow for that?**

**Main view:** for every hour of delivery day *D*, take the newest forecast published by **10:00 UK time on
day D-1**, a typical morning deadline for day-ahead buying. The cut-off time is adjustable in the app, so the
team can set its real deadline. The average lead time is about 26 hours.

## Headline results (10:00 cut-off, all 744 hours of January)

| Measure | Value | Meaning |
| --- | --- | --- |
| Typical error (MAE) | **2,107 MW** | 18.2% of average wind output (11,581 MW) |
| Bias | **+1,840 MW** | the forecast averaged 13,421 MW, but wind delivered 11,581 MW |
| Hours over-forecast | **84.4%** | wind came in below the forecast in more than 5 hours out of 6 |
| Error if bias removed | 1,460 MW | about 31% of the error is a steady offset, not noise |
| Buffer for 90% of hours | **4,377 MW** | the shortfall stayed below this in 9 hours out of 10 |
| Buffer for 95% of hours | 5,401 MW | |
| Worst hour | 6,857 MW | |
| Forecast vs actual correlation | 0.929 | the forecast tracks the *shape* of wind very well |

**What this means:** the forecast gets the ups and downs of wind right, but in January 2026 it was
consistently too high. A team buying against the raw forecast would have been short of wind in most hours,
by about 1.8 GW on average.

## Findings

1. **A steady over-forecast is the biggest single issue.** It shows up at every lead time: +1.6 GW even for
   forecasts made right before the hour, and +2.1 GW at 47 h. So it is not mainly about predicting the
   weather further ahead. Possible causes include wind farms being curtailed (paid to turn down) during grid
   constraints, which lowers metered output but not the weather-based forecast, and differences in which wind
   farms each dataset covers. This pilot does not verify the cause; that is a recommended next step.
2. **Correcting with recent bias helps, using only information available at decision time.** Subtracting the
   average error of the previous 7 complete days (known by D-1) cuts the typical error from 2,035 MW to
   1,705 MW, **16% lower**. This was tested day by day across 27 delivery days, with no look-ahead.
3. **Error grows with lead time, but slowly.** MAE is 1,794 MW for the newest forecast, 2,050 MW at 24 h ahead
   and 2,492 MW at 47 h ahead. Waiting for a later forecast helps a little: moving the cut-off from 10:00 to
   18:00 lowers MAE from 2,107 to 1,968 MW, if the market timing allows.
4. **Nights are worse.** The bias averages 2.3 GW between 00:00 and 07:00 UK, against 1.5 GW between 10:00 and
   20:00.
5. **A few days dominate the risk.** On 28 January, the daily average over-forecast was 5.3 GW; on 11 and 12
   January it was about 4.9 GW. The forecast ran low on average on only 4 days of the month.

## Recommendations for the pilot

- Treat the wind forecast as an upper estimate. Plan on the forecast minus a buffer: about **4.4 GW covers 90%
  of hours**, and about 5.4 GW covers 95%. The app recomputes these for any date range.
- Add a rolling bias correction (finding 2) to the product as the next feature, and show both raw and
  corrected forecasts.
- Investigate the cause of the bias with Elexon curtailment data before relying on it in production.

## Method and assumptions

- **Data:** Elexon BMRS FUELHH (`fuelType = WIND`, half-hourly actual output) and WINDFOR (hourly forecasts,
  published every 2–4 hours), downloaded by `backend/scripts/fetch_data.py`.
- **Scope:** target hours in January 2026 (UTC, which is UK time in winter). Only forecasts made 0–48 h before
  their target are used; forecasts published after the hour (hindcasts) are excluded.
- **Matching:** forecasts are hourly, so accuracy is scored on the 744 on-the-hour half-hours that have both
  values. Nothing is interpolated.
- **Error convention:** error = forecast − actual. Positive means wind came in short.
- **Lead time 47 h:** only 217 hours have a forecast that early, so the right end of the lead-time chart is
  based on fewer hours.
- **Bias correction:** for delivery day D, the average error of the up to 7 days ending at D-2 (the last day
  fully known when buying on D-1); days with fewer than 3 prior days are skipped.
- **Limits:** one winter month, national level only, wind only, as the brief requires. The results describe
  January 2026, not a guarantee for other months.
