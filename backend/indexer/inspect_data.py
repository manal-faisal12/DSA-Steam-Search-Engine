import glob
import pyarrow.parquet as pq

files = glob.glob("data/raw/**/*.parquet", recursive=True)
print("Files:", files)

total = sum(pq.ParquetFile(f).metadata.num_rows for f in files)
print("Total rows:", total)

row = next(pq.ParquetFile(files[0]).iter_batches(batch_size=1)).to_pylist()[0]
for k, v in row.items():
    print(f"{k:28s} | {str(v)[:70]!r}")
