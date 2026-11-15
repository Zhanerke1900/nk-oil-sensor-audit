SELECT split, COUNT(*) AS observations, MIN(timestamp) AS first_time,
       MAX(timestamp) AS last_time, SUM(flag <> '') AS flagged_observations,
       COUNT(DISTINCT well_id) AS wells
FROM observations GROUP BY split ORDER BY first_time;
