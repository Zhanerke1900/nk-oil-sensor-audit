SELECT f.flag_name, COUNT(*) AS occurrences, COUNT(DISTINCT o.well_id) AS wells
FROM flags f JOIN observation_flags ofl ON f.flag_name = ofl.flag_name
JOIN observations o ON o.observation_id = ofl.observation_id
GROUP BY f.flag_name ORDER BY occurrences DESC;
