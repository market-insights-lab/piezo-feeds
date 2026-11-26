# Aerospace & Defense feeds

Two separate RSS feeds, harvested daily at 05:17 UTC by GitHub Actions:

- Tenders (EU TED API): `https://raw.githubusercontent.com/USER/REPO/main/feeds/tenders.xml`
  Aerospace, defence, space and astronomy tenders. High = piezo component level, Medium = system level.
- Patents (WIPO Patentscope RSS): `https://raw.githubusercontent.com/USER/REPO/main/feeds/patents.xml`
  Piezo patents filed by monitored competitors, kept only when they fall into one of the six business fields.

To start the patents feed: add the Patentscope RSS link of the competitor search to `config.json` → `patents.rss_feeds`.
`data/` keeps every item ever found. Run now: Actions → "Daily harvest" → Run workflow.
