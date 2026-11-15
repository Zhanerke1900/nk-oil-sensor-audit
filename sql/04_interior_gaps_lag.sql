WITH ordered AS (
    SELECT well_id, parameter, timestamp,
           LAG(timestamp) OVER (
               PARTITION BY well_id, parameter ORDER BY timestamp
           ) AS previous_timestamp
    FROM observations
)
SELECT well_id, parameter, previous_timestamp, timestamp,
       (CAST(strftime('%s', timestamp) AS INTEGER) -
        CAST(strftime('%s', previous_timestamp) AS INTEGER)) / 3600 - 1 AS missing_hours
FROM ordered
WHERE (CAST(strftime('%s', timestamp) AS INTEGER) -
       CAST(strftime('%s', previous_timestamp) AS INTEGER)) > 3600
ORDER BY well_id, parameter, timestamp
;
