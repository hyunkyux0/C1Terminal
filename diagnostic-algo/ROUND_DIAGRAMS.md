# Per-Round Structure Diagrams

## Legend

```
T = Turret          U = Upgraded Turret
W = Wall            X = Upgraded Wall
S = Support         P = Upgraded Support
. = Empty tile      (space) = Out of arena
^ = Funnel gap      * = Chokepoint (open corridor)
```

## Cost Reference

| Unit     | Place | Upgrade |
|----------|-------|---------|
| Wall     | 2 SP  | 1 SP    |
| Turret   | 3 SP  | 8 SP    |
| Support  | 4 SP  | 4 SP    |

## Arena Column Index

```
         1111111111222222222
x: 0123456789012345678901234567
```

---

## Turn 0 (40 SP, 5 MP)

Spent: 4 turrets (12 SP) + 14 walls (28 SP) = 40 SP
Mobile: 1 interceptor (3 MP)

The wall list is interleaved left/right from corners inward:
[1,13],[26,13],[2,13],[25,13],...,[7,13],[20,13] = 14 walls.
Remaining 10 walls ([8-12,13] and [15-19,13]) can't be afforded.

```
         1111111111222222222
x: 0123456789012345678901234567

y13: TWWWWWWW............WWWWWWWT
y12:  ..........T...T..............
y11:   ........................
```

Gap at y=13: x=8..19 (12 tiles wide, wide open)
Kill box turrets at [11,12] and [15,12] are placed but gap hasn't narrowed to them yet.
SP remaining: 0

---

## Turn 1 (+5 SP = 5 SP)

Spent: 2 walls (4 SP)
New walls: [8,13] and [19,13]

```
         1111111111222222222
x: 0123456789012345678901234567

y13: TWWWWWWWW..........WWWWWWWWT
y12:  ..........T...T..............
```

Gap at y=13: x=9..18 (10 tiles)
SP remaining: 1

---

## Turn 2 (+5 SP = 6 SP)

Spent: 3 walls (6 SP)
New walls: [9,13], [18,13], [10,13]

```
         1111111111222222222
x: 0123456789012345678901234567

y13: TWWWWWWWWWW.......WWWWWWWWWT
y12:  ..........T...T..............
```

Gap at y=13: x=11..17 (7 tiles)
Supports now eligible (turn >= 2) but 0 SP left.
SP remaining: 0

---

## Turn 3 (+5 SP = 5 SP)

Spent: 2 walls (4 SP)
New walls: [17,13], [11,13]

```
         1111111111222222222
x: 0123456789012345678901234567

y13: TWWWWWWWWWWW.....WWWWWWWWWWT
y12:  ..........T...T..............
```

Gap at y=13: x=12..16 (5 tiles)
SP remaining: 1

---

## Turn 4 (+5 SP = 6 SP)

Spent: 3 walls (6 SP)
New walls: [16,13], [12,13], [15,13]

```
         1111111111222222222
x: 0123456789012345678901234567

y13: TWWWWWWWWWWWWW^^WWWWWWWWWWWT
y12:  ..........T...T..............
```

**FUNNEL MOUTH COMPLETE!** Gap narrowed to x=13,14 (2 tiles).
But chokepoint walls at y=12 not yet placed -- corridor is still wide at y=12.
SP remaining: 0

---

## Turn 5 (+5 SP = 5 SP)  --  FIRST ATTACK TURN

Spent: 2 chokepoint walls (4 SP)
New walls: [12,12] and [14,12]
Attack: ~9 scouts from least-damage side

```
         1111111111222222222
x: 0123456789012345678901234567

y13: TWWWWWWWWWWWWW^^WWWWWWWWWWWT
y12:  ..........TW*WT..............
y11:   ........................
```

**CHOKEPOINT ACTIVE!** All traffic forced through [13,12] (marked *).
Turrets at [11,12] and [15,12] both fire on anything at [13,12].

