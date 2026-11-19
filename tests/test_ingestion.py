from pathlib import Path
import tempfile
import unittest

import pandas as pd
from src.ingestion import read_chunks, validate_frame


class IngestionChecks(unittest.TestCase):
    def test_chunk_size_must_be_positive_integer(self):
        for chunksize in (0, -2, True, 1.5):
            with self.subTest(chunksize=chunksize):
                with self.assertRaisesRegex(ValueError, "chunksize"):
                    read_chunks(Path("irrelevant.csv"), chunksize=chunksize)

    def test_chunked_read_preserves_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "small.csv"
            path.write_text("well_id,value\nNK-7,1\nNK-7,2\n", encoding="utf-8")
            frame, largest_chunk_bytes = read_chunks(path, chunksize=1)
        self.assertEqual(frame["value"].tolist(), [1, 2])
        self.assertGreater(largest_chunk_bytes, 0)

    def test_empty_measurement_file_is_rejected(self):
        columns = ["well_id", "well_type", "timestamp", "parameter", "value",
                   "unit", "n_obs", "flag"]
        with self.assertRaisesRegex(ValueError, "No sensor observations"):
            validate_frame(pd.DataFrame(columns=columns))


if __name__ == "__main__":
    unittest.main()
