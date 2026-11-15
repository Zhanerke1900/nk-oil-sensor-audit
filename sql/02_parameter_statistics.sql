SELECT p.parameter, p.unit, COUNT(*) AS observations, AVG(o.value) AS mean_value,
       MIN(o.value) AS minimum_value, MAX(o.value) AS maximum_value,
       AVG(o.n_obs) AS mean_raw_records_per_hour
FROM observations o JOIN parameters p ON p.parameter = o.parameter
GROUP BY p.parameter, p.unit ORDER BY p.parameter;