Our scout path: [13,0] -> ... -> [13,11] -> [13,12]* -> [13,13]^ -> enemy
Enemy path:     enters [13,13]^ or [14,13]^ -> [13,12]* -> [13,11] -> down

SP remaining: 1

---

## Turn 6 (+5 SP = 6 SP)  --  save MP turn

Spent: 1 support (4 SP)
New: support [10,9]

```
         1111111111222222222
x: 0123456789012345678901234567

y13: TWWWWWWWWWWWWW^^WWWWWWWWWWWT
y12:  ..........TW*WT..............
y11:   ........................
y10:    ......................
y09:     ......S..............
```

SP remaining: 2

---

## Turn 7 (+5 SP = 7 SP)  --  attack turn

Spent: upgrade support [10,9] (4 SP) + upgrade walls [12,12],[14,12] (2 SP)
Upgraded: [10,9] S->P, [12,12] W->X, [14,12] W->X

```
         1111111111222222222
x: 0123456789012345678901234567

y13: TWWWWWWWWWWWWW^^WWWWWWWWWWWT
y12:  ..........TX*XT..............
y11:   ........................
y10:    ......................
y09:     ......P..............
```

Upgraded walls at chokepoint now have 120 HP -- very durable.
Upgraded support shields passing scouts with 6.7 HP each.
SP remaining: 1

---

## Turn 8 (+5 SP = 6 SP)  --  save MP turn

Spent: 1 support (4 SP)
New: support [17,9]

```
         1111111111222222222
x: 0123456789012345678901234567

y13: TWWWWWWWWWWWWW^^WWWWWWWWWWWT
y12:  ..........TX*XT..............
y11:   ........................
y10:    ......................
y09:     ......P......S.......
```

SP remaining: 2

---

## Turn 9 (+5 SP = 7 SP)  --  attack turn

Spent: upgrade [17,9] (4 SP) + turret [12,11] (3 SP)
New: turret [12,11], upgraded support [17,9]

```
         1111111111222222222
x: 0123456789012345678901234567

y13: TWWWWWWWWWWWWW^^WWWWWWWWWWWT
y12:  ..........TX*XT..............
y11:   ..........T.................
y10:    ......................
y09:     ......P......P.......
```

Kill box deepened! Turret at [12,11] adds a 3rd gun covering [13,12].
Both supports now upgraded (6.7 shield each, range 12).
SP remaining: 0

---

## Turn 10 (+5 SP = 5 SP)  --  MP income now 6/turn

Spent: turret [14,11] (3 SP)
New: turret at [14,11]

```
         1111111111222222222
x: 0123456789012345678901234567

y13: TWWWWWWWWWWWWW^^WWWWWWWWWWWT
y12:  ..........TX*XT..............
y11:   ..........T*T...............
y10:    ......................
y09:     ......P......P.......
```

**FULL KILL BOX!** 4 turrets overlap on [13,12]:
  [11,12] dist 2.0   [15,12] dist 2.0
  [12,11] dist 1.41  [14,11] dist 1.41
All within base range 2.5. Enemy units at [13,12] take fire from all 4.
Scout corridor [13,11]->[13,12]->[13,13] still open.
SP remaining: 2

---

## Turn 11 (+5 SP = 7 SP)

Spent: turrets [5,12] (3 SP) and [22,12] (3 SP)
New: side turrets for wider coverage

```
         1111111111222222222
x: 0123456789012345678901234567

y13: TWWWWWWWWWWWWW^^WWWWWWWWWWWT
y12:  ....T.....TX*XT......T......
y11:   ..........T*T...............
y10:    ......................
y09:     ......P......P.......
```

Side turrets cover enemy units walking along y=13 wall toward the gap.
SP remaining: 1

---

## Turns 12-18: Upgrade Phase

With 5 SP/turn (plus scoring bonuses), turret upgrades (8 SP each) take
~2 turns to save for. Approximate timeline:

