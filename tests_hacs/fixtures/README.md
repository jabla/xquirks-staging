# Frozen content

Copies of real quirk files and manifest entries that the tests load, edit or compare. They are
frozen because the content may drop any file once ZHA covers its device itself. Replace a quirk
file only when the guard stops accepting it, for example in the pull request that brings a new
`fixed_code.json`; replace its entry in `manifest.json` with it.

- `manifest.json`: the manifest entries of the quirk files below that the guard tests check them
  against
- `z2m_tuya_ts0105.py.txt`, `z2m_bosch_bsen_w.py.txt`, `z2m_moes_zm6lt1.py.txt`,
  `z2m_aqara_qbcz15lm.py.txt`, `z2m_alias_moes_zc_hm.py.txt`, `z2m_alias_neo_nas_wv03b.py.txt`: the
  guard tests (`test_guard_files.py`, `test_guard.py`); the Tuya file also in the registry check of
  `test_edge_cases.py`
- `z2m_sonoff_trv_zbt_*.py.txt`: two revisions of one file (change list tests), one of them also in
  the registry check of `test_edge_cases.py`
- `manifest-kinds.json`: real manifest entries, one of each kind the integration reads (a zcl file
  with endpoints, a Tuya file, alias files, a take-over, a refused take-over, a device not built,
  open upstream pull requests). Replace them with current entries of the same kinds when the
  manifest changes its fields.
