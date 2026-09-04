# Data & label-set licences

Every third-party dataset, label set, or tag pack shipped with or used to train
Aegis must be listed here with its licence and a link, before it is committed or
relied on in a demo. This is a Phase 0 stub — fill each row as the dataset is
actually brought in (tracked in the design vault's open questions).

| Dataset / label set | Purpose | Licence | Source | Verified | Notes |
|---|---|---|---|---|---|
| Elliptic | GNN training (Bitcoin illicit-tx typology) | _TBD_ | _TBD_ | ☐ | Research-use terms need reading before redistribution |
| Elliptic++ | GNN training (extended actor/tx graph) | _TBD_ | _TBD_ | ☐ | |
| GraphSense TagPacks | VASP / service attribution | _TBD_ | https://github.com/graphsense/graphsense-tagpacks | ☐ | Per-pack licences vary |
| BABD-13 | Address-behaviour classification | _TBD_ | _TBD_ | ☐ | |
| OFAC SDN list | Sanctioned-address flagging | Public domain (US Gov) | https://sanctionslist.ofac.treas.gov | ☐ | |
| Block-explorer labels (scraped) | Heuristic attribution | _TBD_ | _TBD_ | ☐ | Check each explorer's ToS; may not be redistributable |
| India VASP pack (our own) | Domestic exchange attribution | MIT (this repo) | internal | ☐ | Document provenance of each entry |

## Rules

- A dataset with an unread or incompatible licence does **not** get committed or
  shown in a demo.
- Redistributable data lives in the repo (small) or a documented release asset
  (large). Non-redistributable data is fetched by a script with the licence
  acknowledgement inline.
- Demo mode never uses real victim data. Public addresses used in scenarios must
  have documented provenance.
