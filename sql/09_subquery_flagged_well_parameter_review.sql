SELECT well_id, parameter, COUNT(*) AS observations,
       SUM(flag <> '') AS flagged_hours, SUM(value = 0) AS zero_value_hours
FROM observations
WHERE well_id IN (
    SELECT well_id FROM observations GROUP BY well_id HAVING SUM(flag <> '') >= 100
)
GROUP BY well_id, parameter ORDER BY well_id, parameter;
