SELECT w.well_id, w.well_type, COUNT(*) AS observations,
       SUM(o.flag <> '') AS flagged_observations,
       ROUND(100.0 * SUM(o.flag <> '') / COUNT(*), 3) AS flagged_percent
FROM observations o JOIN wells w ON o.well_id = w.well_id
GROUP BY w.well_id, w.well_type HAVING SUM(o.flag <> '') >= 100
ORDER BY flagged_percent DESC;
