SELECT w.well_id, w.well_type, COUNT(o.observation_id) AS observations,
       COUNT(DISTINCT o.parameter) AS observed_parameters,
       MIN(o.timestamp) AS first_observation, MAX(o.timestamp) AS last_observation
FROM wells w LEFT JOIN observations o ON w.well_id = o.well_id
GROUP BY w.well_id, w.well_type ORDER BY w.well_id;
