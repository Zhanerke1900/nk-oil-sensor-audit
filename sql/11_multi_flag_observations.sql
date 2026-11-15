SELECT o.observation_id, o.well_id, o.parameter, o.timestamp, o.value,
       COUNT(ofl.flag_name) AS flag_count,
       GROUP_CONCAT(ofl.flag_name, ';') AS individual_flags
FROM observations o JOIN observation_flags ofl ON o.observation_id = ofl.observation_id
GROUP BY o.observation_id HAVING COUNT(ofl.flag_name) > 1
ORDER BY o.timestamp;
