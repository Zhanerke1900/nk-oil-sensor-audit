WITH completeness AS (
    SELECT wp.well_id, wp.parameter, 6552 AS expected_hours,
           COUNT(o.observation_id) AS observed_hours,
           6552 - COUNT(o.observation_id) AS missing_hours
    FROM well_parameters wp LEFT JOIN observations o
      ON wp.well_id = o.well_id AND wp.parameter = o.parameter
    GROUP BY wp.well_id, wp.parameter
)
SELECT *, DENSE_RANK() OVER (ORDER BY missing_hours DESC) AS missing_rank
FROM completeness ORDER BY missing_rank, well_id, parameter;
