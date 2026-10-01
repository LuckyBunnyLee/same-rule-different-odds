"""Parse the raw yt-dlp flat listing of the World Athletics channel (retrieved 2026-09-28) into a clean TSV.

Usage:
  python analysis/measure/parse_channel_listing.py --raw analysis/measure/discovery/wa_channel_videos.tsv \
      --out analysis/measure/discovery/wa_channel_videos_clean.tsv
The raw file was produced by: yt-dlp --flat-playlist --print "%(id)s\t%(duration)s\t%(upload_date)s\t%(title)s"
https://www.youtube.com/@WorldAthletics/videos (the \t was written literally, hence this parser).
"""
import argparse

BS = chr(92) + "t"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = []
    for line in open(a.raw, encoding="utf-8", errors="replace"):
        parts = line.rstrip("\n").split(BS)
        if len(parts) >= 4:
            rows.append(parts[:3] + [BS.join(parts[3:])])
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("id\tduration\tupload_date\ttitle\n")
        for r in rows:
            f.write("\t".join(r) + "\n")


if __name__ == "__main__":
    main()
