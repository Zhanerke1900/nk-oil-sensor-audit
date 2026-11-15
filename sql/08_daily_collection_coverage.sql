WITH RECURSIVE calendar(date) AS (
    SELECT '2026-01-01'
    UNION ALL
    SELECT date(date, '+1 day') FROM calendar WHERE date < '2026-09-30'
), daily AS (
    SELECT substr(timestamp,1,10) AS date, COUNT(*) AS observed_rows,
           COUNT(DISTINCT well_id) AS wells_reporting
    FROM observations GROUP BY date
)
SELECT c.date, COALESCE(d.observed_rows, 0) AS observed_rows, 43 * 24 AS expected_rows,
       43 * 24 - COALESCE(d.observed_rows, 0) AS missing_rows,
       COALESCE(d.wells_reporting, 0) AS wells_reporting
FROM calendar c LEFT JOIN daily d ON c.date = d.date
ORDER BY missing_rows DESC, c.date;
