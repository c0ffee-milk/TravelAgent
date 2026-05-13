# HANDOFF

## Goal

- Continue the TravelAgent teaching project around the current CLI demo and early lessons.
- Current focus: make the requirement-clarification loop more stable and map preview more useful before later itinerary planning.
- Keep the repository rule: functional logic belongs under `agent/src/`; `agent/scripts/demo_clarification_chat.py` should stay a thin integration/demo entrypoint.

## Current Progress

- Created repo-level `CLAUDE.md` with project architecture, commands, and working boundaries.
- Connected Lesson 03 Amap map tools into the demo as an optional ready-stage preview.
- Added map preview behavior in `agent/src/travel_agent/map_tools.py`:
  - destination geocoding
  - origin geocoding
  - route preview
  - theme-based POI preview
- Added LLM-assisted theme-to-POI query planning:
  - `agent/src/travel_agent/llm_provider.py` has `build_theme_poi_query_messages(...)`
  - `agent/src/travel_agent/map_tools.py` has `build_poi_preview_queries_with_llm(...)`
  - static `build_poi_preview_queries(...)` remains as fallback
- Stabilized time precision and transport preferences:
  - `agent/src/travel_agent/schemas.py` now includes `TimePrecision`
  - `TravelRequest` now includes `time_precision`, `long_distance_transport_preference`, `local_transport_preference`
  - `agent/src/travel_agent/request_normalization.py` was added to move request parsing/merging out of the demo
  - demo imports `travel_request_from_dict(...)` and `merge_travel_request(...)` from `request_normalization.py`
- Updated clarification behavior:
  - `agent/src/travel_agent/llm_provider.py` prompt asks for long-distance and local transport preferences
  - `agent/src/travel_agent/clarification.py` ready guard asks transport preference when origin/destination are known but preferences are missing
- Improved POI preview:
  - `collect_theme_pois(...)` aggregates multiple query terms
  - `canonicalize_poi_name(...)` canonicalizes names such as `宽窄巷子(地铁站)` -> `宽窄巷子`
  - `is_transport_or_subpoi(...)` filters transport/sub-POI noise like subway stations, bus stops, roads, parking lots, entrances/exits
  - `select_distinct_preview_pois(...)` selects distinct POI places
- Added Amap network resilience:
  - `AmapConfig.max_retries` from `AMAP_MAX_RETRIES`, default `2`
  - `AmapClient._send_with_retries(...)` retries transient network errors
  - POI multi-query collection continues after a single query failure and only fails if all queries fail

## What Worked

- Keeping demo thin and moving logic into `agent/src/` matched the user's explicit preference.
- `build_map_preview_lines(...)` returning display lines is a useful seam: demo just prints; source code owns behavior.
- LLM-assisted POI query planning improved abstract themes:
  - Example: `成都 + 经典景点打卡` produced `宽窄巷子` instead of searching the raw abstract theme.
- Deterministic `TimePrecision` avoids unstable `inferred.time_precision` values from the LLM.
- `py_compile` and `runpy` smoke checks worked as lightweight validation.

## What Didn't Work

- Directly searching raw theme strings like `城市漫游` produced bad POI results, e.g. unrelated game venues.
- Putting functional logic in `agent/scripts/demo_clarification_chat.py` was rejected by the user; do not repeat this.
- An earlier edit accidentally damaged `llm_provider.py` by inserting a new function over `build_natural_clarification_messages(...)`; when editing prompt files, use precise context and run compile immediately.
- Amap cross-city driving preview is semantically questionable when user prefers flight/high-speed rail. It can also create unnecessary API calls.
- Amap HTTPS/TLS handshake timeouts occurred after successful geocode calls; retry support was added, but API/network failures may still happen.

## Next Steps

- Run the demo manually with the latest changes:
  - `cd agent`
  - `python scripts/demo_clarification_chat.py`
- Re-test recent cases:
  - Xi'an case: `我想明年这个时候跟我女朋友去 西安旅游`, origin `武汉`, duration `一周左右`, budget `人均5000左右,包含交通和住宿`, transport `飞机吧,在西安主要坐公共交通`, theme `主要体验历史文化景点`
  - Chengdu case: similar flow with `成都` and `经典景点打卡`
- Watch specifically for:
  - `时间精度` staying deterministic (`month`, `day`, etc.)
  - transport preference guard asking once before ready
  - POI preview showing multiple distinct places, not one place's station/gate/road variants
  - Amap retry reducing handshake timeout failures
- Consider next improvement: make route preview respect `long_distance_transport_preference`.
  - Current `build_map_preview_lines(...)` signature only has `destination`, `origin`, `themes`.
  - To avoid irrelevant cross-city driving preview, pass `long_distance_transport_preference` and `local_transport_preference` from demo into `build_map_preview_lines(...)` and skip `driving_route(...)` unless user prefers self-driving.
- Consider adding tests under `agent/tests/`:
  - `derive_time_precision(...)`
  - `merge_travel_request(...)` not downgrading precision
  - transport ready guard in `clarification.py`
  - POI canonicalization/filtering/dedup in `map_tools.py`

## Verification Commands

```bash
cd agent
python -m py_compile src/travel_agent/schemas.py src/travel_agent/request_normalization.py src/travel_agent/clarification.py src/travel_agent/llm_provider.py src/travel_agent/map_tools.py scripts/demo_clarification_chat.py
python - <<'PY'
import runpy
runpy.run_path('scripts/demo_clarification_chat.py', run_name='not_main')
print('demo_runpy_load_ok')
PY
```

## Current Git State Notes

- Modified:
  - `agent/scripts/demo_clarification_chat.py`
  - `agent/src/travel_agent/clarification.py`
  - `agent/src/travel_agent/llm_provider.py`
  - `agent/src/travel_agent/map_tools.py`
  - `agent/src/travel_agent/schemas.py`
- New/untracked:
  - `CLAUDE.md`
  - `HANDOFF.md`
  - `agent/src/travel_agent/request_normalization.py`
