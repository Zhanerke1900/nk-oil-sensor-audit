SELECT w.well_id, w.well_type, o.parameter, p.unit,
       substr(o.timestamp,1,7) AS month, COUNT(*) AS observations,
       AVG(o.value) AS mean_value, SUM(o.flag <> '') AS flagged_hours
FROM observations o JOIN wells w ON w.well_id = o.well_id
JOIN parameters p ON p.parameter = o.parameter
GROUP BY w.well_id, w.well_type, o.parameter, p.unit, month
ORDER BY w.well_id, o.parameter, month;
