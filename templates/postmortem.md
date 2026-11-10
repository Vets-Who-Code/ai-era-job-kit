# Blameless postmortem

One incident, one cause, one fix. No blame, on you or on them.

**Application:** company / role / funnel id
**Date:**

## 01 · Incident
What happened, and at which stage? (applied, screen, second, third, final, offer)

## 02 · Cause
The one cause you can act on. Not "the market", not "they picked someone else".

## 03 · Fix
The one change, and the layer it fixes:

| If you see | Layer | Fix |
|---|---|---|
| No screens | resume | Resume score, Screen Grade, shift channels |
| Screens, but no finals | interview | Mock screens, rerun your weakest answers |
| Finals, but no offers | defense | Defend every line: Stack Defense Doc |
| One source never converts | channel | Reallocate toward what converts |

Log it: `python3 scripts/funnel.py postmortem --id N --cause "..." --fix "..." --layer resume|interview|defense|channel`

**72-hour rule:** no upward momentum within 72 hours means the fix was opinion, not tactical intelligence. Try the next one.