| Turn | Upgrade                    | Cumulative |
|------|----------------------------|------------|
| 13   | [11,12] turret -> U        | 1 upgraded turret in kill box |
| 14   | [15,12] turret -> U        | 2 upgraded turrets in kill box |
| 16   | [0,13] corner -> U         | Left corner upgraded |
| 18   | [27,13] corner -> U        | Right corner upgraded |
| 19   | [12,11] turret -> U        | 3rd kill box turret upgraded |
| 20   | [14,11] turret -> U        | Full kill box upgraded |
| 22   | [5,12] turret -> U         | Left flank upgraded |
| 23   | [22,12] turret -> U        | Right flank upgraded |

Note: Scoring bonus SP (+1 per point dealt) accelerates this significantly.
If scouts score 5 pts, that's +5 SP next turn, cutting upgrade time in half.

---

## Final Form (~Turn 23+)

```
         1111111111222222222
x: 0123456789012345678901234567

y13: UWWWWWWWWWWWWW^^WWWWWWWWWWWU    U = upgraded turrets at corners
y12:  ....U.....UX*XU......U......    U = upgraded turrets flanking
y11:   ..........U*U...............    U = upgraded deep kill box
y10:    ......................
y09:     ......P......P.......        P = upgraded supports (6.7 shield, range 12)
y08:      .....P......P......         P = extra supports if SP allows
```

**Kill box stats (all upgraded):**
- 4 turrets x 20 damage = 80 damage/frame at [13,12]
- Each enemy scout (15 HP) dies in 1 frame at chokepoint
- Upgraded walls (120 HP) protect the turrets
- 2-4 upgraded supports shield outgoing scouts with 6.7 HP each

**Scout corridor** (always open):
```
[13,0] -> [13,1] -> ... -> [13,11] -> [13,12] -> [13,13] -> enemy territory
                               *           *          ^
                           open tile    chokepoint   funnel gap
```

---

## SP Budget Summary (pessimistic, no scoring bonus)

| Turn | Income | Spent On                          | Remaining |
|------|--------|-----------------------------------|-----------|
| 0    | 40     | 4 turrets + 14 walls              | 0         |
| 1    | 5      | 2 walls                           | 1         |
| 2    | 6      | 3 walls                           | 0         |
| 3    | 5      | 2 walls                           | 1         |
| 4    | 6      | 3 walls (gap = 2 tiles)           | 0         |
| 5    | 5      | 2 chokepoint walls                | 1         |
| 6    | 6      | 1 support [10,9]                  | 2         |
| 7    | 7      | upgrade support + 2 wall upgrades | 1         |
| 8    | 6      | 1 support [17,9]                  | 2         |
| 9    | 7      | upgrade support + turret [12,11]  | 0         |
| 10   | 5      | turret [14,11]                    | 2         |
| 11   | 7      | turrets [5,12] + [22,12]          | 1         |
| 12+  | 5/turn | turret upgrades (8 SP each)       | varies    |

## MP Budget Summary

| Turn | Income | Spent On             | Saved |
|------|--------|----------------------|-------|
| 0    | 5.0    | 1 interceptor (3)    | 2.0   |
| 1    | 6.5    | 1 interceptor (3)    | 3.5   |
| 2    | 7.6    | 1 interceptor (3)    | 4.6   |
| 3    | 8.5    | 1 interceptor (3)    | 5.5   |
| 4    | 9.1    | 1 interceptor (3)    | 6.1   |
| 5    | 9.6    | ~9 scouts (attack)   | 0.6   |
| 6    | 5.5    | 1 interceptor (save) | 2.5   |
| 7    | 6.9    | ~6 scouts (attack)   | 0.9   |
| 8    | 5.7    | 1 interceptor (save) | 2.7   |
| 9    | 7.0    | ~7 scouts (attack)   | 0.0   |
| 10+  | 6/turn | alternating save/attack pattern   |

MP income increases: 6/turn at turns 10-19, 7 at 20-29, etc.
Attack waves grow larger over time as income scales.
