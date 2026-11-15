SELECT regime, parameter, COUNT(*) AS observations,
       AVG(value) AS mean_value, SUM(value = 0) AS zero_hours,
       SUM(value < 0) AS negative_hours, SUM(flag <> '') AS flagged_hours
FROM observations WHERE well_id = 'NK-7'
GROUP BY regime, parameter ORDER BY parameter, regime;
